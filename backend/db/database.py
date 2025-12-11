from sqlalchemy import create_engine,text
from sqlalchemy.orm import sessionmaker, declarative_base
# from core.config import settings
import core.config as config

db_url = config.db_url
engine = create_engine(db_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
def init_db(app):
    @app.on_event("startup")
    async def startup_check():
        # optional async or sync—either way works
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("DB connection OK")
        except Exception as exc:
            print("DB connection failed:", exc)
            raise
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()