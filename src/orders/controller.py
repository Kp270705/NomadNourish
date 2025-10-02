# src/orders/controller.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from typing import Annotated
from datetime import datetime, timezone

from database.core import get_db
from services.authService import get_current_user_or_restaurant
from models.r_schema import OrderBase, Order, OrderResponse
from models.r_model import (Order as OrderModel, User as UserModel, Restaurant as RestaurantModel)
from user.service import get_current_user
from restaurant.service import get_current_restaurant

router = APIRouter(
    prefix='/order',
    tags=['order']
)

# ==========================================================
# 🔹 ORDER APIs

# For Users:
@router.post("/orders/{restaurant_id}", response_model=Order)
def create_order(
    restaurant_id: int,
    order: OrderBase,
    db: Session = Depends(get_db),
    current_user:UserModel= Depends(get_current_user)
):
    """
    Creates a new order for the authenticated user at a specific restaurant.
    """
    # 1. Check if the authenticated entity is a user, not a restaurant
    if not isinstance(current_user, UserModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Restaurant owners cannot place orders."
        )

    # 2. Convert the list of items into a single string
    items_string = ", ".join(order.items)
    
    # 3. Create the new order model instance
    db_order = OrderModel(
        items=items_string,
        total_price=order.total_price,
        restaurant_id=restaurant_id,
        user_id=current_user.id,
        order_date=str(datetime.now(timezone.utc))
    )

    # 4. Save the order to the database
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    print(f"\n\tOrder.id: {db_order.id}")
    res = {
        "id": db_order.id,
        "items": order.items,
        "total_price": db_order.total_price,
        "restaurant_id": db_order.restaurant_id,
        "user_id": db_order.user_id,
        "order_date":db_order.order_date
    }

    return res


# @router.get("/orders/{order_id}", response_model=OrderResponse)
# def get_order_details(
#     order_id: int,
#     db: Session = Depends(get_db),
#     current_user:UserModel= Depends(get_current_user)

# ):
#     """
#     Retrieves a single order for the authenticated user.
#     """
#     if not isinstance(current_user, UserModel):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="You are not authorized to view this order."
#         )

#     order = db.query(OrderModel).filter(
#         OrderModel.id == order_id, 
#         OrderModel.user_id == current_user.id
#     ).first()
    
#     if not order:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found or you don't have permission to view it.")

#     return order


@router.get("/user/my-orders", response_model=list[OrderResponse])
def get_user_orders(
    db: Session = Depends(get_db),
    current_user:UserModel= Depends(get_current_user)
):
    """
    Retrieves all orders for the authenticated user with restaurant names.
    """
    if not isinstance(current_user, UserModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only users can view their orders."
        )
    
    orders_with_names = db.query(OrderModel, RestaurantModel.name).join(RestaurantModel).filter(
        OrderModel.user_id == current_user.id
    ).all()
    
    # Manually map the joined data to the response schema
    result = []
    for order, restaurant_name in orders_with_names:
        order_dict = order.__dict__
        order_dict['restaurant_name'] = restaurant_name
        result.append(order_dict)

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


