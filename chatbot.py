import streamlit as st
import asyncio
import json
from src.utils.config import config
from src.modules.assistant import assistant_tooled

# Configuración para leer la tabla de productos
PRODUCTS_SHEET_ID = config["products_sheet_id"]
PRODUCTS_WORKSHEET_NAME = config["products_worksheet_name"]

def cargar_productos():
    from src.modules.gspread_conexion import leer_google_sheet  # Ajustá la ruta real
    productos = leer_google_sheet(PRODUCTS_SHEET_ID, PRODUCTS_WORKSHEET_NAME)
    print(f"Productos cargados: {len(productos)}")
    return productos

# Inicializar sesión
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "productos" not in st.session_state:
    st.session_state.productos = cargar_productos()

st.title("Chat demo")

# Mostrar historial completo
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input del usuario
user_input = st.chat_input("Escribí algo...")

if user_input:
    # Mostrar mensaje del usuario y guardar en historial
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Procesar respuesta
    with st.spinner("Pensando..."):
        productos_json = json.dumps(st.session_state.productos, ensure_ascii=False)

        respuesta, new_thread_id = asyncio.run(
            assistant_tooled(
                user_message=user_input,
                products=productos_json if st.session_state.thread_id is None else None,
                thread_id=st.session_state.thread_id
            )
        )

        st.session_state.thread_id = new_thread_id
        st.chat_message("assistant").markdown(respuesta)
        st.session_state.messages.append({"role": "assistant", "content": respuesta})
