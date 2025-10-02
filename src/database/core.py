from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = "sqlitecloud://cjd2p1bqhk.g6.sqlite.cloud:8860/test.db?apikey=0ukPyeLQzVCz88wHE8wbaaWnZErI3Z5x10eKT8gx82I"

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

