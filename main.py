from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from fastapi.encoders import jsonable_encoder
import json

app = FastAPI()

# Дозволяємо запити з Vercel і Telegram
origins = [
    "https://habitflow-webapp.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # або ["*"] для тесту
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


SQLALCHEMY_DATABASE_URL = "sqlite:///./habits.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========================
# Database модель
# ========================
class HabitDB(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    user_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    streak_data = Column(Text, default='["none", "none", "none", "none", "none", "none", "none"]')
    weeks_count = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

# ========================
# Pydantic моделі
# ========================
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
    created_at: datetime
    streak_data: List[str]
    weeks_count: int

    class Config:
        orm_mode = True

# ========================
# API
# ========================
@app.get("/habits", response_model=List[Habit])
def get_habits(user_id: int = Query(...)):
    db = SessionLocal()
    habits = db.query(HabitDB).filter(HabitDB.user_id == user_id).all()
    for habit in habits:
        habit.streak_data = json.loads(habit.streak_data)
    db.close()
    return habits

@app.post("/habits", response_model=Habit)
def create_habit(habit: HabitCreate):
    db = SessionLocal()
    db_habit = HabitDB(title=habit.title, user_id=habit.user_id)
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)
    db_habit.streak_data = json.loads(db_habit.streak_data)
    db.close()
    return db_habit

@app.put("/habits/{habit_id}", response_model=Habit)
def update_habit(habit_id: int, habit: HabitUpdate):
    db = SessionLocal()
    db_habit = db.query(HabitDB).filter(HabitDB.id == habit_id).first()
    if not db_habit:
        db.close()
        raise HTTPException(status_code=404, detail="Habit not found")

    db_habit.title = habit.title
    if habit.streak_data is not None:
        db_habit.streak_data = json.dumps(habit.streak_data)
    if habit.weeks_count is not None:
        db_habit.weeks_count = habit.weeks_count

    db.commit()
    db.refresh(db_habit)
    db_habit.streak_data = json.loads(db_habit.streak_data)
    db.close()
    return db_habit

@app.delete("/habits/{habit_id}")
def delete_habit(habit_id: int):
    db = SessionLocal()
    habit = db.query(HabitDB).filter(HabitDB.id == habit_id).first()
    if not habit:
        db.close()
        raise HTTPException(status_code=404, detail="Habit not found")
    db.delete(habit)
    db.commit()
    db.close()
    return {"message": "Habit deleted"}

@app.put("/habits/{habit_id}/mark_done_today", response_model=Habit)
def mark_done_today(habit_id: int):
    db = SessionLocal()
    habit = db.query(HabitDB).filter(HabitDB.id == habit_id).first()
    if not habit:
        db.close()
        raise HTTPException(status_code=404, detail="Habit not found")

    streak = json.loads(habit.streak_data)
    streak[-1] = "done"

    # Псевдологіка підрахунку тижнів
    if all(day == "done" for day in streak):
        habit.weeks_count += 1
        streak = ["none"] * 7
    habit.streak_data = json.dumps(streak)

    db.commit()
    db.refresh(habit)
    habit.streak_data = json.loads(habit.streak_data)
    db.close()
    return habit
