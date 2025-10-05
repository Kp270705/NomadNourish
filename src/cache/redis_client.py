# src/cache/redis_client.py (FINAL VERSION)

import os
from dotenv import load_dotenv
# --- REPLACE standard 'redis' with 'upstash_redis' ---
from upstash_redis import Redis 

load_dotenv()

# The client is initialized once, reading URL and Token from the environment.
# Note: Upstash handles string/bytes decoding internally.
try:
    # Use the synchronous client and auto-load credentials
    redis_client = Redis.from_env() 
    
    # Simple check to ensure connection works (using a simple set/get instead of ping for REST clients)
    redis_client.set('connection_test', 'success')
    if redis_client.get('connection_test') == 'success':
        print("✅ Upstash Redis connection successful!")
        redis_client.delete('connection_test')
    else:
        raise Exception("Connection test failed after ping/set.")
        
except Exception as e:
    print(f"❌ Upstash Redis connection failed: {e}")
    # Note: Upstash Redis is built for REST, so it usually throws exceptions on call, 
    # but this structure is best for checking the initial setup.
    redis_client = None

def get_redis_client():
    """Dependency to provide the Redis client."""
    if redis_client is None:
        # Halt the app if the critical cache service is unavailable
        raise Exception("Upstash Redis connection is not available.")
    return redis_client