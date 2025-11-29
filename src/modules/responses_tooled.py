import json, os, asyncio
from src.modules.openai_client import OpenAIService
from src.modules.gspread_conexion import (
    insertar_cliente,
    crear_pedido_completo,
    leer_google_sheet,
    add_phone_to_client)
from src.modules.gmail_connection import send_notification
from src.utils.config import config
from fastapi import APIRouter, HTTPException, Depends
from src.utils.config import config
from src.schemas.schemas import NotificacionSchema
from tools.query_handler import (
    handle_get_client, 
    handle_link_phone_to_client,
    handle_create_purchase,
    handle_get_client_orders,
    handle_contact_company)
import logging


# Configuración para leer la tabla de productos
PRODUCTS_SHEET_ID = config["products_sheet_id"]
PRODUCTS_WORKSHEET_NAME = config["products_worksheet_name"]


current_dir = os.path.dirname(os.path.abspath(__file__))

instructions_path = os.path.join(current_dir, '..', '..', 'tools', 'system_message.txt')
instructions_path_path = os.path.normpath(instructions_path)

# Leemos el contenido del archivo y lo guardamos en la variable
with open(instructions_path, 'r', encoding='utf-8') as file:
    system_message = file.read()


tools_path = os.path.join(current_dir, '..', '..', 'tools', 'tool_definition.json')
tools_path = os.path.normpath(tools_path)

# Leemos el contenido del archivo y lo guardamos en la variable
with open(tools_path, 'r', encoding='utf-8') as file:
    TOOLS = json.load(file)

def cargar_productos():
    from src.modules.gspread_conexion import leer_google_sheet  # Ajustá la ruta real
    productos = leer_google_sheet(PRODUCTS_SHEET_ID, PRODUCTS_WORKSHEET_NAME)
    print(productos)
    return productos

productos = cargar_productos()


TOOL_HANDLERS = {
    "get_client_by_cuit": handle_get_client,
    "link_phone_to_client": handle_link_phone_to_client,
    "create_purchase": handle_create_purchase,
    "get_client_orders": handle_get_client_orders,
    "contact_company": handle_contact_company,
    "get_client": handle_get_client,
}


async def required_query(tool_call: dict, client_phone: str):

    tool_call_id = tool_call.call_id
    function_name = tool_call.name
    arguments = json.loads(tool_call.arguments)
    
    logging.info(f"Ejecutando herramienta: {function_name} con argumentos: {arguments}")
    
    if function_name not in TOOL_HANDLERS:
        query_results = {"error": f"Tool '{function_name}' no reconocida."}
    else:
        try:
            # Llama al handler del diccionario
            handler_function = TOOL_HANDLERS[function_name]
            query_results = await  handler_function(arguments)
            
        except Exception as e:
            logging.error(f"Error al ejecutar la herramienta {function_name}: {e}")
            query_results = {"error": f"No se pudo ejecutar la herramienta. Detalle: {e}"}

    logging.info(f"Resultados de la herramienta {function_name}: {query_results}")    
    
    # Formato de respuesta (sin cambios)
    results ={
        "type": "function_call_output",
        "call_id": tool_call_id,
        "output": str(query_results)
    }
    
    return results


#################################################################################################


async def responses_tooled(user_message: str,  thread_id:str=None, 
                           products:str=productos, 
                           system_message: str = system_message, 
                           user_information: str = None,
                           client_phone:str = None,
                           files_id: list = None):
    openai = OpenAIService()
    print(f"Starting to process message: {user_message}, with files_id: {files_id}")
    if thread_id is None:
        if user_information is not None:
            input_messages = [{"role":"system", "content": system_message}, 
                            {"role" : "developer", "content": f"Los productos disponibles son: {products}"},
                            {"role": "developer", "content": f"La información del usuario es: {user_information}"},
                            {"role": "user", "content": user_message}]
        else:
            input_messages = [{"role":"system", "content": system_message}, 
                            {"role" : "developer", "content": f"Los productos disponibles son: {products}"},
                            {"role": "developer", "content": f"El cliente se ha contactado con un numero no registrado: {client_phone}"},
                            {"role": "user", "content": user_message}]
        if files_id:
            print(f"Files ID provided: {files_id}")
            input_messages.append({"role":"developer", "content":f"Id de los archivos adjuntos: {str(files_id)}"})
            

    elif files_id:
        print(f"Files ID provided: {files_id}")
        input_messages = [{"role":"user", "content":user_message},
                          {"role":"developer", "content":f"Id de los archivos adjuntos: {str(files_id)}"}]
        print(f"Input messages with files: {input_messages}")

    else:
        input_messages = [{"role":"user", "content":user_message}]
        
    response = await openai.client.responses.create(
                model="gpt-4o",
                input=input_messages,
                temperature=0.1,
                tools=TOOLS,
                tool_choice="auto",
                previous_response_id=thread_id,
                )
         
    print(f"Response: {response.output_text}")
    tool_call_needed = True
    while tool_call_needed:
        tools_output = []
        tool_call_needed = False
        for tool_call in response.output:
            print(f"Processing tool call: {tool_call}")
            if tool_call.type != "function_call":
                continue
            tool_call_needed = True
            output = await required_query(tool_call, client_phone)
            if isinstance(output, dict):
                tools_output.append(output)
            else:
                raise HTTPException(status_code=500, detail="Error executing tool call")

        if tool_call_needed:
            response = await openai.client.responses.create(
                model="gpt-4o",
                input=tools_output,
                temperature=0.1,
                tools=TOOLS,
                tool_choice="auto",
                previous_response_id=response.id,
            )

    response_message = response.output_text
    print(f"Total tokens used: {response.usage.total_tokens}")
    print(response.usage)
    print(f"Final response message: {response_message}")
    return response_message, response.id
