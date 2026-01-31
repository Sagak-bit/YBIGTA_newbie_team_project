# app/dependencies.py
from functools import lru_cache
from fastapi import Depends

from app.user.user_service import UserService
from app.user.user_repository import UserRepository

@lru_cache
def get_mysql_engine():
    # 여기서 늦게 import -> 서버 부팅 단계에서는 MySQL env 없어도 안 죽음
    from database.mysql_connection import engine
    return engine

def get_user_repository():
    engine = get_mysql_engine()
    return UserRepository(engine)

def get_user_service(repo=Depends(get_user_repository)):
    return UserService(repo)
