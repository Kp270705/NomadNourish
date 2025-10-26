from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime 
from uuid import UUID

# Base schemas for creating and updating data

DietaryCategory = Literal["Veg", "Non-Veg", "Egg"]
OrderStatus = Literal["Pending", "Preparing", "Ready", "Delivered", "Cancelled"]

# restro status: 
OperatingStatus = Literal["Open", "Closed"]
KitchenStatus = Literal["Normal", "Busy", "Emergency"]
DeliveryStatus = Literal["Active", "Inactive"]


# Cuisines: 
class CuisineBase(BaseModel):
    cuisine_name: str
    price_full: float = Field(...) # Must be greater than zero
    price_half: Optional[float] = Field(None)
    category: DietaryCategory

class CuisineInfo(BaseModel):
    cuisine_name: str

    class Config:
        from_attributes = True


# Feedbacks:
class FeedbackBase(BaseModel):
    comments: Optional[str] = None
    rating: Optional[float] = None


# Orders:
class OrderItemBase(BaseModel):
    cuisine_id: int
    quantity: int = Field(gt=0) # Must be at least 1
    size: Literal["half", "full"]

# Restaurants:
class RestaurantBase(BaseModel):
    name: str
    location: str
    mobile_number: str
    gstIN: str
    support_email: EmailStr
    announcement_text: Optional[str] = None


# Users:
class UserBase(BaseModel):
    username: str
    email: EmailStr
    location: Optional[str] = None
    current_location: Optional[str] = None

# =======================================

# Schemas for creating new objects (e.g., in a POST request)

# Cuisines:
class CuisineCreate(CuisineBase):
    pass


# Feedbacks:
class FeedbackCreate(FeedbackBase):
    order_id: int


# Orders 
class OrderCreate(BaseModel):
    items: List[OrderItemBase]
    client_total_price: float = Field(..., gt=0) # Must be greater than zero

# Restaurants:
class RestaurantCreate(RestaurantBase):
    password: str

# Users:
class UserCreate(UserBase):
    password: str



# ========================================

# schemas for updating existing objects (e.g., in a PUT request)

# New schema for updating a cuisine
class CuisineUpdate(BaseModel):
    cuisine_name: Optional[str] = None
    price_full: Optional[float] = Field(None)
    price_half: Optional[float] = Field(None)
    category: Optional[DietaryCategory] = None

class RestaurantUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    announcement_text: Optional[str] = None

class RestaurantStatusUpdate(BaseModel):
    operating_status: Optional[OperatingStatus] = None
    kitchen_status: Optional[KitchenStatus] = None
    delivery_status: Optional[DeliveryStatus] = None

class UserUpdate(UserBase):
    name: Optional[str] = None
    image_url: Optional[str] = None
    current_location: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    new_status: OrderStatus

# ======================================

# Schemas for API responses (e.g., in a GET request)


# Cuisines:
class Cuisine(CuisineBase):
    id: int
    restaurant_id: int
    restaurant_specific_cuisine_id: Optional[int] = None  # New field for restaurant-specific ID
    is_active: bool
    
    class Config:
        from_attributes = True


# Feedbacks:
class Feedback(FeedbackBase):
    id: int
    restaurant_id: int
    order_id: int
    user_id: int

    class Config:
        from_attributes = True


# Orders:
class OrderItem(BaseModel):
    id: int
    quantity: int
    size: Literal["half", "full"]
    price_at_purchase: float
    cuisine: CuisineInfo

    class Config:
        from_attributes = True

class Order(BaseModel):
    id: int
    user_id: int
    restaurant_id: int
    status: OrderStatus
    total_price: float # backend calculated price 
    # The response should contain the list of structured items from the database relationship
    order_items: List[OrderItem] 

    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    restaurant_name: str
    restaurant_id: int
    order_date: str
    status: OrderStatus # Add the new status field
    total_price: float
    order_items: List[OrderItem]
    cancelled_by: Optional[str] = None
    
    class Config:
        from_attributes = True


# Restaurants:
class RestaurantOverview(BaseModel):
    name: str
    ratings: Optional[float] = 0.0 # Optional and with a default value
    location: str

class Restaurant(RestaurantBase):
    id: int
    operating_status: str
    kitchen_status: str
    delivery_status: str
    image_url: Optional[str] = None
    table_id: Optional[UUID] = None 

    class Config:
        from_attributes = True

class RestaurantMenuResponse(BaseModel):
    restaurant_name: str
    restaurant_location: str
    cuisines: List[Cuisine]

class RestaurantAnalytics(BaseModel):
    total_revenue: float
    total_orders: int
    average_order_value: float
    top_selling_items: List[Dict[str, Any]]
    top_revenue_items: List[Dict[str, Any]]
    revenue_by_day: List[Dict[str, Any]]

   

# stats:
class AppStats(BaseModel):
    total_customers: int
    total_restaurants: int
    total_orders: int


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
    table_id: Optional[UUID] = None
    current_location: Optional[str] = None

    class Config:
        from_attributes = True

class UserInfoForOrder(BaseModel):
    username: str
    class Config:
        from_attributes = True

class OrderForRestaurantResponse(BaseModel):
    id: int
    order_date: datetime 
    status: OrderStatus
    total_price: float
    user: UserInfoForOrder         
    order_items: List[OrderItem] 
    # cancelled_by: Optional[str] = None

    class Config:
        from_attributes = True

 