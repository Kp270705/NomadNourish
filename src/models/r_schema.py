from pydantic import BaseModel, EmailStr
from typing import Optional, List

# Base schemas for creating and updating data
class UserBase(BaseModel):
    username: str
    email: EmailStr
    
class RestaurantBase(BaseModel):
    name: str
    location: str

class CuisineBase(BaseModel):
    cuisine_name: str
    cuisine_price: float

class OrderBase(BaseModel):
    items: List[str]
    total_price: float

class FeedbackBase(BaseModel):
    comments: str
    rating: float

# Schemas for creating new objects (e.g., in a POST request)
class UserCreate(UserBase):
    password: str

class RestaurantCreate(RestaurantBase):
    password: str

# ================================================================


# Schemas for API responses (e.g., in a GET request)
class User(UserBase):
    id: int
    
    class Config:
        from_attributes = True

class Restaurant(RestaurantBase):
    id: int
    
    class Config:
        from_attributes = True

class Cuisine(CuisineBase):
    id: int
    restaurant_id: int

    class Config:
        from_attributes = True

class Order(OrderBase):
    id: int
    user_id: int
    restaurant_id: int

    class Config:
        from_attributes = True

class Feedback(FeedbackBase):
    id: int
    restaurant_id: int
    order_id: int
    user_id: int

    class Config:
        from_attributes = True

class RestaurantOverview(BaseModel):
    name: str
    ratings: Optional[float] = 0.0 # Optional and with a default value


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None


class CuisineCreate(CuisineBase):
    pass
