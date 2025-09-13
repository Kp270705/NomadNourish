from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from sqlalchemy import func
from typing import List
import os, uuid

from database.core import get_db
from models.r_schema import (CuisineCreate, Cuisine, RestaurantMenuResponse)
from models.r_model import (Restaurant as RestaurantModel, Cuisine as CuisineModel)
from restaurant.service import get_current_restaurant



router = APIRouter(
    prefix='/cuisine',
    tags=['cuisine']
)

@router.post("/cuisine/register", response_model=Cuisine)
def create_cuisine(
    cuisine: CuisineCreate,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    # 1. Find the highest existing restaurant_specific_cuisine_id for this restaurant
    max_id = db.query(func.max(CuisineModel.restaurant_specific_cuisine_id)).filter(
        CuisineModel.restaurant_id == current_restaurant.id
    ).scalar()
    new_cuisine_id = (max_id or 0) + 1

    # 3. Create the new Cuisine object with the calculated ID
    db_cuisine = CuisineModel(
        cuisine_name=cuisine.cuisine_name,
        cuisine_price=cuisine.cuisine_price,
        restaurant_id=current_restaurant.id,
        restaurant_specific_cuisine_id=new_cuisine_id
    )

    db.add(db_cuisine)
    db.commit()
    db.refresh(db_cuisine)
    return db_cuisine



@router.get("/get_all", response_model=list[Cuisine])
def list_cuisines(db: Session = Depends(get_db)):
    return db.query(CuisineModel).all()


#  New API to get a particular hotel's dishes
@router.get("/cuisines_by_restaurant_id/{restaurant_id}", response_model=RestaurantMenuResponse)
def get_restaurant_cuisines(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")

    cuisines = db.query(CuisineModel).filter(CuisineModel.restaurant_id == restaurant_id).all()
    
    # Combine the data into the new response schema
    return {
        "restaurant_name": restaurant.name,
        "restaurant_location": restaurant.location,
        "cuisines": cuisines
    }

