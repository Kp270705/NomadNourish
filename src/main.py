from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Annotated
import os
from dotenv import load_dotenv

from database.core import engine, Base, get_db
from models.r_schema import (
    UserCreate, User, RestaurantCreate, Restaurant,
    Token, TokenData, CuisineBase, Cuisine, CuisineCreate
)
from models.r_model import User as UserModel
from models.r_model import Restaurant as RestaurantModel
from models.r_model import Cuisine as CuisineModel

# ==========================================================
# ❌❌❌
# 🔑 JWT & Password setup 
SECRET_KEY=str(os.environ.get('SECRET_KEY'))
ALGORITHM=str(os.environ.get('ALGORITHM', 'HS256'))
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Use a single token URL for both user and restaurant login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# ==========================================================
# 🔑 Unified Authentication Logic
# ❌❌
def get_current_user_or_restaurant(token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)):
    """
    Decodes the JWT token and returns the authenticated user or restaurant object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        is_restaurant = payload.get("is_restaurant", False)
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    if is_restaurant:
        entity = db.query(RestaurantModel).filter(RestaurantModel.name == username).first()
    else:
        entity = db.query(UserModel).filter(UserModel.username == username).first()

    if entity is None:
        raise credentials_exception
    
    return entity

def get_current_user(entity: Annotated[UserModel, Depends(get_current_user_or_restaurant)]):
    """Dependency to get a regular user."""
    if not isinstance(entity, UserModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a user to access this resource."
        )
    return entity

def get_current_restaurant(entity: Annotated[RestaurantModel, Depends(get_current_user_or_restaurant)]):
    """Dependency to get a restaurant owner."""
    if not isinstance(entity, RestaurantModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a restaurant owner to access this resource."
        )
    return entity


# ==========================================================


Base.metadata.create_all(bind=engine)
app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

# ==========================================================
# 🔹 UNIFIED LOGIN ENDPOINT
@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Unified login endpoint for both users and restaurants.
    """
    # Attempt to authenticate as a user
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if user and verify_password(form_data.password, user.password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "is_restaurant": False}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # If not a user, attempt to authenticate as a restaurant
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.name == form_data.username).first()
    if restaurant and verify_password(form_data.password, restaurant.password):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": restaurant.name, "is_restaurant": True}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    
    # If no match is found
    raise HTTPException(status_code=401, detail="Incorrect username or password")


# ==========================================================
# 🔹 USER APIs (Now Protected)

@app.post("/users", response_model=User)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(user.password)
    db_user = UserModel(username=user.username, email=user.email, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ==========================================================
# 🔹 RESTAURANT APIs (Now Protected)

@app.post("/restaurant", response_model=Restaurant)
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


@app.get("/restaurant/{restaurant_id}", response_model=Restaurant)
def get_restaurant(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    return restaurant

# ==========================================================
# 🔹 CUISINE APIs (Restaurant Protected)

@app.post("/cuisine", response_model=Cuisine)
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

@app.get("/cuisine", response_model=list[Cuisine])
def list_cuisines(db: Session = Depends(get_db)):
    return db.query(CuisineModel).all()