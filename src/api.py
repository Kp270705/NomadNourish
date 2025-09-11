from fastapi import FastAPI

from auth.controller import router as auth_router
from restaurant.controller import router as restaurant_router
from user.controller import router as users_router 
from cuisines.controller import router as cuisines_router
from orders.controller import router as orders_router


def register_routes(app: FastAPI):
    app.include_router(auth_router)
    app.include_router(restaurant_router)
    app.include_router(users_router)
    app.include_router(cuisines_router)
    app.include_router(orders_router)