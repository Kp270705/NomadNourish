# src/orders/controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Annotated, List
from datetime import datetime, timezone
import math

from database.core import get_db
from services.authService import get_current_user_or_restaurant
from models.r_schema import OrderBase, Order, OrderResponse
from models.r_model import (Order as OrderModel, User as UserModel, Restaurant as RestaurantModel, Cuisine as CuisineModel, OrderItem as OrderItemModel)
from user.service import get_current_user
from restaurant.service import get_current_restaurant


router = APIRouter(
    prefix='/order',
    tags=['order']
)

# ==========================================================
# 🔹 ORDER APIs

# For Users:
@router.post("/create/{restaurant_id}", response_model=Order)
def create_order(
    restaurant_id: int,
    order_data: OrderBase, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Creates a new order. It VERIFIES the total price sent by the client
    against a secure, backend-calculated total.
    """
    if not isinstance(current_user, UserModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant owners cannot place orders."
        )

    # 1. Fetch all cuisine details from the DB to get the TRUE prices
    cuisine_ids = [item.cuisine_id for item in order_data.items]
    cuisines = db.query(CuisineModel).filter(CuisineModel.id.in_(cuisine_ids)).all()
    cuisine_map = {c.id: c for c in cuisines}

    # 2. Securely calculate the total price on the backend
    backend_total_price = 0
    order_items_to_create = []

    for item_data in order_data.items:
        cuisine = cuisine_map.get(item_data.cuisine_id)
        
        if not cuisine or cuisine.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cuisine with id {item_data.cuisine_id} not found."
            )

        price_for_item = cuisine.price_full if item_data.size == "full" else cuisine.price_half
        
        if price_for_item is None:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cuisine '{cuisine.cuisine_name}' does not have a '{item_data.size}' price option."
            )
            
        backend_total_price += price_for_item * item_data.quantity
        
        order_items_to_create.append(
            OrderItemModel(
                cuisine_id=item_data.cuisine_id,
                quantity=item_data.quantity,
                size=item_data.size,
                price_at_purchase=price_for_item
            )
        )

    # 3. VERIFY the frontend price against the secure backend price
    # We use math.isclose() to handle potential floating-point inaccuracies
    if not math.isclose(order_data.client_total_price, backend_total_price):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Price mismatch. Client price: {order_data.client_total_price}, Server price: {backend_total_price}. Please refresh."
        )

    # 4. Create the order using the TRUSTED, backend-calculated price
    db_order = OrderModel(
        total_price=backend_total_price, # <-- Using the secure price
        restaurant_id=restaurant_id,
        user_id=current_user.id
    )

    db_order.order_items.extend(order_items_to_create)
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    
    return db_order



@router.get("/user/my-orders", response_model=List[OrderResponse])
def get_user_orders(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieves all orders for the authenticated user, eagerly loading restaurant names and order items.
    """
    if not isinstance(current_user, UserModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can view their orders."
        )
    
    # Use joinedload to prevent the N+1 query problem
    orders = db.query(OrderModel).options(
        joinedload(OrderModel.restaurant),
        joinedload(OrderModel.order_items).joinedload(OrderItemModel.cuisine)
    ).filter(OrderModel.user_id == current_user.id).all()

    # Pydantic can now handle the mapping automatically with a bit of help
    result = []
    for order in orders:
        result.append({
            "id": order.id,
            "restaurant_name": order.restaurant.name,
            "order_date": str(order.order_date),
            "status": order.status,
            "total_price": order.total_price,
            "order_items": order.order_items,  # This will be automatically serialized
            "restaurant_id": order.restaurant_id,
        })
        
    return result



# ==============================================================
# For Restaurants: 

# fetching restaurants order history: 
@router.get("/restaurant/my-orders", response_model=list[OrderResponse])
def get_restaurant_orders(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves all orders for the authenticated restaurant owner.
    """
    if not isinstance(current_restaurant, RestaurantModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only restaurant owners can view their orders."
        )
    
    orders = db.query(OrderModel).filter(OrderModel.restaurant_id == current_restaurant.id).all()
    
    # We must manually map the data to the Pydantic schema here.
    result = []
    for order in orders:
        order_dict = order.__dict__
        order_dict['restaurant_name'] = current_restaurant.name # Get name from current restaurant
        result.append(order_dict)
    
    return result


