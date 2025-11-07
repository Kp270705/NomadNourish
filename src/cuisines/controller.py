from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session 
from sqlalchemy import func
from typing import List
import os, uuid

from database.core import get_db
from models.r_schema import (CuisineCreate, Cuisine, RestaurantMenuResponse, CuisineUpdate, CuisineCategory)
from models.r_model import (Restaurant as RestaurantModel, Cuisine as CuisineModel)
from restaurant.service import get_current_restaurant



router = APIRouter(
    prefix='/cuisine',
    tags=['cuisine']
)

@router.post("/register", response_model=Cuisine)
def create_cuisine(
    cuisine: CuisineCreate,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    # 1. Find the highest existing restaurant_specific_cuisine_id for this restaurant
    max_id = db.query(func.max(CuisineModel.restaurant_specific_cuisine_id)).filter(
        CuisineModel.restaurant_id == current_restaurant.id
    ).scalar()
    new_cuisine_id = (max_id or 0) + 1

    # 3. Create the new Cuisine object with the calculated ID
    db_cuisine = CuisineModel(
        cuisine_name=cuisine.cuisine_name,
        price_half=cuisine.price_half,
        price_full=cuisine.price_full,
        category=cuisine.category,
        restaurant_id=current_restaurant.id,
        restaurant_specific_cuisine_id=new_cuisine_id
    )

    db.add(db_cuisine)
    db.commit()
    db.refresh(db_cuisine)
    return db_cuisine


@router.patch("/{cuisine_id}", response_model=Cuisine)
def update_cuisine(
    cuisine_id: int,
    cuisine_data: CuisineUpdate,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    print(f"\n\nReceived update request for cuisine ID {cuisine_id} of cuisine type: {cuisine_data.cuisine_type}\n\n")
    # Find the cuisine and verify it belongs to the current restaurant
    db_cuisine = db.query(CuisineModel).filter(
        CuisineModel.id == cuisine_id,
        CuisineModel.restaurant_id == current_restaurant.id
    ).first()

    if not db_cuisine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuisine not found or does not belong to this restaurant."
        )
    
    # Update fields if provided
    for key, value in cuisine_data.model_dump().items():
        if value is not None:
            print(f"\n\nUpdating {key} to {value}\n\n")
            setattr(db_cuisine, key, value)
    if db_cuisine.is_active == False:
        db_cuisine.is_active = True
    db.commit()
    db.refresh(db_cuisine)
    return db_cuisine


# 🔹 API to soft delete a cuisine
@router.patch("/deactivate/{cuisine_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_cuisine(
    cuisine_id: int,
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    # Find the cuisine and verify it belongs to the current restaurant
    db_cuisine = db.query(CuisineModel).filter(
        CuisineModel.id == cuisine_id,
        CuisineModel.restaurant_id == current_restaurant.id
    ).first()

    if not db_cuisine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cuisine not found or does not belong to this restaurant."
        )

    db_cuisine.is_active = False
    db.commit()
    return


@router.get("/get_all", response_model=list[Cuisine])
def list_cuisines(db: Session = Depends(get_db)):
    return db.query(CuisineModel).all()


#  New API to get a particular hotel's dishes
@router.get("/cuisines_by_restaurant_id/{restaurant_id}", response_model=RestaurantMenuResponse)
def get_restaurant_cuisines(restaurant_id: int, db: Session = Depends(get_db)):
    restaurant = db.query(RestaurantModel).filter(RestaurantModel.id == restaurant_id).first()
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found.")

    cuisines = db.query(CuisineModel).filter(CuisineModel.restaurant_id == restaurant_id, CuisineModel.is_active == True).all()
    
    # Combine the data into the new response schema
    return {
        "restaurant_name": restaurant.name,
        "restaurant_location": restaurant.location,
        "cuisines": cuisines
    }


# when restaurants create cuisine, this will show their existing cuisines: 
@router.get("/my-cuisines", response_model=List[Cuisine])
def get_my_cuisines(
    db: Session = Depends(get_db),
    current_restaurant: RestaurantModel = Depends(get_current_restaurant)
):
    """
    Retrieves all cuisines for the current authenticated restaurant.
    """
    cuisines = db.query(CuisineModel).filter(CuisineModel.restaurant_id == current_restaurant.id).all()
    return cuisines


category_details_lookup = {
    "Momos":    { "id": "cat1", "image": "https://placehold.co/100x100/E86E6E/FFFFFF?text=Momos" },
    "Noodles":  { "id": "cat2", "image": "https://placehold.co/100x100/5203FF/FFFFFF?text=Noodles" },
    "Pizzas":   { "id": "cat3", "image": "https://placehold.co/100x100/9AFF03/FFFFFF?text=Pizzas" },
    "Cakes":    { "id": "cat4", "image": "https://placehold.co/100x100/E8A66E/FFFFFF?text=Cakes" },
    "Biryani":  { "id": "cat5", "image": "https://placehold.co/100x100/8A6EE8/FFFFFF?text=Biryani" },
    "Non-Veg":  { "id": "cat6", "image": "https://placehold.co/100x100/E86EA6/FFFFFF?text=Non-Veg" },
    "Desert":   { "id": "cat7", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Desert" },
    "Paneer":   { "id": "cat8", "image": "https://placehold.co/100x100/FFDD03/FFFFFF?text=Paneer" },
    "Street Food":   { "id": "cat9", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Street Food" },
    "Nachos":   { "id": "cat10", "image": "https://placehold.co/100x100/FC6F03/FFFFFF?text=Nachos" },
    "Cheese":   { "id": "cat11", "image": "https://placehold.co/100x100/FFB303/FFFFFF?text=Cheese" },
    "Chicken":   { "id": "cat12", "image": "https://placehold.co/100x100/FC4903/FFFFFF?text=Chicken" },
}

@router.get(
    "/categories", 
    response_model=List[CuisineCategory], 
    tags=["Cuisine Categories (User)"] # <-- Naya tag, docs mein alag dikhega
)
async def get_cuisine_categories_for_user(db: Session = Depends(get_db)): # <-- DB dependency add ki
    """
    Yeh endpoint user ke homepage (Svelte) ke liye hai.
    Yeh database (Cuisine table) se *distinct* category names nikalega
    aur unhe images ke sath return karega.
    """
    print("GET /cuisine/categories hit (for user homepage)")
    db_categories_tuples = db.query(CuisineModel.cuisine_type).filter(
        CuisineModel.cuisine_type != None, CuisineModel.is_active == True
    ).distinct().all()
    
    # 2. Tuples ki list ko ek simple Set mein convert karo: {'Momos', 'Pizzas'}
    # Set fast lookups ke liye aacha hai
    active_categories_from_db = {category for (category,) in db_categories_tuples}
    print("\n\tActive categories from DB:", active_categories_from_db)
    
    # 3. Ab, hamare "lookup table" se filter karo
    # Sirf woh categories bhejo jo DB mein active hain
    final_categories = []
    for name, details in category_details_lookup.items():
        if name in active_categories_from_db:
            final_categories.append({
                "id": details["id"],
                "name": name,
                "image": details["image"]
            })
    
    return final_categories

