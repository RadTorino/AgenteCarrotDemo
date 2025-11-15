from datetime import timedelta, datetime
import json
from src.modules.redis_conexion import get_redis_client
from src.utils.logger import get_logger

logger = get_logger(__name__)
EXPIRATION_TIME = timedelta(hours=24)

class MemoryHandler:
    """Maneja la memoria conversacional de los clientes (threads activos)."""

    def __init__(self, expiration_time: timedelta = EXPIRATION_TIME):
        self.expiration_time = expiration_time
        self.redis_client = get_redis_client()

    def get_or_create_thread(self, client_number: str):
        """
        Devuelve el thread_id activo del cliente o crea uno nuevo si expiró o no existe.
        """
        thread_info_json = self.redis_client.get(client_number)
        thread_info = json.loads(thread_info_json) if thread_info_json else None

        if thread_info:
            last_activity_str = thread_info.get("last_activity")
            last_activity = datetime.fromisoformat(last_activity_str) if last_activity_str else None
            
            if not last_activity or datetime.now() - last_activity > self.expiration_time:
                logger.info(f"🕒 Conversación expirada para {client_number}. Reiniciando...")
                self.redis_client.delete(client_number)
                thread_id = None
            else:
                thread_id = thread_info.get("thread_id")
        else:
            thread_id = None

        return thread_id

    def update_thread_activity(self, client_number: str, thread_id: str):
        """
        Actualiza o crea la entrada de conversación con su timestamp.
        """
        thread_info = {
            "thread_id": thread_id,
            "last_activity": datetime.now().isoformat()
        }
        self.redis_client.set(client_number, json.dumps(thread_info))
        logger.info(f"💾 Memoria actualizada para {client_number} (thread {thread_id})")
        return thread_id

memory_handler = MemoryHandler()
