from fastapi import APIRouter, Depends, HTTPException, Form, File, Query
from fastapi import UploadFile, status, Request
from fastapi.responses import StreamingResponse


from sqlalchemy import func, Date
from sqlalchemy.orm import Session, joinedload
from typing import List
from datetime import datetime, timedelta
import math, json
from typing import Optional, Union, List
import os, uuid

from database.core import get_db
from services.authService import get_password_hash, get_current_entity_for_stream
from models.r_schema import (RestaurantCreate, Restaurant, RestaurantStatusUpdate, RestaurantAnalytics)
from models.r_model import (Restaurant as RestaurantModel, OrderItem as OrderItemModel, Cuisine as CuisineModel, Order as OrderModel, User as UserModel)
from .service import get_current_restaurant, get_restaurant_status_by_id
from services.authService import get_current_user_or_restaurant
from dotenv import load_dotenv
import json, asyncio


# For Google Cloud Storage
from google.oauth2 import service_account
from google.cloud import storage
from google.api_core import exceptions
from cache.redis_client import get_redis_client

load_dotenv()
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
GCP_APPLICATION_CREDENTIALS = os.getenv("GCP_APPLICATION_CREDENTIALS")

router = APIRouter(
    prefix='/restaurant',
    tags=['restaurant']
)


# --- Google Cloud Storage Setup ---
try:
    # Authenticate with Google Cloud using service account credentials
    credentials = service_account.Credentials.from_service_account_file(GCP_APPLICATION_CREDENTIALS)
    storage_client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(GCP_BUCKET_NAME)
except Exception as e:
    print(f"Error initializing Google Cloud Storage client: {e}")
    storage_client = None
    bucket = None

# ==========================================================
# 🔹 RESTAURANT Auth APIs (Now Protected)

@router.post("/register", response_model=Restaurant)
def create_restaurant(restaurant: RestaurantCreate, db: Session = Depends(get_db)):
    db_restaurant = db.query(RestaurantModel).filter(RestaurantModel.gstIN == restaurant.gstIN).first()
    if db_restaurant:
        raise HTTPException(status_code=400, detail="Restaurant already exists")
    hashed_password = get_password_hash(restaurant.password)
    db_restaurant = RestaurantModel(
        name=restaurant.name,
        password=hashed_password,
        location=restaurant.location,
        mobile_number=restaurant.mobile_number,
        gstIN=restaurant.gstIN,
        support_email=restaurant.support_email,
    )
    db.add(db_restaurant)
    db.commit()
    db.refresh(db_restaurant)
    return db_restaurant


@router.get("/get_by_id/{restaurant_id}", response_model=Restaurant)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant


@router.get("/get_all", response_model=List[Restaurant])
async def get_all_restaurants(
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client),
    location: Optional[str] = Query(None, description="Optional filter by city/location")
    ):
    query = db.query(RestaurantModel)
    if location:
        query = query.filter(
            RestaurantModel.location.ilike(f"%{location}%")
        )
    db_restaurants = query.all()
    final_restaurants = []

    for rest in db_restaurants:
        status_data = await get_restaurant_status_by_id(db, redis_client, rest.id)
        rest_pydantic = Restaurant.model_validate(rest)
        rest_dict = rest_pydantic.model_dump()
        print(f"\n\n\tStatus Data fetched: {status_data}\n\n")
        
        if status_data:
            rest_dict.update(status_data)

        final_restaurants.append(rest_dict)
    return final_restaurants


# used to edit restaurant details:
@router.patch("/update_details", response_model=Restaurant)
async def update_restaurant_details(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant),
    name: str | None = Form(None),
    location: str | None = Form(None),
    contact_no: str | None = Form(None),
    contact_email: str | None = Form(None),
    image: UploadFile | None = File(None),
):
    print("▶️ In restro update details")
    print(f"Type of 'image' is: {type(image)}")

    if name:
        current_restaurant.name = name
    if location:
        current_restaurant.location = location
    if contact_no:
        current_restaurant.mobile_number = contact_no
    if contact_email:
        current_restaurant.support_email = contact_email

     # Handle image upload if a file is provided
     # Note: `image` can be None, so we check its type first
    if image is not None:
        print("✅ SUCCESS: The isinstance check passed!")
        print(f"Image filename is: {image.filename}")

        if not image.filename:
            raise HTTPException(status_code=400, detail="Please select a valid image.")

        if not storage_client or not bucket:
            raise HTTPException(status_code=500, detail="GCS not configured properly.")
        
        try:

            file_ext = os.path.splitext(image.filename)[1]
            unique_name = f"{uuid.uuid4()}{file_ext}"

            blob = bucket.blob(unique_name)

            # `image.file` is a SpooledTemporaryFile – reset pointer
            image.file.seek(0)
            blob.upload_from_file(image.file, content_type=image.content_type)

            current_restaurant.image_url = blob.public_url
        except Exception as e:
            print(f"Image is not Uploaded,due to this: 👇 👇 👇\n\t{e}")


    db.commit()
    db.refresh(current_restaurant)
    return current_restaurant


