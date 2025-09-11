from fastapi import Depends, HTTPException, status
from typing import Annotated


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