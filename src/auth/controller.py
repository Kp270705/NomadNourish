from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Annotated, Union

from database.core import get_db
from services.authService import get_current_user_or_restaurant, get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from models.r_schema import (Token)
from models.r_model import (User as UserModel, Restaurant as RestaurantModel)
from services.authService import (
    verify_password, 
    create_access_token, 
    ACCESS_TOKEN_EXPIRE_MINUTES,
    oauth2_scheme,
    TOKEN_BLACKLIST,
)


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
    user = db.query(UserModel).filter(UserModel.email == form_data.username).first()
    if user and verify_password(form_data.password, user.password):

        print(f"\n\nUser trying to access: {user.email}")

        user_table_id_str = str(user.table_id)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user_table_id_str, "is_restaurant": False, "user_id": user.email},
            expires_delta=access_token_expires
        )

        print(f"\n\n\tAccess Token: {access_token}\n\n")

        user_details = {
            "username": user.username,
            "email": user.email,
            "image_url": user.image_url
        }
        
        return JSONResponse(content={
            "message": 'user is authenticated', 
            "user_type": 'user', 
            "access_token": access_token, 
            "token_type": "bearer",
            "user_details": user_details,
        })

    # If not a user, attempt to authenticate as a restaurant
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.gstIN == form_data.username).first()
    if restaurant and verify_password(form_data.password, restaurant.password):

        print(f"\n\nRestaurant trying to access: {restaurant.name}")

        restaurant_table_id_str = str(restaurant.table_id)
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": restaurant_table_id_str, "is_restaurant": True, "user_id": restaurant.gstIN},
            expires_delta=access_token_expires
        )
        
        print(f"\n\n\tAccess Token: {access_token}\n\n")

        user_details = {
            "name": restaurant.name,
            "location": restaurant.location,
            "mobile_number": restaurant.mobile_number,
            "image_url": restaurant.image_url,
            "support_email": restaurant.support_email,
            "gstIN": restaurant.gstIN
        }
        return JSONResponse(content={
            "message": 'restaurant is authenticated', 
            "user_type": 'restaurant', 
            "access_token": access_token, 
            "token_type": "bearer",
            "user_details": user_details,
        })

    # If no match is found
    raise HTTPException(status_code=401, detail="Incorrect username or password")


@router.post("/logout")
def logout_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    Logs out the user by blacklisting their current token.
    """
    TOKEN_BLACKLIST.add(token)
    return {"message": "Successfully logged out"}

