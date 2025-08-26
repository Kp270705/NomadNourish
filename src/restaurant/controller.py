from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session 

from database.core import get_db
from services.authService import get_password_hash
from models.r_schema import (RestaurantCreate, Restaurant, CuisineCreate, Cuisine)
from models.r_model import (Restaurant as RestaurantModel, Cuisine as CuisineModel)
from .service import get_current_restaurant


router = APIRouter(
    prefix='/restaurant',
    tags=['restaurant']
)


# ==========================================================
# 🔹 RESTAURANT Auth APIs (Now Protected)

@router.post("/restaurant", response_model=Restaurant)
def create_restaurant(restaurant: RestaurantCreate, db: Session = Depends(get_db)):
    db_restaurant = db.query(RestaurantModel).filter(RestaurantModel.name == restaurant.name).first()
    if db_restaurant:
        raise HTTPException(status_code=400, detail="Restaurant already exists")
    hashed_password = get_password_hash(restaurant.password)
    db_restaurant = RestaurantModel(name=restaurant.name, password=hashed_password, location=restaurant.location)
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant


@router.get("/restaurant/{restaurant_id}", response_model=Restaurant)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


# ==========================================================
# 🔹 CUISINE APIs (Restaurant Protected)

@router.post("/cuisine", response_model=Cuisine)
def create_cuisine(
    cuisine: CuisineCreate,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    db_cuisine = CuisineModel(
        cuisine_name=cuisine.cuisine_name,
        cuisine_price=cuisine.cuisine_price,
        restaurant_id=current_restaurant.id
    )
    db.add(db_cuisine)
    db.commit()
    db.refresh(db_cuisine)
    return db_cuisine

@router.get("/cuisine", response_model=list[Cuisine])
def list_cuisines(db: Session = Depends(get_db)):
    return db.query(CuisineModel).all()