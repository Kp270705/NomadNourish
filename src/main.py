from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session

from database.core import engine, Base, get_db
from models.r_schema import UserCreate, User
from models.r_model import User as UserModel


Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post('/users', response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = UserModel(username=user.username, email=user.email, password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get('/users/{user_id}', response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    return user


# ====================================================


