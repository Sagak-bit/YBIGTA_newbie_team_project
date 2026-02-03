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
        # SQL 실행
        row = self.db.execute(
            text("SELECT email, password, username FROM users WHERE email = :email"),
            {"email": str(email)},
        ).fetchone()

        if row is None:
            return None

        # 튜플(row)에서 데이터 꺼내서 User 객체 생성
        return User(email=row[0], password=row[1], username=row[2])

    def save_user(self, user: User) -> User:
        existing = self.get_user_by_email(user.email)

        if existing is None:
            # 없으면 INSERT (회원가입)
            self.db.execute(
                text("""
                    INSERT INTO users (email, password, username)
                    VALUES (:email, :password, :username)
                """),
                {"email": str(user.email), "password": user.password, "username": user.username},
            )
        else:
            # 있으면 UPDATE (정보수정)
            self.db.execute(
                text("""
                    UPDATE users
                    SET password = :password,
                        username = :username
                    WHERE email = :email
                """),
                {"email": str(user.email), "password": user.password, "username": user.username},
            )

        # ★ 핵심 수정: commit 기능이 있을 때만 실행 (테스트 환경 에러 방지)
        if hasattr(self.db, "commit"):
            self.db.commit()

        # 저장된 데이터 다시 조회해서 반환
        return self.get_user_by_email(user.email)

    def delete_user(self, user: User) -> User:
        # 삭제
        self.db.execute(
            text("DELETE FROM users WHERE email = :email"),
            {"email": str(user.email)},
        )
        
        # ★ 핵심 수정: commit 기능이 있을 때만 실행
        if hasattr(self.db, "commit"):
            self.db.commit()
            
        return user