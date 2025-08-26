from fastapi import FastAPI

from auth.controller import router as auth_router
from restaurant.controller import router as restaurant_router
from user.controller import router as users_router 


def register_routes(app: FastAPI):
    app.include_router(auth_router)
    app.include_router(restaurant_router)
    app.include_router(users_router)