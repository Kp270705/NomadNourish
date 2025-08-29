from sqlalchemy import inspect, text
from core import engine

def add_column_if_not_exists():
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("restaurants")]
    if "owner_name" not in columns:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE restaurants ADD COLUMN owner_name VARCHAR"))
            conn.commit()

add_column_if_not_exists()
