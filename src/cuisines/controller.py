from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
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
    # Fast Food and Snacks
    "Momos":    { "id": "cat1", "image": "https://placehold.co/100x100/CB6555/FFFFFF?text=Momos" },
    "Noodles":  { "id": "cat2", "image": "https://placehold.co/100x100/5203FF/FFFFFF?text=Noodles" },
    "Pizzas":   { "id": "cat3", "image": "https://placehold.co/100x100/BCCF57/FFFFFF?text=Pizzas" },
    "Pastas":   { "id": "cat4", "image": "https://placehold.co/100x100/9AFF03/FFFFFF?text=Pastas" },
    "Burgers":   { "id": "cat5", "image": "https://placehold.co/100x100/9AFF03/FFFFFF?text=Burgers" },
    "Snacks":   { "id": "cat6", "image": "https://placehold.co/100x100/D7AC3E/FFFFFF?text=Snacks" },
    "Chaat":   { "id": "cat7", "image": "https://placehold.co/100x100/A5833E/FFFFFF?text=Chaat" },
    "Street Food":   { "id": "cat8", "image": "https://placehold.co/100x100/C1AC3E/FFFFFF?text=Street Food" },

    # Foreign Famous Cuisines:
    "Cheese":   { "id": "cat9", "image": "https://placehold.co/100x100/FFB303/FFFFFF?text=Cheese" },
    "Nachos":   { "id": "cat10", "image": "https://placehold.co/100x100/FC6F03/FFFFFF?text=Nachos" },
    "Shwarma":   { "id": "cat11", "image": "https://placehold.co/100x100/FF943E/FFFFFF?text=Shwarma" },

    # Regular Categories
    "Paneer":   { "id": "cat12", "image": "https://placehold.co/100x100/A6AfA4/FFFFFF?text=Paneer" },
    "Egg":   { "id": "cat13", "image": "https://placehold.co/100x100/E1D7A4/FFFFFF?text=Egg" },
    "Chicken":   { "id": "cat14", "image": "https://placehold.co/100x100/FB472B/FFFFFF?text=Chicken" },
    "Non-Veg":   { "id": "cat15", "image": "https://placehold.co/100x100/FFDD03/FFFFFF?text=Non-Veg" },
    "Biryani":   { "id": "cat16", "image": "https://placehold.co/100x100/FFDD03/FFFFFF?text=Biryani" },
    "Rice":   { "id": "cat17", "image": "https://placehold.co/100x100/E1F1F9/FFFFFF?text=Rice" },

    # Sweet Dishes
    "Cakes":    { "id": "cat18", "image": "https://placehold.co/100x100/E8A66E/FFFFFF?text=Cakes" },
    "Deserts":   { "id": "cat19", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Deserts" },
    "Ice Creams":   { "id": "cat20", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Ice Creams" },

    # Beverages and Drinks
    "Shakes":   { "id": "cat21", "image": "https://placehold.co/100x100/7E7360/FFFFFF?text=Shakes" },
    "Juices":   { "id": "cat22", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Juices" },
    "Cold Drinks":   { "id": "cat23", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Cold Drinks" },
    "Beverages":   { "id": "cat24", "image": "https://placehold.co/100x100/6EE8D8/FFFFFF?text=Beverages" },
}

@router.get( "/categories", response_model=List[CuisineCategory], )
async def get_cuisine_categories_for_user(
    location: Optional[str] = Query(None, description="Optional: Filter categories by user's location"),
    db: Session = Depends(get_db)
):
    print(f"GET /cuisine/categories hit. Location: {location}")

    restaurant_query = db.query(RestaurantModel.id).filter(
        RestaurantModel.operating_status == "Open"
    )
    if location:
        locations_list = [loc.strip() for loc in location.split(',') if loc.strip()]
        location_conditions = [RestaurantModel.location.ilike(f"%{loc}%") for loc in locations_list]
        
        if location_conditions:
            restaurant_query = restaurant_query.filter(or_(*location_conditions))
    
    matching_restaurant_ids = [id for (id,) in restaurant_query.all()]

    if not matching_restaurant_ids:
        db_categories_tuples = []
    else:
        query = db.query(CuisineModel.cuisine_type).filter(
            CuisineModel.restaurant_id.in_(matching_restaurant_ids),
            CuisineModel.cuisine_type != None,
            CuisineModel.is_active == True
        )
        db_categories_tuples = query.distinct().all()

    active_categories_from_db = {category for (category,) in db_categories_tuples}
    
    final_cuisine_types = []
    for name, details in category_details_lookup.items():
        if name in active_categories_from_db:
            final_cuisine_types.append({
                "id": details["id"],
                "name": name,
                "image": details["image"]
            })
    
    return final_cuisine_types

