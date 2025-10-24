# src/cache/redis_client.py

import os
from dotenv import load_dotenv
import redis.asyncio as redis # Use the standard asyncio redis library

load_dotenv()

# This is the new URL you get from the Upstash dashboard
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL") 
redis_client = None

if UPSTASH_REDIS_REST_URL:
    try:
        # Create an async client from the URL
        redis_client = redis.from_url(UPSTASH_REDIS_REST_URL, decode_responses=True)
        print("✅ Standard Redis connection pool created.")
    except Exception as e:
        print(f"❌ Could not create Redis connection pool: {e}")
else:
    print("❌ UPSTASH_REDIS_REST_URL environment variable not set.")


async def get_redis_client():
    """Async dependency to provide the Redis client."""
    if redis_client is None:
        raise Exception("Redis client is not available.")
    
    # Simple check to ensure connection works
    try:
        redis_client.ping()
        # await redis_client.ping()
    except Exception as e:
         raise Exception(f"Could not connect to Redis: {e}")
         
    return redis_client