from sqlmodel import SQLModel, Field, create_engine, Session
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    return Session(engine)

class Habit(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str

class HabitCreate(SQLModel):
    title: str
