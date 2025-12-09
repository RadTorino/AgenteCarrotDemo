from fastapi import FastAPI, Request, HTTPException, Query
import hmac
import hashlib
from src.modules.whatsapp_handler import download_media, send_text_message, parse_whatsapp_message
from src.modules.openai_client import OpenAIService
from src.modules.responses_tooled import responses_tooled
from src.modules.chat_memory import memory_handler
from src.utils.db_connection import get_client_by_phone, get_products
from src.utils.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
app = FastAPI()

VERIFY_TOKEN = settings.WHATSAPP_VERIFY_TOKEN
APP_SECRET = settings.APP_SECRET
ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
API_VERSION = settings.WHATSAPP_API_VERSION

agent = OpenAIService()

@app.post("/webhook")
async def receive_webhook(request: Request):
    logger.info("📩 Entró al endpoint POST")

    # --- Verificación de firma ---
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not verify_signature(body_bytes, signature):
        logger.debug(f"Signature received: {signature}")
        # logger.error("Invalid signature")
        # raise HTTPException(status_code=403, detail="Invalid signature")

    # --- Parseo de datos ---
    data = await request.json()
    messages = parse_whatsapp_message(data)
    logger.debug(f"Received data: {data}")
    files_id = None

    if not messages:
        logger.warning("No se encontraron mensajes en el payload.")
        return {"status": "no messages"}

    # --- Loop principal ---
    productos = None
    for msg in messages:
        from_number = "54" + msg["from"][3:]  # --> validar y ajustar.
        msg_type = msg["type"]
        user_message = None

        logger.info(f"📨 Mensaje de {from_number} - tipo: {msg_type}")

        thread_id = memory_handler.get_or_create_thread(from_number)
        if not thread_id:
            productos = await get_products()
            user_info = None
            user_info = await get_client_by_phone(from_number)
            if user_info:
                logger.info(f"👤 Información del usuario: {user_info}")

        if msg_type == "text":
            user_message = msg.get("text")
            logger.info(f"💬 Texto recibido: {user_message}")
            if not user_message:
                await send_text_message(to=from_number, message="Perdón, no puedo procesar tu mensaje.")
                continue

        elif msg_type == "audio":
            media_id = msg.get("audio_id")
            audio_bytes = await download_media(
                media_id=media_id,
                media_type='audio',
                from_number=from_number,
                timestamp=msg.get("timestamp")
            )

            if audio_bytes:
                try:
                    transcription = await agent.transcribe_audio(audio_bytes=audio_bytes, language="es")
                    user_message = transcription.text
                    logger.info(f"📝 Transcripción: {user_message}")
                except Exception as e:
                    logger.error(f"❌ Error procesando audio: {e}", exc_info=True)
                    await send_text_message(to=from_number, message="Hubo un error al procesar tu audio.")
                    continue
            else:
                await send_text_message(to=from_number, message="No pude descargar tu audio.")
                continue

        elif msg_type == "image":
            media_id = msg.get("image_id")
            image_id = await download_media(
                media_id=media_id,
                media_type='image',
                from_number=from_number,
                timestamp=msg.get("timestamp"),
                mime_type=msg.get("mime_type")
            )

            if image_id:
                files_id = [image_id]
                user_message = f"Archivo enviado: {image_id}"
                logger.info(f"✅ Imagen descargada y mapeada con éxito. ID: {image_id}")
            else:
                await send_text_message(to=from_number, message="No pude descargar tu imagen.")
                continue

        elif msg_type == "document":
            media_id = msg.get("document_id")
            document_id = await download_media(
                media_id=media_id,
                media_type='document',
                from_number=from_number,
                timestamp=msg.get("timestamp"),
                original_filename=msg.get("filename"),
                mime_type=msg.get("mime_type")
            )

            if document_id:
                files_id = [document_id]
                user_message = f"Archivo enviado: {document_id}"
                logger.info(f"✅ Documento descargado y mapeado con éxito. ID: {document_id}")
            else:
                await send_text_message(to=from_number, message="No pude descargar tu archivo.")
                continue

        else:
            logger.warning(f"Tipo de mensaje no manejado: {msg_type}")
            continue

        logger.info(f"🤖 Procesando mensaje del usuario: {user_message}, con archivos: {files_id}")
        # --- Respuesta agente ---
        respuesta, thread_id = await responses_tooled(
            user_message=user_message,
            client_phone=from_number,
            thread_id=thread_id,
            user_information=user_info if not thread_id else None,
            files_id = files_id,
            products=productos 
        )

        response_message = await send_text_message(to=from_number, message=respuesta)
        memory_handler.update_thread_activity(from_number, thread_id)
        logger.info(f"✅ Respuesta enviada a {from_number}: {response_message}")

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
    logger.info("GET /webhook called")
    logger.info(f"Webhook verification: hub_mode={hub_mode}, hub_challenge={hub_challenge}, hub_verify_token={hub_verify_token}")
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.debug(f"hub_challenge type: {type(hub_challenge)}")
        return int(hub_challenge)
    else:
        logger.debug(f"VERIFY_TOKEN: {VERIFY_TOKEN}")
        return VERIFY_TOKEN