# kitchen status update:
@router.patch("/status", response_model=Restaurant)
async def update_restaurant_status(
    status_update: RestaurantStatusUpdate,
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant),
):
    """
    Allows the authenticated restaurant owner to quickly update 
    their operational status, kitchen load, and delivery availability.
    """
    if not isinstance(current_restaurant, RestaurantModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Must be a restaurant owner."
        )

    # Use model_dump(exclude_none=True) to get only the fields provided in the request body
    # This prevents updating fields that the owner didn't send.
    update_data = status_update.model_dump(exclude_none=True)
    
    # Apply updates to the database model instance
    for key, value in update_data.items():
        # This dynamically updates operating_status, kitchen_status, or delivery_status
        setattr(current_restaurant, key, value)
        
    db.commit()
    db.refresh(current_restaurant)

    cache_key = f"status:restaurant:{current_restaurant.id}"
    
    # Get the latest status data that Pydantic would use
    status_data = {
        "operating_status": current_restaurant.operating_status,
        "kitchen_status": current_restaurant.kitchen_status,
        "delivery_status": current_restaurant.delivery_status,
    }

    print(f"\n\n\tStatus Data to cache: {status_data}\n\n")
    # Store the JSON string in Redis (Set a 1 hour TTL - Time To Live)
    await redis_client.set(cache_key, json.dumps(status_data), ex=3600) 
    return current_restaurant


@router.get("/me", response_model=Restaurant)
def get_my_restaurant_details(
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves the details for the current authenticated restaurant owner.
    """
    return current_restaurant

# ======== new live sse event =============


@router.patch("/announcement", response_model=Restaurant)
def update_announcement(
    announcement: str = Form(..., description="The announcement text (max 1000 characters)"),
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Allows the authenticated restaurant owner to update their active announcement.
    If the announcement is an empty string, it clears the current announcement.
    """
    if len(announcement) > 500:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Announcement exceeds 500 characters.")
    
    # Update the field
    current_restaurant.announcement_text = announcement if announcement else None
    
    db.commit()
    db.refresh(current_restaurant)
    return current_restaurant


@router.get("/analytics", response_model=RestaurantAnalytics)
def get_restaurant_analytics(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant),
):
    """
    Calculates and returns key business analytics (revenue and sales focused)
    for the authenticated restaurant.
    """
    # 1. Fetch all completed orders for this restaurant
    completed_orders = db.query(OrderModel).filter(
        OrderModel.restaurant_id == current_restaurant.id,
        OrderModel.status == 'Delivered'
    ).all()

    if not completed_orders:
        return RestaurantAnalytics(
            total_revenue=0, total_orders=0, average_order_value=0,
            top_selling_items=[], top_revenue_items=[], revenue_by_day=[]
        )

    # 2. Calculate basic stats
    total_orders = len(completed_orders)
    total_revenue = sum(order.total_price for order in completed_orders)
    average_order_value = total_revenue / total_orders

    # 3. Find top 5 selling items by quantity
    top_selling_items = db.query(
        CuisineModel.cuisine_name,
        func.sum(OrderItemModel.quantity).label('total_quantity')
    ).join(OrderItemModel).join(OrderModel).filter(
        OrderModel.restaurant_id == current_restaurant.id,
        OrderModel.status == 'Delivered'
    ).group_by(CuisineModel.cuisine_name).order_by(func.sum(OrderItemModel.quantity).desc()).limit(5).all()

    # 4. Find top 5 revenue-generating items
    top_revenue_items = db.query(
        CuisineModel.cuisine_name,
        func.sum(OrderItemModel.price_at_purchase * OrderItemModel.quantity).label('total_revenue')
    ).join(OrderItemModel).join(OrderModel).filter(
        OrderModel.restaurant_id == current_restaurant.id,
        OrderModel.status == 'Delivered'
    ).group_by(CuisineModel.cuisine_name).order_by(func.sum(OrderItemModel.price_at_purchase * OrderItemModel.quantity).desc()).limit(5).all()

    # 5. Get revenue for the last 7 days for a line chart
    # seven_days_ago = datetime.utcnow() - timedelta(days=7)
    
    seven_days_ago = datetime.now() - timedelta(days=7)
    revenue_by_day = db.query(
        func.cast(OrderModel.order_date, Date).label('date'),
        func.sum(OrderModel.total_price).label('daily_revenue')
    ).filter(
        OrderModel.restaurant_id == current_restaurant.id,
        OrderModel.status == 'Delivered',
        OrderModel.order_date >= seven_days_ago
    ).group_by('date').order_by('date').all()

    return RestaurantAnalytics(
        total_revenue=total_revenue,
        total_orders=total_orders,
        average_order_value=average_order_value,
        top_selling_items=[{"name": name, "value": qty} for name, qty in top_selling_items],
        top_revenue_items=[{"name": name, "value": rev} for name, rev in top_revenue_items],
        revenue_by_day=[{"date": str(date), "revenue": rev} for date, rev in revenue_by_day]
    )




