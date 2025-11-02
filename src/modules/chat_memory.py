from datetime import timedelta, datetime
from src.utils.config import conversations

EXPIRATION_TIME = timedelta(hours=24)

class MemoryHandler:
    """Maneja la memoria conversacional de los clientes (threads activos)."""

    def __init__(self, expiration_time: timedelta = EXPIRATION_TIME):
        self.expiration_time = expiration_time

    def get_or_create_thread(self, client_number: str):
        """
        Devuelve el thread_id activo del cliente o crea uno nuevo si expiró o no existe.
        """
        thread_info = conversations.get(client_number)

        if thread_info:
            last_activity = thread_info.get("last_activity")
            if not last_activity or datetime.now() - last_activity > self.expiration_time:
                print(f"🕒 Conversación expirada para {client_number}. Reiniciando...")
                del conversations[client_number]
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
        conversations[client_number] = {
            "thread_id": thread_id,
            "last_activity": datetime.now()
        }
        print(f"💾 Memoria actualizada para {client_number} (thread {thread_id})")
        return thread_id

memory_handler = MemoryHandler()
