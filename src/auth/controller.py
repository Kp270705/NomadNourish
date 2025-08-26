from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database.core import get_db
from services.authService import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from models.r_schema import (Token)
from models.r_model import (User as UserModel, Restaurant as RestaurantModel)


router = APIRouter(
    prefix='/auth',
    tags=['auth']
)


@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Unified login endpoint for both users and restaurants.
    """
    # Attempt to authenticate as a user
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if user and verify_password(form_data.password, user.password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "is_restaurant": False}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # If not a user, attempt to authenticate as a restaurant
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.name == form_data.username).first()
    if restaurant and verify_password(form_data.password, restaurant.password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": restaurant.name, "is_restaurant": True}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # If no match is found
    raise HTTPException(status_code=401, detail="Incorrect username or password")