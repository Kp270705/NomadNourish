from fastapi import Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.orm import Session
import redis, json
from cache.redis_client import get_redis_client
from upstash_redis import Redis as UpstashRedisClient

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


def get_restaurant_status_by_id(db: Session, redis_client: UpstashRedisClient, restaurant_id: int):
    """
    Implements the Cache-Aside READ strategy.
    """
    cache_key = f"status:restaurant:{restaurant_id}"
    
    # 1. Check Cache (Fast Read)
    cached_status = redis_client.get(cache_key)
    if cached_status:
        return json.loads(str(cached_status))

    # 2. Cache Miss: Read from PostgreSQL (Slow Read)
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
    redis_client.set(cache_key, status_json, ex=3600) # 1 hour TTL
    
    return status_data