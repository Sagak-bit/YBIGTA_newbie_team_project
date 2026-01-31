# database/mysql_connection.py
from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

# .env에서 읽기 (키 이름은 과제/팀 규칙에 맞춰 통일하세요)
DB_USER = os.getenv("MYSQL_USER")
DB_PASSWD = os.getenv("MYSQL_PASSWORD")
DB_HOST = os.getenv("MYSQL_HOST")
DB_PORT = os.getenv("MYSQL_PORT", "3306")
DB_NAME = os.getenv("MYSQL_DATABASE")

# 방어: 누락된 값이 있으면 import 시점에 바로 명확히 알려줌
_missing = [k for k, v in {
    "MYSQL_USER": DB_USER,
    "MYSQL_PASSWORD": DB_PASSWD,
    "MYSQL_HOST": DB_HOST,
    "MYSQL_DATABASE": DB_NAME,
}.items() if not v]

if _missing:
    raise RuntimeError(
        "MySQL env missing: "
        + ", ".join(_missing)
        + " (check your .env or environment variables)"
    )

# 방어: pymysql 드라이버가 없으면 create_engine에서 실패 -> 메시지 명확화
try:
    import pymysql  # noqa: F401
except Exception as e:
    raise RuntimeError(
        "Missing dependency 'pymysql'. Add it to requirements.txt / poetry / pip install pymysql."
    ) from e

DB_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset=utf8mb4"
)

# echo는 로그 폭탄이 될 수 있어 기본 False 권장
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() in ("1", "true", "yes")

engine = create_engine(
    DB_URL,
    echo=SQLALCHEMY_ECHO,
    pool_pre_ping=True,     # 방어: 끊긴 커넥션 재검증
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)
