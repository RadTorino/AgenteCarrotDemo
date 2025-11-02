import os
import requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

ACCESS_TOKEN = "EAATRx4YkN0gBP43dLyvuRrv2760GbMRJ2PnelzNFXEphZAa8cYNiKteh6DZAzo4oaiNMz4zsi2Inwofyv3syaZBhQZBG24yxrcW9qxZBDVpMSztUZBhOwx8s2avx1Q1dq2wEUcpN2ZA6YwODQdyCPCUgSpQjM0ZCfMw8cJUuPBPogQ1ZAIby8lFv1xbZBBwOoZA9nd7ZAtJESrSJVe6ebMTCVYQZBx8rOqoLDWCNg2Txtq4pWM6v40YY90ZANjrpCNb7Ou40Kr6s0RPFsZCyjy2Rc8ZBzOZBDYVZCL"
AUDIO_FOLDER = "audios_recibidos"
PHONE_NUMBER_ID = "801735439696882"
API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v24.0")
os.makedirs(AUDIO_FOLDER, exist_ok=True)

def verify_signature(body_bytes, signature):
    # tu función de validación ya existente
    return True  # placeholder

async def download_media(media_id, filename):
    """Descarga un archivo multimedia de Meta y lo guarda localmente."""
    # 1. Obtener URL temporal del archivo
    url = f"https://graph.facebook.com/v21.0/{media_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Error al obtener metadata del media_id {media_id}: {resp.text}")
        return None
    
    media_info = resp.json()
    media_url = media_info.get("url")
    if not media_url:
        print(f"No se encontró URL para media_id {media_id}")
        return None

    # 2. Descargar el archivo real
    media_resp = requests.get(media_url, headers=headers)
    if media_resp.status_code == 200:
        filepath = os.path.join(AUDIO_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(media_resp.content)
        print(f"✅ Archivo guardado en {filepath}")
        return media_resp.content
    else:
        print(f"Error al descargar media: {media_resp.text}")
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
                    "mime_type": msg.get("audio", {}).get("mime_type"),
                    "text": msg.get("text", {}).get("body"),
                }
                messages_data.append(message_info)

    return messages_data
