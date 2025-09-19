# src/stats/controller.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.core import get_db
from models.r_model import User as UserModel, Restaurant as RestaurantModel, Order as OrderModel
from models.r_schema import AppStats

router = APIRouter(
    prefix="/stats",
    tags=["stats"]
)

@router.get("/community", response_model=AppStats)
def get_community_stats(db: Session = Depends(get_db)):
    total_customers = db.query(UserModel).filter(UserModel.is_hotel_owner == False).count()
    total_restaurants = db.query(RestaurantModel).count()
    total_orders = db.query(OrderModel).count()
    
    return AppStats(
        total_customers=total_customers,
        total_restaurants=total_restaurants,
        total_orders=total_orders
    )