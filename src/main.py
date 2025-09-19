from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.core import engine, Base
from api import register_routes


# ==========================================================

Base.metadata.create_all(bind=engine)
app = FastAPI()
origins = [
    "http://localhost.tiangolo.com",
    "https://localhost.tiangolo.com",
    "http://localhost:5173",
    "https://nomad-nourish-ui.vercel.app/"
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_routes(app)
