from fastapi import APIRouter, Depends, HTTPException, Form, File
from fastapi import UploadFile, status
# from starlette.datastructures import UploadFile
from sqlalchemy.orm import Session 
from typing import Optional, Union, List
import os, uuid

from database.core import get_db
from services.authService import get_password_hash
from models.r_schema import (RestaurantCreate, Restaurant, RestaurantStatusUpdate)
from models.r_model import (Restaurant as RestaurantModel)
from .service import get_current_restaurant
from services.authService import get_current_user_or_restaurant
from dotenv import load_dotenv


# For Google Cloud Storage
from google.oauth2 import service_account
from google.cloud import storage
from google.api_core import exceptions

load_dotenv()
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
GCP_APPLICATION_CREDENTIALS = os.getenv("GCP_APPLICATION_CREDENTIALS")
# print(f"\n\n\tgcp creds: {GCP_APPLICATION_CREDENTIALS}")
# print(f"\n\n\tgcp bucket name: {GCP_BUCKET_NAME}")
# print(f"\n\n\tgcp project_id: {GCP_PROJECT_ID}")

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
def get_all_restaurants(db: Session = Depends(get_db)):
    restaurants = db.query(RestaurantModel).all()
    
    restaurant_list = []
    for r in restaurants:
        restaurant_list.append({
            "id": r.id,
            "name": r.name,
            "location": r.location,
            "mobile_number": r.mobile_number if r.mobile_number is not None else "",
            "image_url": r.image_url if r.image_url is not None else "",
            "gstIN": r.gstIN if r.gstIN is not None else "",
            "support_email": r.support_email if r.support_email is not None else "",
            "table_id": r.table_id if r.table_id is not None else "",
        })
        
    return restaurant_list


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


