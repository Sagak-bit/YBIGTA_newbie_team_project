# app/user/user_repository.py
from __future__ import annotations

from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.user.user_schema import User


class UserRepository:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def get_user_by_email(self, email: str) -> Optional[User]:
        row = self.db.execute(
            text(
                """
                SELECT email, password, username
                FROM users
                WHERE email = :email
                """
            ),
            {"email": str(email)},
        ).fetchone()

        if row is None:
            return None

        return User(email=row[0], password=row[1], username=row[2])

    def save_user(self, user: User) -> User:
        # 존재 여부 확인
        existing = self.get_user_by_email(user.email)

        if existing is None:
            # INSERT
            self.db.execute(
                text(
                    """
                    INSERT INTO users (email, password, username)
                    VALUES (:email, :password, :username)
                    """
                ),
                {"email": str(user.email), "password": user.password, "username": user.username},
            )
        else:
            # UPDATE
            self.db.execute(
                text(
                    """
                    UPDATE users
                    SET password = :password,
                        username = :username
                    WHERE email = :email
                    """
                ),
                {"email": str(user.email), "password": user.password, "username": user.username},
            )

        self.db.commit()

        saved = self.get_user_by_email(user.email)
        return saved if saved is not None else user

    def delete_user(self, user: User) -> User:
        self.db.execute(
            text("DELETE FROM users WHERE email = :email"),
            {"email": str(user.email)},
        )
        self.db.commit()
        return user
