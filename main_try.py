from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from uuid import uuid4

from src.modules.assistant import process_chat

app = FastAPI()

# Estado de conversaciones por número de WhatsApp
conversations = {}

@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    print(f"Mensaje recibido de {From}: {Body}")

    # Determinar el "thread_id" usando el número del cliente
    thread_id = conversations.get(From, None)

    # Procesar la respuesta del asistente
    try:
        response = await process_chat(Body, thread_id)
        # Actualizar el estado de la conversación
        conversations[From] = response["thread_id"]
        assistant_reply = response["answer"]
    except Exception as e:
        print(f"Error procesando el mensaje: {e}")
        assistant_reply = "Lo siento, hubo un error procesando tu mensaje."

    # Crear la respuesta Twilio (TwiML)
    twilio_resp = MessagingResponse()
    msg = twilio_resp.message()
    msg.body(assistant_reply)

    return Response(content=str(twilio_resp), media_type="application/xml")

