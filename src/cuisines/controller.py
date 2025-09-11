from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from sqlalchemy import func
from typing import List
import os, uuid

from database.core import get_db
from models.r_schema import (CuisineCreate, Cuisine)
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
@router.get("/cuisines_by_restaurant_id/{restaurant_id}", response_model=List[Cuisine])
def get_restaurant_cuisines(restaurant_id: int, db: Session = Depends(get_db)):
    """
    Retrieves all cuisine details for a specific restaurant.
    """
    cuisines = db.query(CuisineModel).filter(CuisineModel.restaurant_id == restaurant_id).all()
    if not cuisines:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No cuisines found for this restaurant."
        )
    return cuisines


# <CircleMinusSolid class="shrink-0 h-6 w-6" />
