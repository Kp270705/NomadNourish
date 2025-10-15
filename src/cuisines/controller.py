from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from sqlalchemy import func
from typing import List
import os, uuid

from database.core import get_db
from models.r_schema import (CuisineCreate, Cuisine, RestaurantMenuResponse, CuisineUpdate)
from models.r_model import (Restaurant as RestaurantModel, Cuisine as CuisineModel)
from restaurant.service import get_current_restaurant



router = APIRouter(
    prefix='/cuisine',
    tags=['cuisine']
)

@router.post("/register", response_model=Cuisine)
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
        price_half=cuisine.price_half,
        price_full=cuisine.price_full,
        category=cuisine.category,
        restaurant_id=current_restaurant.id,
        restaurant_specific_cuisine_id=new_cuisine_id
    )

    db.add(db_cuisine)
    db.commit()
    db.refresh(db_cuisine)
    return db_cuisine


@router.patch("/{cuisine_id}", response_model=Cuisine)
def update_cuisine(
    cuisine_id: int,
    cuisine_data: CuisineUpdate,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    # Find the cuisine and verify it belongs to the current restaurant
    db_cuisine = db.query(CuisineModel).filter(
        CuisineModel.id == cuisine_id,
        CuisineModel.restaurant_id == current_restaurant.id
    ).first()

    if not db_cuisine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuisine not found or does not belong to this restaurant."
        )
    
    # Update fields if provided
    for key, value in cuisine_data.model_dump().items():
        if value is not None:
            print(f"\n\nUpdating {key} to {value}\n\n")
            setattr(db_cuisine, key, value)
    if db_cuisine.is_active == False:
        db_cuisine.is_active = True
    db.commit()
    db.refresh(db_cuisine)
    return db_cuisine


# 🔹 API to soft delete a cuisine
@router.patch("/deactivate/{cuisine_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_cuisine(
    cuisine_id: int,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    # Find the cuisine and verify it belongs to the current restaurant
    db_cuisine = db.query(CuisineModel).filter(
        CuisineModel.id == cuisine_id,
        CuisineModel.restaurant_id == current_restaurant.id
    ).first()

    if not db_cuisine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuisine not found or does not belong to this restaurant."
        )

    db_cuisine.is_active = False
    db.commit()
    return


@router.get("/get_all", response_model=list[Cuisine])
def list_cuisines(db: Session = Depends(get_db)):
    return db.query(CuisineModel).all()


#  New API to get a particular hotel's dishes
@router.get("/cuisines_by_restaurant_id/{restaurant_id}", response_model=RestaurantMenuResponse)
def get_restaurant_cuisines(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")

    cuisines = db.query(CuisineModel).filter(CuisineModel.restaurant_id == restaurant_id, CuisineModel.is_active == True).all()
    
    # Combine the data into the new response schema
    return {
        "restaurant_name": restaurant.name,
        "restaurant_location": restaurant.location,
        "cuisines": cuisines
    }


# when restaurants create cuisine, this will show their existing cuisines: 
@router.get("/my-cuisines", response_model=List[Cuisine])
def get_my_cuisines(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves all cuisines for the current authenticated restaurant.
    """
    cuisines = db.query(CuisineModel).filter(CuisineModel.restaurant_id == current_restaurant.id).all()
    return cuisines