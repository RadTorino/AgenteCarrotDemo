import streamlit as st
import uuid
import asyncio, os
import json
from datetime import datetime, timedelta
from src.utils.config import config
from src.modules.assistant import assistant_tooled
from src.modules.responses_tooled import responses_tooled
from src.modules.gspread_conexion import get_client_by_phone

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


EXPIRATION_TIME = timedelta(hours=24)

if "conversations" not in st.session_state:
    st.session_state.conversations = {}
    
if "messages" not in st.session_state:
    st.session_state.messages = []

if "productos" not in st.session_state:
    st.session_state.productos = cargar_productos()

if "user_information" not in st.session_state:
    st.session_state.user_information = {}

if "client_number" not in st.session_state:
    st.session_state.client_number = "1123912091"  

def get_or_create_thread(client_number):
    """
    Gestiona el thread_id de la conversación. Si no existe o ha expirado,
    crea uno nuevo.
    """
    thread_info = st.session_state.conversations.get(client_number)
    
    if thread_info:
        last_activity = thread_info["last_activity"]
        # Si la conversación ha expirado, la eliminamos
        if datetime.now() - last_activity > EXPIRATION_TIME:
            del st.session_state.conversations[client_number]
            thread_id = None
            st.session_state.conversations[client_number] = {}
            print(f"Conversación de {client_number} expirada.")
        else:
            thread_id = thread_info["thread_id"]
    else:
        st.session_state.conversations[client_number] = {}
        thread_id = None
    return thread_id

st.title("🥕 Chatbot Carrot - Demo de pedidos mayoristas")

# Mostrar historial completo
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input del usuario
user_input = st.chat_input("Escribí algo...")

if user_input:
    thread_id = get_or_create_thread(st.session_state.client_number)
    if thread_id is None:
        user_information = get_client_by_phone(st.session_state.client_number) 
        if user_information:
            st.session_state.user_information = str(user_information)
            print(f"Información del usuario: {user_information}")
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Procesar respuesta
    with st.spinner("Pensando..."):
        productos_json = json.dumps(st.session_state.productos, ensure_ascii=False)

        # respuesta, new_thread_id = asyncio.run(
        #     assistant_tooled(
        #         user_message=user_input,
        #         products=productos_json if st.session_state.thread_id is None else None,
        #         thread_id=st.session_state.thread_id
        #     )
        # )
        respuesta, new_thread_id = asyncio.run(
            responses_tooled(
                user_message=user_input,
                products=productos_json if thread_id is None else None,
                thread_id=thread_id,
                system_message=system_message,
                user_information= st.session_state.user_information or None,
                client_phone=st.session_state.client_number 
            )
        )

        st.session_state.conversations[st.session_state.client_number]["thread_id"] = new_thread_id
        st.session_state.conversations[st.session_state.client_number]["last_activity"] = datetime.now()
        st.chat_message("assistant").markdown(respuesta)
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
