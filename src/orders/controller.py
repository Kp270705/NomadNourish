from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session 

from database.core import get_db
from services.authService import get_password_hash
from models.r_schema import (UserCreate, User)
from models.r_model import (User as UserModel)


router = APIRouter(
    prefix='/order',
    tags=['order']
)

# @router.post("/orders", response_model=User)


