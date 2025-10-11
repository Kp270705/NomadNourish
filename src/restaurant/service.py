from fastapi import Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session
import json
from cache.redis_client import get_redis_client
from redis.asyncio import Redis

from services.authService import get_current_user_or_restaurant 
from models.r_model import (Restaurant as RestaurantModel)


def get_current_restaurant(entity: Annotated[RestaurantModel, Depends(get_current_user_or_restaurant)]):
    print(f"\n\n\tIn GCR...")
    """Dependency to get a restaurant owner."""
    if not isinstance(entity, RestaurantModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a restaurant owner to access this resource."
        )
    return entity


# via redis 
async def get_restaurant_status_by_id(db: Session, redis_client: Redis, restaurant_id: int):

    """
    Implements the Cache-Aside READ strategy.
    """
    cache_key = f"status:restaurant:{restaurant_id}"
    
    # 1. Check Cache (Fast Read)
    cached_status = await redis_client.get(cache_key)
    
    # Explicitly check for None instead of just `if cached_status:`
    # Also, remove the unnecessary str() conversion.
    if cached_status is not None:
        return json.loads(cached_status)

    # 2. Cache Miss: Read from PostgreSQL (Slow Read)
    # This part of the code is correct and only runs if the cache is empty.
    db_restaurant = db.query(RestaurantModel).filter(
        RestaurantModel.id == restaurant_id
    ).first()

    if not db_restaurant:
        return None # Restaurant not found

    # 3. Write back to Redis (Refill Cache)
    status_data = {
        "operating_status": db_restaurant.operating_status,
        "kitchen_status": db_restaurant.kitchen_status,
        "delivery_status": db_restaurant.delivery_status,
    }

    print(f"\n\n\tStatus Data to cache: {status_data}\n\n")
    
    status_json = json.dumps(status_data)
    await redis_client.set(cache_key, status_json, ex=3600) # 1 hour TTL
    
    return status_data



