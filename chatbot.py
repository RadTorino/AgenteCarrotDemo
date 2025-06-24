import streamlit as st
import asyncio
from uuid import uuid4

from src.modules.assistant import process_chat

# Inicializar sesión
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Chat demo")

# Mostrar historial completo
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input del usuario
user_input = st.chat_input("Escribí algo...")

if user_input:
    # Mostrar mensaje del usuario en pantalla y guardar
    st.chat_message("user").markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Procesar respuesta
    with st.spinner("Pensando..."):
        result = asyncio.run(process_chat(user_input, st.session_state.thread_id))
        st.session_state.thread_id = result["thread_id"]
        respuesta = result["answer"]

    # Mostrar respuesta del bot y guardar
    st.chat_message("assistant").markdown(respuesta)
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
