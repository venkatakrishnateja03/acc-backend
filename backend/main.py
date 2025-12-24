from fastapi import FastAPI, Depends
import os
from fastapi.middleware.cors import CORSMiddleware
from models import user, media
from db.database import engine
from sqlalchemy.orm import Session
from typing import Annotated
from db.database import init_db, get_db
from routers import files, auth
from routers import workspaces
from routers import documents, comments

app = FastAPI()
init_db(app)
# Configure CORS. Set environment variable `ALLOWED_ORIGINS` to a comma-separated
# list of allowed origins (e.g. "https://example.com,https://app.example.com").
# If not set, defaults to allow all origins for development convenience.
allowed_origins_env = os.getenv("ALLOWED_ORIGINS")
if allowed_origins_env:
    allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
else:
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
user.Base.metadata.create_all(bind=engine)
media.Base.metadata.create_all(bind=engine)
app.include_router(files.router)
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(documents.router)
app.include_router(comments.router)
db_dependency = Annotated[Session, Depends(get_db)]


@app.get("/")
async def user1():
    return {"message": "Welcome to the FastAPI application!"}
