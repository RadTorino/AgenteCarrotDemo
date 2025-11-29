from pydantic import BaseModel
from typing import Optional, Literal

class NotificacionSchema(BaseModel):
    """
    args:
        type (str): Tipo de notificación. Puede ser uno de los siguientes:
            - "nuevo_cliente_mayorista"
            - "potencial_proveedor"
            - "potencial_empleado"
            - "reclamos"
        data (dict): Datos específicos de la notificación.
        user_id (Optional[str]): ID del usuario que envía la notificación.
        file_url (Optional[str]): URL del archivo adjunto, si aplica.
    """
    type: str
    data: dict
    user_id: Optional[str] = None
    file_url: Optional[str] = None