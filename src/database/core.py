from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os


load_dotenv()
DB_URL = os.getenv(
    "DATABASE_URL",
    # "PG_PRODUCTION_DB_URI", # this is for future use
)

if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



