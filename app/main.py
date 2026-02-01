from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

from app.user.user_router import user
from app.review.review_router import review
from app.config import PORT

app = FastAPI()

static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.include_router(user)
app.include_router(review)

if __name__ == "__main__":
    # 핵심: "main:app"가 아니라 "app.main:app"
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)