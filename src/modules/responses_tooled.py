import json, os, asyncio
from src.modules.openai_client import OpenAIService
from src.modules.gspread_conexion import (
    insertar_cliente,
    crear_pedido_completo,
    leer_google_sheet,
    add_phone_to_client)
from src.utils.config import config
from fastapi import APIRouter, HTTPException, Depends
from dotenv import load_dotenv
load_dotenv()


# Obtenemos la ruta del directorio actual (donde está el script que se ejecuta)
current_dir = os.path.dirname(os.path.abspath(__file__))

file_path = os.path.join(current_dir, '..', '..', 'tools', 'tool_definition.json')
file_path = os.path.normpath(file_path)

# Leemos el contenido del archivo y lo guardamos en la variable
with open(file_path, 'r', encoding='utf-8') as file:
    TOOLS = json.load(file)



async def required_query(tool_call:dict):

    tool_call_id = tool_call.call_id
    function_name = tool_call.name
    arguments = json.loads(tool_call.arguments)
    print(f"Ejecutando herramienta: {function_name} con argumentos: {arguments}")
    try:
        if function_name == "register_client":
            print("Registrando nuevo cliente...")
            nuevo_id = insertar_cliente(
                sheet_id=config["clientes_sheet_id"],
                worksheet_name=config["clientes_worksheet_name"],
                nombre_comercial=arguments["commercial_name"],
                cuit=arguments["cuit"],
                direccion=arguments["address"],
                phone_number=arguments["phone_number"]
            )
            query_results = {"new_client_id": nuevo_id}
            print(f"Nuevo cliente registrado con ID: {nuevo_id}")

        elif function_name == "create_purchase":
            nuevo_id = crear_pedido_completo(
                sheet_id=config["compras_sheet_id"],
                user_id=arguments["user_id"],
                products=arguments["products"]
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
        elif function_name == "link_phone_to_client":
            phone_id = add_phone_to_client(
                sheet_id=config["compras_sheet_id"],
                user_id = arguments["user_id"],
                phone_number=arguments["phone_number"]
            )
            query_results = {"phone_id": phone_id}
        else:
            query_results = {"error": f"Tool '{function_name}' no reconocida."}
    
    except Exception as e:
        print(f"Error al ejecutar la herramienta {function_name}: {e}")
        query_results = {"error": f"No se pudo ejecutar la herramienta"}
    
    print(f"Resultados de la herramienta {function_name}: {query_results}")    
    results ={
        "type": "function_call_output",
        "call_id": tool_call_id,
        "output": str(query_results)
    }
    print(f"Tool call results: {results}")
    return results



async def responses_tooled(user_message: str,  thread_id:str=None, 
                           products:str=None, 
                           system_message: str = None, 
                           user_information: str = None,
                           client_phone:str = None):
    openai = OpenAIService()
    
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
        response = await openai.client.responses.create(
                model="gpt-4o",
                input=input_messages,
                temperature=0.1,
                tools=TOOLS,
                tool_choice="auto",
                )
    else:
         response = await openai.client.responses.create(
                model="gpt-4o",
                input=user_message,
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
            output = await required_query(tool_call)
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