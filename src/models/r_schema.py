from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Base schemas for creating and updating data

# Cuisines: 
class CuisineBase(BaseModel):
    cuisine_name: str
    cuisine_price: float


# Feedbacks:
class FeedbackBase(BaseModel):
    comments: str
    rating: float


# Orders:
class OrderBase(BaseModel):
    items: List[str]
    total_price: float


# Restaurants:
class RestaurantBase(BaseModel):
    name: str
    location: str
    mobile_number: str
    gstIN: str


# Users:
class UserBase(BaseModel):
    username: str
    email: EmailStr


# =======================================

# Schemas for creating new objects (e.g., in a POST request)

# Cuisines:
class CuisineCreate(CuisineBase):
    pass

# Restaurants:
class RestaurantCreate(RestaurantBase):
    password: str

# Users:
class UserCreate(UserBase):
    password: str



# ========================================

# schemas for updating existing objects (e.g., in a PUT request)

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    image_url: Optional[str] = None

class UserUpdate(UserBase):
    name: Optional[str] = None
    image_url: Optional[str] = None

# ======================================

# Schemas for API responses (e.g., in a GET request)


# Cuisines:
class Cuisine(CuisineBase):
    id: int
    restaurant_id: int
    restaurant_specific_cuisine_id: Optional[int] = None  # New field for restaurant-specific ID

    class Config:
        from_attributes = True

class RestaurantMenuResponse(BaseModel):
    restaurant_name: str
    restaurant_location: str
    cuisines: List[Cuisine]


# Feedbacks:
class Feedback(FeedbackBase):
    id: int
    restaurant_id: int
    order_id: int
    user_id: int

    class Config:
        from_attributes = True


# Orders:
class Order(OrderBase):
    id: int
    user_id: int
    restaurant_id: int
    order_date: str

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id:int
    items:str
    total_price:float
    restaurant_id: int
    restaurant_name: str # Add this new field
    order_date: str

    class Config:
        from_attributes = True

# Users & Restaurants:
class RestaurantOverview(BaseModel):
    name: str
    ratings: Optional[float] = 0.0 # Optional and with a default value
    location: str

class Restaurant(RestaurantBase):
    id: int
    image_url: Optional[str] = None
    table_id: Optional[str] = None

    class Config:
        from_attributes = True


# Tokens: 
class Token(BaseModel):
    message:str
    user_type: str
    access_token: str
    token_type: str
    user_details: list[str]

class TokenData(BaseModel):
    username: str | None = None


# Users: 
class User(UserBase):
    id: int
    image_url: Optional[str] = None
    table_id: Optional[str] = None

    class Config:
        from_attributes = True