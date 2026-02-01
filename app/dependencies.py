# app/dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session

# mysql_connection에서 SessionLocal을 가져옵니다.
from database.mysql_connection import SessionLocal

from app.user.user_repository import UserRepository
from app.user.user_service import UserService


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_repository(db: Session = Depends(get_db)):
    return UserRepository(db)

def get_user_service(repo: UserRepository = Depends(get_user_repository)):
    return UserService(repo)