from fastapi import FastAPI,status,Depends,HTTPException
from models import user, media
from db.database import engine, SessionLocal
from sqlalchemy.orm import Session
from typing import Annotated
from db.database import init_db, get_db
from routers import files
app = FastAPI()
init_db(app)
user.Base.metadata.create_all(bind=engine)
media.Base.metadata.create_all(bind=engine)
app.include_router(files.router)

db_dependency=Annotated[Session, Depends(get_db)]
@app.get("/")
async def user():
    return {"message": "Welcome to the FastAPI application!"}