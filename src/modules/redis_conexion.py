from redis import Redis
from typing import Optional
import os
from dotenv import load_dotenv
load_dotenv()

_redis_client: Optional[Redis] = None

def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(
            host=os.getenv("REDIS_HOST"),
            port=int(os.getenv("REDIS_PORT")),
            decode_responses=True,
            username=os.getenv("REDIS_USERNAME"),
            password=os.getenv("REDIS_PASSWORD")
        )
    return _redis_client