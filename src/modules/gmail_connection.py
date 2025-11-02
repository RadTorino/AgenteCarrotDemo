from src.schemas.schemas import NotificacionSchema

async def send_notification(NotificacionSchema):
    try:
        tipo = NotificacionSchema.type
        data = NotificacionSchema.data
        user_id = NotificacionSchema.user_id

        print(f"Enviando notificación de tipo: {tipo}")
        print(f"Datos: {data}")
        if user_id:
            print(f"Usuario ID: {user_id}")
        
        return True
    except Exception as e:
        print(f"Error al enviar notificación: {e}")
        return False