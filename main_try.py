from fastapi import FastAPI, Form
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse
from uuid import uuid4
import time, os, asyncio
from datetime import datetime, timedelta
#from src.modules.assistant import process_chat
from src.modules.responses_tooled import responses_tooled
from src.modules.gspread_conexion import get_client_by_phone
from src.utils.config import config

# Configuración para leer la tabla de productos
PRODUCTS_SHEET_ID = config["products_sheet_id"]
PRODUCTS_WORKSHEET_NAME = config["products_worksheet_name"]

current_dir = os.path.dirname(os.path.abspath(__file__))

file_path = os.path.join(current_dir,  'tools', 'system_message.txt')
file_path = os.path.normpath(file_path)

# Leemos el contenido del archivo y lo guardamos en la variable
with open(file_path, 'r', encoding='utf-8') as file:
    system_message = file.read()

def cargar_productos():
    from src.modules.gspread_conexion import leer_google_sheet  # Ajustá la ruta real
    productos = leer_google_sheet(PRODUCTS_SHEET_ID, PRODUCTS_WORKSHEET_NAME)
    #print(f"Productos cargados: {len(productos)}")
    print(productos)
    return productos


def get_or_create_thread(client_number):
    """
    Gestiona el thread_id de la conversación. Si no existe o ha expirado,
    crea uno nuevo.
    """
    thread_info = conversations.get(client_number)
    
    if thread_info:
        last_activity = thread_info["last_activity"]
        # Si la conversación ha expirado, la eliminamos
        if datetime.now() - last_activity > EXPIRATION_TIME:
            del conversations[client_number]
            thread_id = None
            conversations[client_number] = {}
            print(f"Conversación de {client_number} expirada.")
        else:
            thread_id = thread_info["thread_id"]
    else:
        conversations[client_number] = {}
        thread_id = None
    return thread_id

app = FastAPI()

productos_json = cargar_productos()
conversations = {}
EXPIRATION_TIME = timedelta(hours=24) # 24 horas

@app.post("/whatsapp")
async def whatsapp_webhook(
    Body: str = Form(...),
    From: str = Form(...)
):
    print(f"Mensaje recibido de {From}: {Body}")

    thread_id = get_or_create_thread(From)
    user_information = None
    if thread_id is None:
        user_information = get_client_by_phone(From) 
        if user_information:
            print(f"Información del usuario: {user_information}")
    

    # Procesar la respuesta del asistente
    try:
        respuesta, thread_id = await responses_tooled(
                user_message=Body,
                products=productos_json if thread_id is None else None,
                thread_id=thread_id,
                system_message=system_message,
                user_information= user_information,
                client_phone=From
            )

        
        # Actualizar el estado de la conversación con el nuevo thread_id y la marca de tiempo
        conversations[From] = {
            "thread_id": thread_id,
            "last_activity": datetime.now()
        }
        assistant_reply = respuesta
    except Exception as e:
        print(f"Error procesando el mensaje: {e}")
        assistant_reply = "Lo siento, hubo un error procesando tu mensaje."

    # Crear la respuesta Twilio (TwiML)
    twilio_resp = MessagingResponse()
    msg = twilio_resp.message()
    msg.body(assistant_reply)

    return Response(content=str(twilio_resp), media_type="application/xml")

