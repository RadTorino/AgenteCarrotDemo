from src.modules.redis_conexion import get_redis_client
from datetime import timedelta
import uuid

class FileMappingService:
    PREFIX = "file_map:"
    TTL = timedelta(hours=2)
    
    def __init__(self):
        try:
            self.redis = get_redis_client()
        except Exception as e:
            print(f"Error connecting to Redis: {e}")
            self.redis = None
        
    def create_mapping(self, real_link: str) -> str | None:
        if not self.redis:
            return None
        file_id = f"FILE_{uuid.uuid4().hex[:8]}"
        self.redis.setex(
            f"{self.PREFIX}{file_id}",
            self.TTL,
            real_link
        )
        return file_id
    
    def get_link(self, file_id: str) -> str | None:
        if not self.redis or not file_id:
            return None
        link_bytes = self.redis.get(f"{self.PREFIX}{file_id}")
        return link_bytes