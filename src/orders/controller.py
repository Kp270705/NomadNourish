# src/orders/controller.py

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Union, Optional
from datetime import datetime, timedelta, timezone
import math, json, asyncio

from database.core import get_db
from services.authService import get_current_user_or_restaurant
from models.r_schema import OrderCreate, Order, OrderResponse, OrderForRestaurantResponse, OrderStatusUpdate
from models.r_model import (Order as OrderModel, User as UserModel, Restaurant as RestaurantModel, Cuisine as CuisineModel, OrderItem as OrderItemModel)
from user.service import get_current_user
from restaurant.service import get_current_restaurant
from cache.redis_client import redis_client, get_redis_client
from services.authService import get_password_hash, get_current_entity_for_stream


router = APIRouter(
    prefix='/order',
    tags=['order']
)

# ==========================================================
# 🔹 ORDER APIs

# order place by user:
@router.post("/create/{restaurant_id}", response_model=Order)
async def create_order(
    restaurant_id: int,
    order_data: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    redis_client = Depends(get_redis_client),
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

    notification_payload = {
        "status": "Pending",
        "receiver": "restaurant",
        "payload": {
            "order_id": db_order.id,
            "message": f"Order #{db_order.id} has been placed by a user."
        }
    }

    channel = f"restaurant:{db_order.restaurant_id}:notifications"
    await redis_client.publish(channel, json.dumps(notification_payload))

    db.refresh(db_order)
    return db_order


# Order's status progress from restro side 
@router.patch("/restaurant/order/{order_id}/status", response_model=OrderForRestaurantResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant),
    redis_client = Depends(get_redis_client)
):
    """
    Allows a restaurant owner to update the status of one of their orders.
    """
    # Fetch the order with all its relationships for the response
    db_order = db.query(OrderModel).options(
        joinedload(OrderModel.user),
        joinedload(OrderModel.order_items).joinedload(OrderItemModel.cuisine)
    ).filter(OrderModel.id == order_id).first()

    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Security check: Ensure the order belongs to the current restaurant
    if db_order.restaurant_id != current_restaurant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this order")

    # Update status and save
    db_order.status = status_update.new_status

    if status_update.new_status == "Cancelled":
        db_order.cancelled_by = "restaurant"

    db.commit()

    notification_payload = {
        "status": f"{status_update.new_status.capitalize()}",
        "receiver": "user",
        "payload": {
            "order_id": db_order.id,
            "message": f"Order #{db_order.id} has been {status_update.new_status.lower()}."
        }
    }
    
   # Use 'await' for the async publish command
    channel = f"user:{db_order.user_id}:notifications"
    await redis_client.publish(channel, json.dumps(notification_payload))

    db.refresh(db_order)

    # Note: In a future step, you could add an SSE notification here
    # to inform the USER that their order status has changed.

    return db_order


#  order status cancel order by user:
@router.patch("/user/cancel/{order_id}", response_model=Order)
async def cancel_user_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    redis_client = Depends(get_redis_client)
):
    """
    Allows the authenticated user to cancel their own order,
    but only if the status is still 'Pending'.
    """
    # 1. Fetch the order from the database
    db_order = db.query(OrderModel).filter(OrderModel.id == order_id).first()

    # 2. Check if the order exists
    if not db_order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # 3. Security Check: Ensure the user owns this order
    if db_order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this order")

    # 4. Business Logic: Only allow cancellation if the order is still pending
    if db_order.status != "Pending" and db_order.status != "Preparing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status '{db_order.status}'"
        )

    # 5. Update the status
    db_order.status = "Cancelled"
    db_order.cancelled_by = "user"
    db.commit()

    notification_payload = {
        "status": "Cancelled",
        "receiver": "restaurant",
        "payload": {
            "order_id": db_order.id,
            "message": f"Order #{db_order.id} has been cancelled by the user."
        }
    }
    
   # Use 'await' for the async publish command
    channel = f"restaurant:{db_order.restaurant_id}:notifications"
    await redis_client.publish(channel, json.dumps(notification_payload))



    db.refresh(db_order)
    return db_order

# ==============================================================

# Api Response 

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
            "restaurant_id": order.restaurant_id,
            "order_date": str(order.order_date),
            "status": order.status,
            "total_price": order.total_price,
            "order_items": order.order_items,  # This will be automatically serialized
            "cancelled_by": order.cancelled_by,
        })
        
    return result


@router.get("/restaurant/my-orders", response_model=List[OrderForRestaurantResponse])
def get_restaurant_orders(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves ALL orders for the authenticated restaurant owner,
    eagerly loading all related data for high performance.
    Frontend will handle all date filtering.
    """
    print(f"GET /restaurant/my-orders hit. Sending ALL orders for restaurant ID: {current_restaurant.id}")
    
    # Query ab simple hai:
    # Sirf saare orders get karo, sort karke
    orders = db.query(OrderModel).options(
        joinedload(OrderModel.user),
        joinedload(OrderModel.order_items).joinedload(OrderItemModel.cuisine)
    ).filter(OrderModel.restaurant_id == current_restaurant.id).order_by(OrderModel.order_date.desc()).all()
    
    return orders


@router.get("/restaurant/active-orders", response_model=List[OrderForRestaurantResponse])
def get_restaurant_active_orders(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves all orders for a restaurant that are not yet delivered or cancelled.
    """
    active_statuses = ["Pending", "Preparing", "Ready"]
    
    orders = db.query(OrderModel).options(
        joinedload(OrderModel.user),
        joinedload(OrderModel.order_items).joinedload(OrderItemModel.cuisine)
    ).filter(
        OrderModel.restaurant_id == current_restaurant.id,
        OrderModel.status.in_(active_statuses)
    ).order_by(OrderModel.order_date.asc()).all() # Show oldest first to prioritize
    
    return orders


# ==========================================================


# Real Time Notifications via Redis Pub/Sub
@router.get("/notifications/stream")
async def stream_notifications(
    request: Request,
    redis_client = Depends(get_redis_client),
    # This dependency now returns either a User or a Restaurant object
    current_entity: Union[UserModel, RestaurantModel] = Depends(get_current_entity_for_stream)
):
    """
    A unified Server-Sent Events endpoint to stream real-time 
    notifications to either a logged-in user or a restaurant.
    """
    async def event_generator():
        # Use isinstance() to check the type of the logged-in entity
        if isinstance(current_entity, RestaurantModel):
            # If it's a restaurant, subscribe to the restaurant's channel
            channel = f"restaurant:{current_entity.id}:notifications"
        elif isinstance(current_entity, UserModel):
            # If it's a user, subscribe to the user's channel
            channel = f"user:{current_entity.id}:notifications"
        else:
            # A fallback in case of an unexpected entity type
            return

        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)
        
        try:
            async for message in pubsub.listen(): # should in 'for'
                if await request.is_disconnected():
                    break
                
                if message and message.get("type") == "message":
                    data = message["data"]
                    print(f"\n\n\tmessage is: {message}\n\n") # message is redis json obj
                    yield f"data: {data}\n\n"
                
                # A small sleep to prevent a tight loop if no messages
                await asyncio.sleep(0.1)
        finally:
            # Clean up the subscription when the client disconnects
            await pubsub.unsubscribe(channel)

    return StreamingResponse(event_generator(), media_type="text/event-stream")




