import os
from groq import AsyncGroq
from dotenv import load_dotenv
import time
import asyncio

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")


class GroqClient:
    def __init__(self):
        """Inicializa el servicio con la API Key de GROQ."""
        self.client = AsyncGroq(api_key=api_key)

    async def process_text_to_text_response(
        self, 
        text: str, 
        system_message: str | None = None,
        old_messages: list | None = None
    ):
        system_msg = system_message

        if old_messages is not None:
            print(f"Se continua conversación con último mensaje: {old_messages[-1]}.")
            messages = old_messages.copy()

            new_message = {
                        "role": "user",
                        "content": text 
                            }
            messages.append(new_message)
        else:
            print("No se encontró un mensaje anterior, se inicia una nueva conversación.")
            system_msg = system_message
            messages=[
                {
                    "role": "system",
                    "content": system_msg 
            },
                {
                    "role": "user",
                    "content": text
                }
            ]

        completion = await self.client.chat.completions.create(
            model="compound-beta",
            messages=messages
        )
        answer = completion.choices[0].message.content
        print(f"Respuesta del asistente lista: {answer}")

        messages.append({
            'role':'assistant',
            'content': answer
        })

        return answer, messages
