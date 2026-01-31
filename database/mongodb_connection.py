from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

mongo_url = os.getenv("MONGO_URL")
mongo_db_name = os.getenv("MONGO_DB_NAME", "ybigta")  # 기본값은 원하는 걸로

if not mongo_url:
    raise RuntimeError("MONGO_URL is not set. Check your .env file.")

mongo_client = MongoClient(mongo_url)
mongo_db = mongo_client[mongo_db_name]  # 또는 mongo_client.get_database(mongo_db_name)

mongo_client.admin.command("ping")
print("MongoDB connected!")
