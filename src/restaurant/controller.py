from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session 
from sqlalchemy import func
from typing import Optional, Annotated, Union, List
import os, uuid

from database.core import get_db
from services.authService import get_password_hash
from models.r_schema import (RestaurantCreate, Restaurant, CuisineCreate, Cuisine)
from models.r_model import (Restaurant as RestaurantModel, Cuisine as CuisineModel)
from .service import get_current_restaurant
from dotenv import load_dotenv


# For Google Cloud Storage
from google.oauth2 import service_account
from google.cloud import storage
from google.api_core import exceptions

load_dotenv()
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
GCP_APPLICATION_CREDENTIALS = os.getenv("GCP_APPLICATION_CREDENTIALS")
print(f"\n\n\tgcp creds: {GCP_APPLICATION_CREDENTIALS}")

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
    db_restaurant = db.query(RestaurantModel).filter(RestaurantModel.name == restaurant.name).first()
    if db_restaurant:
        raise HTTPException(status_code=400, detail="Restaurant already exists")
    hashed_password = get_password_hash(restaurant.password)
    db_restaurant = RestaurantModel(name=restaurant.name, password=hashed_password, location=restaurant.location)
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

# used to edit restaurant details:
@router.patch("/update_details", response_model=Restaurant)
def update_restaurant_details(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant),
    name: str = Form(None),
    location: str = Form(None),
    image: Optional[Union[UploadFile, str]] = File(None)
):
    """
    Updates the current restaurant's details, including the image.
    """
    print(f"\n\n\tIn restro update details")
    if name:
        current_restaurant.name = name
    if location:
        current_restaurant.location = location

    if image and isinstance(image, UploadFile) and image.filename:
        if not storage_client or not bucket:
            raise HTTPException(status_code=500, detail="Google Cloud Storage is not configured properly.")

        if not image.filename:
            raise HTTPException(status_code=400, detail="Image has no name. Please select a valid image.")

        try:
            # Generate a unique filename to avoid conflicts
            file_extension = os.path.splitext(image.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # Create a new blob (file) in the GCS bucket
            blob = bucket.blob(unique_filename)

            # Upload the file content
            image.file.seek(0)
            blob.upload_from_file(image.file, content_type=image.content_type)

            # Get the public URL of the uploaded file
            public_url = blob.public_url

            current_restaurant.image_url = public_url

        except exceptions.GoogleAPICallError as e:
            print(f"GCS API Error: {e}")
            raise HTTPException(status_code=500, detail=f"An error occurred with Google Cloud Storage: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    db.commit()
    db.refresh(current_restaurant)
    return current_restaurant


@router.get("/get_all", response_model=List[Restaurant])
def get_all_restaurants(db: Session = Depends(get_db)):
    """
    Retrieves a list of all restaurants with their details.
    """
    restaurants = db.query(RestaurantModel).all()
    return restaurants


# ==========================================================
# 🔹 CUISINE APIs (Restaurant Protected)
# ... (all other restaurant routes) ...

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

    # 2. Set the new ID, handling the case of the first cuisine
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


@router.get("/cuisine/get_all", response_model=list[Cuisine])
def list_cuisines(db: Session = Depends(get_db)):
    return db.query(CuisineModel).all()


#  New API to get a particular hotel's dishes
@router.get("/get_cuisines_by_restaurant_id/{restaurant_id}", response_model=List[Cuisine])
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

