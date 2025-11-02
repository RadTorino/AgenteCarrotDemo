from fastapi import FastAPI, Request, HTTPException, Query
import hmac
import hashlib
import os
import requests
from src.modules.whatsapp_handler import download_media, send_text_message, parse_whatsapp_message
from src.modules.openai_client import OpenAIService
from src.modules.responses_tooled import responses_tooled
from src.modules.chat_memory import memory_handler
from src.modules.gspread_conexion import get_client_by_phone

app = FastAPI()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "abcd")
APP_SECRET = "b8ca66b208a660b82fffd01e3c19e613"  
ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = "801735439696882"
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v24.0")

agent = OpenAIService()



@app.post("/webhook")
async def receive_webhook(request: Request):
    print("📩 Entró al endpoint POST")

    # --- Verificación de firma ---
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(body_bytes, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # --- Parseo de datos ---
    data = await request.json()
    messages = parse_whatsapp_message(data)

    if not messages:
        print("⚠️ No se encontraron mensajes en el payload.")
        return {"status": "no messages"}

    # --- Loop principal ---
    for msg in messages:
        from_number = "54" + msg["from"][3:] #--> validar y ajustar. 
        msg_type = msg["type"]
        user_message = None

        print(f"📨 Mensaje de {from_number} - tipo: {msg_type}")

        thread_id = memory_handler.get_or_create_thread(from_number)
        if not thread_id:
            user_info = None
            user_info = get_client_by_phone(from_number)
            if user_info:
                print(f"👤 Información del usuario: {user_info}")

        if msg_type == "text":
            user_message = msg.get("text")
            print(f"💬 Texto recibido: {user_message}")
            if not user_message:
                await send_text_message(to=from_number, message="Perdón, no puedo procesar tu mensaje.")
                continue

        elif msg_type == "audio":
            media_id = msg.get("audio_id")
            mime_type = msg.get("mime_type")
            print(f"🎧 Audio recibido: {media_id} ({mime_type})")

            audio_bytes = await download_media(media_id, f"{media_id}.ogg")

            if audio_bytes:
                try:
                    transcription = await agent.transcribe_audio(audio_bytes=audio_bytes, language="es")
                    user_message = transcription.text
                    print(f"📝 Transcripción: {user_message}")
                except Exception as e:
                    print(f"❌ Error procesando audio: {e}")
                    await send_text_message(to=from_number, message="Hubo un error al procesar tu audio.")
                    continue
            else:
                await send_text_message(to=from_number, message="No pude descargar tu audio.")
                continue

        else:
            print(f"Tipo de mensaje no manejado: {msg_type}")
            continue

        # --- Respuesta agente ---
        respuesta, thread_id = await responses_tooled(
            user_message=user_message,
            client_phone=from_number,
            thread_id=thread_id,
            user_information=user_info if not thread_id else None
        )

        response_message = await send_text_message(to=from_number, message=respuesta)
        memory_handler.update_thread_activity(from_number, thread_id)
        print(f"✅ Respuesta enviada a {from_number}: {response_message}")

    return {"status": "received"}















def verify_signature(request_body: bytes, signature_header: str):
    """Verifica la firma X-Hub-Signature-256 con HMAC SHA256"""
    if not signature_header:
        return False
    sig_prefix = "sha256="
    if not signature_header.startswith(sig_prefix):
        return False
    signature = signature_header[len(sig_prefix):]
    expected = hmac.new(APP_SECRET.encode(), request_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.get("/webhook")
def verify_webhook( hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Endpoint que Meta llama para verificar tu webhook (challenge)"""
    print("Entro al endpoint get")
    print(f"hub_mode: {hub_mode}, hub_challenge: {hub_challenge}, hub_verify_token: {hub_verify_token}")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print(type(hub_challenge))
        return int(hub_challenge)
    else:
        print(VERIFY_TOKEN)
        return VERIFY_TOKEN