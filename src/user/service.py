from fastapi import Depends, HTTPException, status
from typing import Annotated


from ..services.authService import get_current_user_or_restaurant 
from ..models.r_schema import (UserCreate, User)
from ..models.r_model import (User as UserModel)

def get_current_user(entity: Annotated[UserModel, Depends(get_current_user_or_restaurant)]):
    """Dependency to get a regular user."""
    if not isinstance(entity, UserModel):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a user to access this resource."
        )
    return entity