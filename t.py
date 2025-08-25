from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from database.core import engine, Base, get_db
from models.r_schema import UserCreate, User
from models.r_model import User as UserModel # Renaming for clarity in this file

# This line creates the tables in the database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# A simple root endpoint to confirm the API is running
@app.get("/")
def read_root():
    return {"Hello": "World"}

# Endpoint to create a new user in the database
@app.post('/users', response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserModel(username=user.username, email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Endpoint to get a user by ID from the database
@app.get('/users/{user_id}', response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user