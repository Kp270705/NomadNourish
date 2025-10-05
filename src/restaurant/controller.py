from fastapi import APIRouter, Depends, HTTPException, Form, File, Query
from fastapi import UploadFile, status
# from starlette.datastructures import UploadFile
from sqlalchemy.orm import Session 
from typing import Optional, Union, List
import os, uuid

from database.core import get_db
from services.authService import get_password_hash
from models.r_schema import (RestaurantCreate, Restaurant, RestaurantStatusUpdate)
from models.r_model import (Restaurant as RestaurantModel)
from .service import get_current_restaurant, get_restaurant_status_by_id
from services.authService import get_current_user_or_restaurant
from dotenv import load_dotenv
import json


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
def get_all_restaurants(
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client),
    location: Optional[str] = Query(None, description="Optional filter by city/location")
    ):
    # restaurants = db.query(RestaurantModel).all()
    query = db.query(RestaurantModel)
    if location:
        query = query.filter(
            RestaurantModel.location.ilike(f"%{location}%")
        )
    
    db_restaurants = query.all()
    final_restaurants = []
    for rest in db_restaurants:
        # Get the status from Redis/DB using the caching utility
        status_data = get_restaurant_status_by_id(db, redis_client, rest.id)
        
        # Create a dictionary from the SQLAlchemy object
        rest_dict = rest.__dict__
        
        # Inject the status fields from the cache/DB lookup
        if status_data:
            rest_dict['operating_status'] = status_data['operating_status']
            rest_dict['kitchen_status'] = status_data['kitchen_status']
            rest_dict['delivery_status'] = status_data['delivery_status']
        
        # NOTE: Pydantic's from_attributes=True handles most of the mapping, 
        # but manual modification is needed to inject the status fields if they are not loaded by default.
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


@router.patch("/status", response_model=Restaurant)
def update_restaurant_status(
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
    # Store the JSON string in Redis (Set a 1 hour TTL - Time To Live)
    redis_client.set(cache_key, json.dumps(status_data), ex=3600) 
    return current_restaurant


@router.get("/me", response_model=Restaurant)
def get_my_restaurant_details(
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves the details for the current authenticated restaurant owner.
    """
    return current_restaurant



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


