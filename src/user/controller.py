from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from typing import Optional
import os, uuid
from sqlalchemy.orm import Session 

from google.oauth2 import service_account
from google.cloud import storage

from database.core import get_db
from .service import get_current_user
from services.authService import get_password_hash
from models.r_schema import (UserCreate, User)
from models.r_model import (User as UserModel)


router = APIRouter(
    prefix='/user',
    tags=['user']
)

from dotenv import load_dotenv

load_dotenv()
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_BUCKET_NAME = os.getenv("GCP_BUCKET_NAME")
GCP_APPLICATION_CREDENTIALS = os.getenv("GCP_APPLICATION_CREDENTIALS")

router = APIRouter(
    prefix='/user',
    tags=['user']
)

# --- Google Cloud Storage Setup (copy from restaurant/controller.py) ---
try:
    credentials = service_account.Credentials.from_service_account_file(GCP_APPLICATION_CREDENTIALS)
    storage_client = storage.Client(project=GCP_PROJECT_ID, credentials=credentials)
    bucket = storage_client.bucket(GCP_BUCKET_NAME)
except Exception as e:
    print(f"Error initializing Google Cloud Storage client: {e}")
    storage_client = None
    bucket = None


@router.post("/register", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=409, detail="User already registered, enter unique name or email_id")
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(
        username=user.username,
        email=user.email,
        location=user.location,
        current_location=user.location,
        password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


# In src/user/controller.py

@router.patch("/me", response_model=User)
async def update_user_details(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    # We use Form data to accept text and files
    username: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    current_location: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """
    Update the authenticated user's profile details.
    """
    if not isinstance(current_user, UserModel):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update text fields if they were provided
    if username is not None:
        current_user.username = username

    if location is not None:
        current_user.location = location
        # print(f"\n\tUpdated location to: {location}")

    if current_location is not None:
        current_user.current_location = current_location
        print(f"\n\tUpdated current_location to: {current_location}")

    # Handle image upload to GCP
    if image is not None:
        if not image.filename:
            raise HTTPException(status_code=400, detail="Invalid image file.")
        
        if not storage_client or not bucket:
            raise HTTPException(status_code=500, detail="Cloud Storage not configured.")
        
        try:
            file_ext = os.path.splitext(image.filename)[1]
            unique_name = f"user_profiles/{uuid.uuid4()}{file_ext}" # Store in a folder
            blob = bucket.blob(unique_name)

            image.file.seek(0)
            blob.upload_from_file(image.file, content_type=image.content_type)
            
            # Update the user's image_url
            current_user.image_url = blob.public_url
        
        except Exception as e:
            print(f"Error uploading user image: {e}")
            raise HTTPException(status_code=500, detail="Failed to upload image.")

    db.commit()
    db.refresh(current_user)
    
    # We must return the updated user object as a dictionary
    # so it matches the Pydantic 'User' response model
    user_data = User.model_validate(current_user).model_dump()
    return user_data


@router.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


