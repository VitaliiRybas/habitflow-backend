from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

app = FastAPI()

origins = ["*"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])

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

Base.metadata.create_all(bind=engine)

# ========================
# Pydantic моделі
# ========================
class HabitCreate(BaseModel):
    title: str
    user_id: int

class HabitUpdate(BaseModel):
    title: str
    user_id: int

class Habit(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True

# ========================
# API
# ========================
@app.get("/habits", response_model=List[Habit])
def get_habits(user_id: int = Query(...)):
    db = SessionLocal()
    habits = db.query(HabitDB).filter(HabitDB.user_id == user_id).all()
    db.close()
    return habits

@app.post("/habits", response_model=Habit)
def create_habit(habit: HabitCreate):
    db = SessionLocal()
    db_habit = HabitDB(title=habit.title, user_id=habit.user_id)
    db.add(db_habit)
    db.commit()
    db.refresh(db_habit)
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
    db.commit()
    db.refresh(db_habit)
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
