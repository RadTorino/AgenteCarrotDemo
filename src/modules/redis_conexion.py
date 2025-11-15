from redis import Redis
from typing import Optional
from src.utils.settings import settings

_redis_client: Optional[Redis] = None

def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            decode_responses=True,
            username=settings.REDIS_USERNAME,
            password=settings.REDIS_PASSWORD
        )
    return _redis_client