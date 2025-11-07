# src/search/controller.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional

from database.core import get_db
from models.r_model import Restaurant as RestaurantModel, Cuisine as CuisineModel
from models.r_schema import SearchResponse, SearchSuggestion, Restaurant
from cache.redis_client import get_redis_client
from restaurant.service import get_restaurant_status_by_id

router = APIRouter(
    prefix='/search',
    tags=['search']
)

# ... other imports ...

@router.get("/suggestions", response_model=SearchResponse)
def get_search_suggestions(
    query: str = Query(..., min_length=2),
    location: Optional[str] = Query(None, description="Optional: Filter by user's location"), # +++ ADD LOCATION
    db: Session = Depends(get_db)
):
    search_term = f"%{query}%"

    # --- 1. Search for matching restaurants ---
    restaurant_query = db.query(RestaurantModel).filter(
        RestaurantModel.name.ilike(search_term)
    )
    if location:
        locations_list = [loc.strip() for loc in location.split(',') if loc.strip()]
        location_conditions = [RestaurantModel.location.ilike(f"%{loc}%") for loc in locations_list]
        if location_conditions:
            restaurant_query = restaurant_query.filter(or_(*location_conditions))
    db_restaurants = restaurant_query.limit(5).all()

    # --- 2. Search for matching dishes ---
    dish_query = db.query(CuisineModel).filter(
        CuisineModel.cuisine_name.ilike(search_term),
        CuisineModel.is_active == True
    )
    if location:
        locations_list = [loc.strip() for loc in location.split(',') if loc.strip()]
        location_conditions = [RestaurantModel.location.ilike(f"%{loc}%") for loc in locations_list]
        
        if location_conditions:
            dish_query = dish_query.join(RestaurantModel).filter(or_(*location_conditions))
    db_dishes = dish_query.with_entities(CuisineModel.cuisine_name).distinct().limit(10).all()

    restaurant_suggestions = [ SearchSuggestion( type="restaurant", id=rest.id, name=rest.name, image_url=rest.image_url ) for rest in db_restaurants ]
    dish_suggestions = [ SearchSuggestion( type="dish", name=dish_name[0] ) for dish_name in db_dishes ]
    return SearchResponse(restaurants=restaurant_suggestions, dishes=dish_suggestions)


@router.get("/results", response_model=List[Restaurant])
async def get_search_results(
    query: str = Query(..., description="The exact dish or category name"),
    location: Optional[str] = Query(None, description="Optional: Filter by user's location"),
    db: Session = Depends(get_db),
    redis_client = Depends(get_redis_client)
):
    search_term = f"%{query}%"

    # --- Find matching cuisine IDs first ---
    cuisine_query = db.query(CuisineModel.restaurant_id).filter(
        CuisineModel.cuisine_name.ilike(search_term),
        CuisineModel.is_active == True
    )

    if location:
        print(f"\n\tFiltering cuisines by location: {location}")
        # --- START FIX ---
        # Split the location string by comma
        locations_list = [loc.strip() for loc in location.split(',') if loc.strip()]
        
        # Create a list of ILIKE conditions
        location_conditions = [RestaurantModel.location.ilike(f"%{loc}%") for loc in locations_list]
        
        if location_conditions:
            # Join with Restaurant and apply the OR conditions
            cuisine_query = cuisine_query.join(RestaurantModel).filter(or_(*location_conditions))
        # --- END FIX ---

    restaurant_ids = cuisine_query.distinct().all()
    restaurant_ids_list = [id[0] for id in restaurant_ids]
    print(f"\n\tFound restaurant IDs matching cuisine '{query}': {restaurant_ids_list}")

    if not restaurant_ids_list:
        return []

    # Fetch the restaurants
    db_restaurants = db.query(RestaurantModel).filter(
        RestaurantModel.id.in_(restaurant_ids_list)
    ).all()

    # ... (Rest of your code to add Redis status is correct)
    final_restaurants = []
    for rest in db_restaurants:
        status_data = await get_restaurant_status_by_id(db, redis_client, rest.id)
        rest_pydantic = Restaurant.model_validate(rest)
        rest_dict = rest_pydantic.model_dump()
        if status_data:
            rest_dict.update(status_data)
        final_restaurants.append(rest_dict)

    return final_restaurants

