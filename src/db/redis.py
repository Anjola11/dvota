
from redis.asyncio import Redis
from src.config import Config

# Initialize
redis_client = Redis.from_url(
    Config.REDIS_URL,
    decode_responses=True
)

async def check_redis_connection():
    try:
        await redis_client.ping()
        print("Redis connection established")
    except Exception as e:
        print(f"Redis connection failed: {e}")