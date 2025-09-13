from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt, JWTError  
from datetime import timezone, timedelta, datetime
from typing import Annotated
from sqlalchemy.orm import Session
import os

from database.core import get_db
from models.r_model import (User as UserModel, Restaurant as RestaurantModel)


# 🔑 JWT & Password setup
SECRET_KEY=str(os.environ.get('SECRET_KEY'))
ALGORITHM=str(os.environ.get('ALGORITHM', 'HS256'))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Use a single token URL for both user and restaurant login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user_or_restaurant(
    token: Annotated[str, Depends(oauth2_scheme)], 
    db: Session = Depends(get_db)):

    print(f"\n\n\tIn GCUOR...")
    """
    Decodes the JWT token and returns the authenticated user or restaurant object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Login again with correct credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        is_restaurant = payload.get("is_restaurant", False)
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    if is_restaurant:
        entity = db.query(RestaurantModel).filter(RestaurantModel.table_id == username).first()
    else:
        entity = db.query(UserModel).filter(UserModel.table_id == username).first()

    if entity is None:
        raise credentials_exception
    
    return entity