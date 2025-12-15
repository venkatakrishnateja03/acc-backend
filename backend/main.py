from fastapi import FastAPI, Depends
from models import user, media
from db.database import engine
from sqlalchemy.orm import Session
from typing import Annotated
from db.database import init_db, get_db
from routers import files, auth

app = FastAPI()
init_db(app)
user.Base.metadata.create_all(bind=engine)
media.Base.metadata.create_all(bind=engine)
app.include_router(files.router)
app.include_router(auth.router)
db_dependency = Annotated[Session, Depends(get_db)]


@app.get("/")
async def user1():
    return {"message": "Welcome to the FastAPI application!"}
