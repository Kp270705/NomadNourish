from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database.core import Base 

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)
    is_hotel_owner: Mapped[bool] = mapped_column(default=False)
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    feedbacks = relationship("Feedback", back_populates="user")
    
class Restaurant(Base):
    __tablename__ = "restaurants"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)
    location: Mapped[str] = mapped_column(String) 
    image_url: Mapped[str] = mapped_column(String, nullable=True)
    # Relationships
    cuisines = relationship("Cuisine", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")
    feedbacks = relationship("Feedback", back_populates="restaurant")

class Cuisine(Base):
    __tablename__ = "cuisines"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cuisine_name: Mapped[str] = mapped_column(String)
    cuisine_price: Mapped[float] = mapped_column(Float)
    
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))

    restaurant_specific_cuisine_id: Mapped[int] = mapped_column(Integer, nullable=True)  # New field for restaurant-specific ID
    
    # Relationships
    restaurant = relationship("Restaurant", back_populates="cuisines")

class Order(Base):
    __tablename__ = "orders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    items: Mapped[str] = mapped_column(String) # Storing a list as a string for simplicity, can be improved.
    total_price: Mapped[float] = mapped_column(Float)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    
    # Relationships
    user = relationship("User", back_populates="orders")
    restaurant = relationship("Restaurant", back_populates="orders")

class Feedback(Base):
    __tablename__ = "feedbacks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    comments: Mapped[str] = mapped_column(String)
    rating: Mapped[float] = mapped_column(Float)
    
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"))
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    
    # Relationships
    user = relationship("User", back_populates="feedbacks")
    restaurant = relationship("Restaurant", back_populates="feedbacks")