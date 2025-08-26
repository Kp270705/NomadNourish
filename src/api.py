from fastapi import FastAPI

from src.user.controller import router as users_router
from src.restaurant.controller import router as auth_router


def register_routes(app: FastAPI):
    app.include_router(auth_router)
    app.include_router(users_router)