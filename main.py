from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from fastapi.encoders import jsonable_encoder
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

# ========================
# Підключення до БД
# ========================
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ========================
# Модель SQLAlchemy
# ========================
class HabitDB(Base):
    __tablename__ = "habits"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    user_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    streak_data = Column(Text, default="")  # Сюди записуються дати виконання

# Створення таблиці
Base.metadata.create_all(bind=engine)

# ========================
# Pydantic моделі
# ========================
class HabitBase(BaseModel):
    title: str
    user_id: int

class HabitCreate(HabitBase):
    pass

class Habit(HabitBase):
    id: int
    created_at: datetime
    streak_data: Optional[str] = ""

    class Config:
        from_attributes = True  # для pydantic v2

# ========================
# Роути
# ========================
@app.get("/")
def root():
    return {"msg": "Hello from HabitFlow backend!"}


@app.get("/habits", response_model=List[Habit])
def get_habits(user_id: int = Query(...)):
    db = SessionLocal()
    try:
        habits = db.query(HabitDB).filter(HabitDB.user_id == user_id).all()
        return habits
    finally:
        db.close()


@app.post("/habits", response_model=Habit)
def add_habit(habit_data: HabitCreate):
    db = SessionLocal()
    db_habit = HabitDB(**habit_data.dict())
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)
    db.close()
    return db_habit


@app.put("/habits/{habit_id}", response_model=Habit)
def update_habit(habit_id: int, habit: Habit):
    db = SessionLocal()
    db_habit = db.query(HabitDB).filter(HabitDB.id == habit_id).first()
    if not db_habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    for field, value in habit.dict().items():
        setattr(db_habit, field, value)
    db.commit()
    db.refresh(db_habit)
    db.close()
    return db_habit


@app.delete("/habits/{habit_id}")
def delete_habit(habit_id: int):
    db = SessionLocal()
    db_habit = db.query(HabitDB).filter(HabitDB.id == habit_id).first()
    if not db_habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    db.delete(db_habit)
    db.commit()
    db.close()
    return {"detail": "Habit deleted"}

@app.get("/debug-columns")
def debug_columns():
    inspector = inspect(engine)
    columns = inspector.get_columns("habits")
    return {"columns": [col["name"] for col in columns]}
