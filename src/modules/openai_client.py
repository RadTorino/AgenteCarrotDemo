import os
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
import time
import asyncio

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


class OpenAIService:
    def __init__(self):
        """Inicializa el servicio con la API Key de OpenAI."""
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def assistant_response(
        self,
        user_message:str,
        context:str = None, 
        thread_id = None,
        assistant_id = "asst_kdtYur4OlAjJGM9E2WXe3Lvn" #"asst_ghUa1CLukaWOkuaD2bFzAlu5"    
        ):
    
        if not thread_id:
            print("Ningún thread_id provisto por el cliente, generando uno nuevo...")

            thread = await self.client.beta.threads.create(
                messages=[
                    {
                    "role": "assistant",
                    "content": "Soy un chatbot especializado en responder preguntas sobre los productos de Phytobiotics,¿en qué puedo ayudarte?"
                    },
                    {
                    "role": "assistant",
                    "content": f"Estos son los datos históricos sobre trabajos de investigación con los que cuento: {context}"
                    }
            ]) 
            thread_id=thread.id # Obtiene un nuevo thread_id y lo asigna para ser reutilizado.

            if thread_id:
                print(f"Nuevo thread iniciado. ID: {thread_id}")

        else:
            thread_id=thread_id
            print(f"El cliente proporciona thread_id, se utiliza. ID:{thread_id}")
        
        messages = await self.client.beta.threads.messages.list( thread_id=thread_id)


        if not user_message:
            return None, thread_id
        else:
            message = await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                    role="user",
                    content=user_message
                    )
        # Se obtiene un id del mensaje para identificarlo
        message_id=message.id
        print(f"Mensaje del usuario:  agregado al thread.")

        run = await self.client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
        )
        
        if run:
            print("Se inicia la corrida del Asistente...")
            print(run.status)
        if run.status == 'failed':
            print(f"La corrida del Asistente falló: {run.last_error.code} - {run.last_error.message}") 
            raise Exception("La corrida del Asistente falló. Por favor, inténtalo de nuevo más tarde.")        
        messages = await self.client.beta.threads.messages.list(thread_id=thread_id)
        #answer_id = messages.data[0].id
        answer = messages.data[0].content[0].text.value
        print(f"Respuesta del asistente lista: {answer}")
        
        return (answer, thread_id)