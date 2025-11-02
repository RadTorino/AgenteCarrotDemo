import os, io
from openai import AsyncOpenAI
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


class OpenAIService:
    def __init__(self):
        """Inicializa el servicio con la API Key de OpenAI."""
        self.client = AsyncOpenAI(api_key=api_key)
    
    def transcribe_audio(self, audio_bytes, language="es", model="whisper-1"):
        """
        Transcribe un audio utilizando el modelo Whisper de OpenAI.

        Parámetros:
        - audio_bytes: bytes del archivo de audio a transcribir.
        - language: idioma de la transcripción (por defecto, español).
        - model: modelo de OpenAI a utilizar.

        Retorna:
        - La transcripción como JSON, o un mensaje de error.
        """
        filename = "audio.mp3"
        buff = io.BytesIO(audio_bytes)
        buff.name = filename  # OpenAI requiere un nombre de archivo

        try:
            response = self.client.audio.transcriptions.create(
                file=buff,
                model=model,
                language=language,
                temperature=0.2,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )
            return response

        except Exception as e:
            print(f"Error en la transcripción: {str(e)}")
            raise e