from src.modules.groq_client import GroqClient
from uuid import uuid4
from src.modules.openai_client import OpenAIService
from src.modules.gspread_conexion import (
    insertar_cliente,
    insertar_pedido,
    leer_google_sheet)
from src.utils.config import config
import asyncio, json
from fastapi import HTTPException
import os
from dotenv import load_dotenv
load_dotenv()
ASSISTANT_ID= os.getenv("ASSISTANT_ID")


async def ejecutar_tools(run: dict):
    results = []
    for tool_call in run.required_action.submit_tool_outputs.tool_calls:
        tool_call_id = tool_call.id
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Ejecutando herramienta: {function_name} con argumentos: {arguments}")
        try:
            if function_name == "register_client":
                print("Registrando nuevo cliente...")
                nuevo_id = insertar_cliente(
                    sheet_id=config["clientes_sheet_id"],
                    worksheet_name=config["clientes_worksheet_name"],
                    nombre_comercial=arguments["commercial_name"],
                    cuit=arguments["cuit"],
                    direccion=arguments["address"]
                )
                query_results = {"new_client_id": nuevo_id}
                print(f"Nuevo cliente registrado con ID: {nuevo_id}")

            elif function_name == "create_purchase":
                nuevo_id = insertar_pedido(
                    sheet_id=config["compras_sheet_id"],
                    worksheet_name=config["compras_worksheet_name"],
                    user_id=arguments["user_id"],
                    product_id=arguments["product_id"],
                    quantity=arguments["quantity"]
                )
                query_results = {"new_purchase_id": nuevo_id}
            
            elif function_name == "get_client_orders":
                compras = leer_google_sheet(
                    sheet_id=config["compras_sheet_id"],
                    worksheet_name=config["compras_worksheet_name"]
                )
                print(f"Compras obtenidas: {compras}")
                compras_cliente = [c for c in compras if str(c.get("user_id"))== str(arguments["user_id"])]
                query_results = {"orders": compras_cliente}
            
            elif function_name == "get_client":
                clientes = leer_google_sheet(
                    sheet_id=config["clientes_sheet_id"],
                    worksheet_name=config["clientes_worksheet_name"]
                )
                cliente = next((c for c in clientes if str(c.get("cuit")) == str(arguments["cuit"])), None)
                query_results = {"client": cliente} if cliente else {"error": "Cliente no encontrado."}
            
            else:
                query_results = {"error": f"Tool '{function_name}' no reconocida."}
        
        except Exception as e:
            print(f"Error al ejecutar la herramienta {function_name}: {e}")
            query_results = {"error": f"No se pudo ejecutar la herramienta"}
        
        print(f"Resultados de la herramienta {function_name}: {query_results}")
        results.append({
            "tool_call_id": tool_call_id,
            "output": str(query_results)
        })
    
    return results



async def assistant_tooled(user_message: str, products=None, thread_id:str=None,):
    openai = OpenAIService()
    assistant_id = ASSISTANT_ID

    if not thread_id:
        print("Ningún thread_id provisto por el cliente, generando uno nuevo...")

        thread = await openai.client.beta.threads.create(
            messages=[
                {
                "role": "assistant",
                "content": f"Los productos disponibles son: {products}" 
                }
        ]) 
        thread_id=thread.id # Obtiene un nuevo thread_id y lo asigna para ser reutilizado.

        if thread_id:
            print(f"Nuevo thread iniciado. ID: {thread_id}")

    else:
        thread_id=thread_id
        print(f"El cliente proporciona thread_id, se utiliza. ID:{thread_id}")
    
    messages = await openai.client.beta.threads.messages.list( thread_id=thread_id)


    if not user_message:
        return None, thread_id
    else:
        message = await openai.client.beta.threads.messages.create(
            thread_id=thread_id,
                role="user",
                content=user_message
                )
    # Se obtiene un id del mensaje para identificarlo
    message_id=message.id
    print(f"Mensaje del usuario:  agregado al thread.")

    run = await openai.client.beta.threads.runs.create_and_poll(
    thread_id=thread_id,
    assistant_id=assistant_id,
    )
    
    if run:
        print("Se inicia la corrida del Asistente...")
        print(run.status)
        status = run.status
    while status == 'requires_action':
        print(run.status)
        query_results = await ejecutar_tools(run)
        
        run = await openai.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=query_results
                    )
        while True:
            run = await openai.client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id
            )
            print(f"Estado de la corrida del asistente: {run.status}")
            if run.status == "completed":
                status = run.status
                break
            elif run.status == "queued":
                await asyncio.sleep(1)
            elif run.status == "requires_action":
                break
    if run.status == "failed":
        print(f"Error en la corrida del asistente: {run.last_error.code} - {run.last_error.message}")
        raise HTTPException(status_code=500, detail="La corrida del asistente falló.")

    messages = await openai.client.beta.threads.messages.list(thread_id=thread_id)
    #answer_id = messages.data[0].id
    answer = messages.data[0].content[0].text.value
    print(f"Respuesta del asistente lista: {answer}")
    
    return (answer, thread_id)
