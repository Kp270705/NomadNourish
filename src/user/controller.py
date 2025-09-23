from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session 

from database.core import get_db
from services.authService import get_password_hash
from models.r_schema import (UserCreate, User)
from models.r_model import (User as UserModel)


router = APIRouter(
    prefix='/user',
    tags=['user']
)


@router.post("/register", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=409, detail="User already registered, enter unique name or email_id")
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        username=user.username,
        email=user.email,
        password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    db_user.table_id = f"user_id_{db_user.id}"
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
