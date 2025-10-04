
# models/r_model.py

from sqlalchemy import ForeignKey, String, Float, DateTime, func, BigInteger, UUID, Identity
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.core import Base
from datetime import datetime
from typing import Optional
import uuid # For default UUID generation

class User(Base):
    __tablename__ = "users"
    
    # Use BIGINT and Identity for PostgreSQL SERIAL behavior
    id: Mapped[int] = mapped_column( BigInteger, Identity(start=1, always=True), primary_key=True)
    # Use UUID for collision-resistant unique identifiers
    table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=func.gen_random_uuid(), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(128), nullable=False) # Increased size for hashed passwords
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    is_hotel_owner: Mapped[bool] = mapped_column(default=False)
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")

class Restaurant(Base):
    __tablename__ = "restaurants"
    
    id: Mapped[int] = mapped_column( BigInteger, Identity(start=1, always=True), primary_key=True)
    table_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=func.gen_random_uuid(), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str] = mapped_column(String(255), nullable=True)
    mobile_number: Mapped[str] = mapped_column(String(20), nullable=False)
    gstIN: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    operating_status: Mapped[str] = mapped_column(String(20), default="Open")
    kitchen_status: Mapped[str] = mapped_column(String(20), default="Normal")
    delivery_status: Mapped[str] = mapped_column(String(20), default="Active")
    support_email: Mapped[str] = mapped_column(String(100), nullable=False)
    announcement_text: Mapped[str | None] = mapped_column(String(1000), nullable=True)


    # Relationships
    cuisines = relationship("Cuisine", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
    feedbacks = relationship("Feedback", back_populates="restaurant")

class Cuisine(Base):
    __tablename__ = "cuisines"
    
    id: Mapped[int] = mapped_column( BigInteger, Identity(start=1, always=True), primary_key=True)
    cuisine_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # --- NEW PRICE FIELDS ---
    price_half: Mapped[float] = mapped_column(Float, nullable=True) 
    # Full price is the default required price
    price_full: Mapped[float] = mapped_column(Float, nullable=False) 
    
    # --- NEW CATEGORY FIELD --- (e.g., 'Veg', 'Non-Veg', 'Egg')
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    restaurant_specific_cuisine_id: Mapped[int] = mapped_column(BigInteger, nullable=True) 
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="cuisines")


class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column( BigInteger, Identity(start=1, always=True), primary_key=True)
    items: Mapped[str] = mapped_column(String(1024), nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    order_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # NEW COLUMN: Delivery Status
    # Possible values: 'Pending', 'Preparing', 'Ready', 'Delivered', 'Cancelled'
    status: Mapped[str] = mapped_column(String(20), default="Pending", nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    restaurant = relationship("Restaurant", back_populates="orders")

class Feedback(Base):
    __tablename__ = "feedbacks"
    
    id: Mapped[int] = mapped_column( BigInteger, Identity(start=1, always=True), primary_key=True)
    comments: Mapped[str | None] = mapped_column(String(500), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    
    # Relationships
    user = relationship("User", back_populates="feedbacks")
    restaurant = relationship("Restaurant", back_populates="feedbacks")

    