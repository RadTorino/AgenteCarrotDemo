import os, requests
from src.modules.file_mapping_service import FileMappingService
import tempfile
from typing import Optional
from dotenv import load_dotenv
load_dotenv()

# 1. An instance is created at the module level. This is correct.
file_mapper = FileMappingService()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
AUDIO_FOLDER = "audios_recibidos"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v24.0")
print(f"Access Token: {ACCESS_TOKEN}")
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def verify_signature(body_bytes, signature):
    # tu función de validación ya existente
    return True  # placeholder

async def download_media(media_id: str, filename: Optional[str] = None, save_to_temp: bool = False):
    """Descarga un archivo multimedia de Meta.
    - Por defecto devuelve los bytes (útil para audio -> transcriptor).
    - Si save_to_temp=True guarda en un fichero temporal y devuelve la ruta.
    El comportamiento es consistente independientemente del tipo de media.
    """
    # 1. Obtener URL temporal del archivo
    url = f"https://graph.facebook.com/{API_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except Exception as e:
        print(f"Error al solicitar metadata del media_id {media_id}: {e}")
        return None

    if resp.status_code != 200:
        print(f"Error al obtener metadata del media_id {media_id}: {resp.text}")
        return None

    media_info = resp.json()
    media_url = media_info.get("url")
    if not media_url:
        print(f"No se encontró URL para media_id {media_id}")
        return None

    # 2. Descargar el archivo real
    try:
        media_resp = requests.get(media_url, headers=headers, timeout=30)
    except Exception as e:
        print(f"Error al descargar media {media_id}: {e}")
        return None

    if media_resp.status_code != 200:
        print(f"Error al descargar media: {media_resp.text}")
        return None

    content = media_resp.content

    if save_to_temp:
        # Determinar sufijo por filename o dejar vacío
        suffix = ""
        if filename:
            _, ext = os.path.splitext(filename)
            suffix = ext if ext else ""
        # Crear archivo temporal persistente
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=AUDIO_FOLDER)
            tmp.write(content)
            tmp.flush()
            tmp.close()
            # 2. The method is called on the instance. This is also correct.
            id = file_mapper.create_mapping(tmp.name)
            return id
        except Exception as e:
            print(f"Error guardando archivo temporal para media_id {media_id}: {e}")
            return None

    
    return content

async def send_text_message(to: str, message: str):
    """Enviar un mensaje de texto usando la API de WhatsApp Cloud"""
    url = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    # Podés manejar errores aquí (logs, reintentos, etc.)
    # Por ahora:
    return resp.json()

def parse_whatsapp_message(data: dict):
    """Extrae los datos relevantes del webhook de WhatsApp."""
    messages_data = []

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                message_info = {
                    "from": msg.get("from"),
                    "type": msg.get("type"),
                    "id": msg.get("id"),
                    "timestamp": msg.get("timestamp"),
                    "audio_id": msg.get("audio", {}).get("id"),
                    "image_id": msg.get("image", {}).get("id"),
                    "document_id": msg.get("document", {}).get("id"),
                    "filename": msg.get("document", {}).get("filename", "archivo"),
                    "mime_type": msg.get(msg.get("type"), {}).get("mime_type"),
                    "text": msg.get("text", {}).get("body"),
                }
                messages_data.append(message_info)

    return messages_data
