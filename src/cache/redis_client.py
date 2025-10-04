# src/cache/redis_client.py

import os
import redis
from dotenv import load_dotenv

load_dotenv()

# Get Redis configuration from environment variables
REDIS_HOST = os.getenv("UPSTASH_REDIS_REST_URL", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("UPSTASH_REDIS_REST_TOKEN")

# Create and export the Redis client instance
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        decode_responses=True # Decode responses to get strings instead of bytes
    )
    # Simple check to ensure connection works
    redis_client.ping()
    print("✅ Redis connection successful!")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    redis_client = None

def get_redis_client():
    """Dependency to provide the Redis client."""
    if redis_client is None:
        raise Exception("Redis connection is not available.")
    return redis_client
