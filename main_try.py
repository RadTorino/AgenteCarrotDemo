from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from uuid import uuid4
import time
from datetime import datetime, timedelta

from src.modules.assistant import process_chat


app = FastAPI()

# Estado de conversaciones por número de WhatsApp con su última marca de tiempo
conversations = {}
EXPIRATION_TIME = timedelta(hours=24) # 24 horas

@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    print(f"Mensaje recibido de {From}: {Body}")

    # Validar si la conversación existente ha expirado
    conversation_info = conversations.get(From, None)
    thread_id = None
    if conversation_info:
        last_activity_time = conversation_info["last_activity"]
        if datetime.now() - last_activity_time <= EXPIRATION_TIME:
            # Si no ha expirado, usamos el thread_id existente
            thread_id = conversation_info["thread_id"]
        else:
            # Si expiró, la eliminamos y el thread_id será None
            del conversations[From]
            print(f"La conversación para {From} ha expirado y ha sido eliminada.")

    # Procesar la respuesta del asistente
    try:
        response = await process_chat(Body, thread_id)
        
        # Actualizar el estado de la conversación con el nuevo thread_id y la marca de tiempo
        conversations[From] = {
            "thread_id": response["thread_id"],
            "last_activity": datetime.now()
        }
        assistant_reply = response["answer"]
    except Exception as e:
        print(f"Error procesando el mensaje: {e}")
        assistant_reply = "Lo siento, hubo un error procesando tu mensaje."

    # Crear la respuesta Twilio (TwiML)
    twilio_resp = MessagingResponse()
    msg = twilio_resp.message()
    msg.body(assistant_reply)

    return Response(content=str(twilio_resp), media_type="application/xml")

