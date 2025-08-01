from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import json
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Дозволені фронти
origins = [
    "https://habitflow-webapp.vercel.app",
    "https://web.telegram.org",
    "https://t.me",
    "https://web.telegram.org/k/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# База даних
SQLALCHEMY_DATABASE_URL = "sqlite:///./habits_v2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class HabitDB(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    user_id = Column(Integer, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    streak_data = Column(Text, default='["none", "none", "none", "none", "none", "none", "none"]')
    weeks_count = Column(Integer, default=0)


Base.metadata.create_all(bind=engine)


class HabitBase(BaseModel):
    title: str
    user_id: int


class HabitCreate(HabitBase):
    pass


class HabitUpdate(HabitBase):
    streak_data: Optional[List[str]] = None
    weeks_count: Optional[int] = None


class Habit(HabitBase):
    id: int
    created_at: Optional[datetime] = None
    streak_data: List[str]
    weeks_count: int

    class Config:
        orm_mode = True


@app.get("/")
def root():
    return {"message": "HabitFlow backend is up"}


@app.get("/habits", response_model=List[Habit])
def get_habits(user_id: int = Query(...)):
    db = SessionLocal()
    try:
        habits = db.query(HabitDB).filter(HabitDB.user_id == user_id).all()
        for habit in habits:
            try:
                habit.streak_data = json.loads(habit.streak_data) if habit.streak_data else ["none"] * 7
            except Exception as e:
                logging.warning(f"JSON decode error for habit ID {habit.id}: {e}")
                habit.streak_data = ["none"] * 7
        logging.info(f"Loaded {len(habits)} habits for user {user_id}")
        return habits
    except Exception as e:
        logging.error(f"💥 Error in /habits: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        db.close()


@app.post("/habits", response_model=Habit)
def create_habit(habit: HabitCreate):
    db = SessionLocal()
    try:
        db_habit = HabitDB(title=habit.title, user_id=habit.user_id)
        db.add(db_habit)
        db.commit()
        db.refresh(db_habit)
        db_habit.streak_data = json.loads(db_habit.streak_data)
        logging.info(f"Created habit '{habit.title}' for user {habit.user_id}")
        return db_habit
    finally:
        db.close()


@app.put("/habits/{habit_id}", response_model=Habit)
def update_habit(habit_id: int, habit: HabitUpdate):
    db = SessionLocal()
    try:
        db_habit = db.query(HabitDB).filter(HabitDB.id == habit_id, HabitDB.user_id == habit.user_id).first()
        if not db_habit:
            raise HTTPException(status_code=404, detail="Habit not found or access denied")

        db_habit.title = habit.title
        if habit.streak_data is not None:
            db_habit.streak_data = json.dumps(habit.streak_data)
        if habit.weeks_count is not None:
            db_habit.weeks_count = habit.weeks_count

        db.commit()
        db.refresh(db_habit)
        db_habit.streak_data = json.loads(db_habit.streak_data)
        return db_habit
    finally:
        db.close()


@app.delete("/habits/{habit_id}")
def delete_habit(habit_id: int, user_id: int = Query(...)):
    db = SessionLocal()
    try:
        habit = db.query(HabitDB).filter(HabitDB.id == habit_id, HabitDB.user_id == user_id).first()
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found or access denied")
        db.delete(habit)
        db.commit()
        return {"message": "Habit deleted"}
    finally:
        db.close()


@app.post("/habits/{habit_id}/done", response_model=Habit)
def mark_done_today(habit_id: int, user_id: int = Query(...)):
    db = SessionLocal()
    try:
        habit = db.query(HabitDB).filter(HabitDB.id == habit_id, HabitDB.user_id == user_id).first()
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found or access denied")

        streak = json.loads(habit.streak_data)
        streak[-1] = "done"

        if all(day == "done" for day in streak):
            habit.weeks_count += 1
            streak = ["none"] * 7

        habit.streak_data = json.dumps(streak)
        db.commit()
        db.refresh(habit)
        habit.streak_data = json.loads(habit.streak_data)
        logging.info(f"✅ Marked done for habit ID {habit_id}, user {user_id}")
        return habit
    finally:
        db.close() # force redeploy