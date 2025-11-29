import os, requests, mimetypes
from src.modules.file_mapping_service import FileMappingService
from src.modules.sharepoint_service import SharePointService
import tempfile
from typing import Optional
from src.utils.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)

file_mapper = FileMappingService()
sp_service = SharePointService(client_name="Celula")

ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
API_VERSION = settings.WHATSAPP_API_VERSION
logger.debug(f"Access Token: {ACCESS_TOKEN}")

def verify_signature(body_bytes, signature):
    # tu función de validación ya existente
    return True  # placeholder

async def download_media(media_id: str, media_type: str, from_number: str, timestamp: str, original_filename: Optional[str] = None, mime_type: Optional[str] = None):
    """
    Descarga un archivo multimedia de Meta.
    - Si es audio, devuelve los bytes.
    - Si es imagen o documento, lo sube a SharePoint y devuelve un file_id.
    """
    url = f"https://graph.facebook.com/{API_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        media_info = resp.json()
        media_url = media_info.get("url")
        if not media_url:
            logger.error(f"No se encontró URL para media_id {media_id}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al solicitar metadata del media_id {media_id}: {e}", exc_info=True)
        return None

    try:
        media_resp = requests.get(media_url, headers=headers, timeout=30)
        media_resp.raise_for_status()
        content = media_resp.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error al descargar media {media_id}: {e}", exc_info=True)
        return None

    if media_type == "audio":
        return content

    # Para imágenes y documentos
    extension = mimetypes.guess_extension(mime_type) if mime_type else ''
    if media_type == 'document' and original_filename:
        filename = f"{timestamp}_{from_number}_{original_filename}"
    else:
        filename = f"{from_number}_{media_type}_{timestamp}{extension or '.dat'}"

    try:
        sharepoint_url = sp_service.upload_file(
            folder_key="staging", 
            file_name=filename, 
            file_content=content
        )
        if sharepoint_url:
            file_id = file_mapper.create_mapping(sharepoint_url)
            logger.info(f"Archivo subido a SharePoint y mapeado con ID: {file_id}")
            return file_id
    except Exception as e:
        logger.error(f"Error al subir archivo a SharePoint para media_id {media_id}: {e}", exc_info=True)
    
    return None

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
