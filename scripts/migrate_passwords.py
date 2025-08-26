import sys
import os

# Add the project directory to the Python path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from passlib.context import CryptContext

# ✅ Correct
from src.database.core import get_db, Base, engine
from src.models.r_model import User as UserModel
from src.models.r_model import Restaurant as RestaurantModel


# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)


def is_password_hashed(password):
    """
    Checks if a password string is likely a bcrypt hash.
    Bcrypt hashes usually start with '$2b$', '$2a$', or '$2y$'.
    """
    return password.startswith(("$2b$", "$2a$", "$2y$"))

def migrate_passwords():
    print("Starting password migration for users...")
    db: Session
    for db in get_db():
        # Migrate users
        users = db.query(UserModel).all()
        for user in users:
            # Check if the password is already hashed to avoid re-hashing
            if not is_password_hashed(user.password):
                print(f"Hashing password for user: {user.username}")
                user.password = get_password_hash(user.password)

        # Migrate restaurants
        restaurants = db.query(RestaurantModel).all()
        for restaurant in restaurants:
            # Check if the password is already hashed to avoid re-hashing
            if not is_password_hashed(restaurant.password):
                print(f"Hashing password for restaurant: {restaurant.name}")
                restaurant.password = get_password_hash(restaurant.password)

        db.commit()
        print("Migration complete. All passwords are now hashed.")
        break  # Exit the loop after one successful migration

if __name__ == "__main__":
    migrate_passwords()