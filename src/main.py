from fastapi import FastAPI


from database.core import engine, Base
from api import register_routes


# ==========================================================

Base.metadata.create_all(bind=engine)
app = FastAPI()
register_routes(app)
