from src.modules.gspread_conexion import (
    insertar_cliente,
    crear_pedido_completo,
    leer_google_sheet,
    add_phone_to_client)
from src.modules.gmail_connection import send_notification
from src.utils.config import config
import logging 
from src.schemas.schemas import NotificacionSchema

async def handle_create_purchase(arguments):

    try: 
        nuevo_id = crear_pedido_completo(
            sheet_id=config["compras_sheet_id"],
            user_id=arguments["user_id"],
            products=arguments["products"]
        )
        query_results = {"new_purchase_id": nuevo_id}
        return query_results
    except Exception as e:
        logging.error(f"Error al crear la compra: {e}")
        return {"error": "Error al crear la compra."}



async def handle_get_client_orders(arguments):
    
    try:
        compras = leer_google_sheet(
            sheet_id=config["compras_sheet_id"],
            worksheet_name=config["compras_worksheet_name"]
        )
        print(f"Compras obtenidas: {compras}")
        compras_cliente = [c for c in compras if str(c.get("user_id"))== str(arguments["user_id"])]
        orders_detail = leer_google_sheet(
                sheet_id=config["compras_sheet_id"],
                worksheet_name="orders_detail")
        for compra in compras_cliente:
            compra_id = compra.get("id")
            detalles = [
            {k: v for k, v in d.items() if k not in ["id", "order_id"]}
            for d in orders_detail
            if str(d.get("order_id")) == str(compra_id)
        ]
            compra["details"] = detalles
        query_results = {"orders": compras_cliente}
        return query_results
    except Exception as e:
        logging.error(f"Error al obtener las compras del cliente: {e}")
        return {"error": "Error al obtener las compras del cliente."}
    


async def handle_get_client(arguments):
    
    try:       
        clientes = leer_google_sheet(
            sheet_id=config["clientes_sheet_id"],
            worksheet_name=config["clientes_worksheet_name"]
        )
        cliente = next((c for c in clientes if str(c.get("cuit")) == str(arguments["cuit"])), None)
        query_results = {"client": cliente} if cliente else {"error": "Cliente no encontrado."}
        return query_results
    except Exception as e:
        logging.error(f"Error al obtener el cliente: {e}")
        return {"error": "Error al obtener el cliente."}
    


async def handle_link_phone_to_client(arguments):
    try:
        phone_id = add_phone_to_client(
            sheet_id=config["compras_sheet_id"],
            user_id = arguments["user_id"],
            phone_number=arguments["phone_number"]
        )
        query_results = {"phone_id": phone_id}
        return query_results
    except Exception as e:
        logging.error(f"Error al vincular el teléfono al cliente: {e}")
        return {"error": "Error al vincular el teléfono al cliente."}

async def handle_contact_company(arguments):
    try:
            
        type_of_contact = arguments.get("type")
        data_payload = arguments.get("data", {})
        user_id = arguments.get("user_id") # Opcional/condicional

        logging.info(f"Iniciando flujo de contacto tipo: {type_of_contact}")

        # Llama a la función de negocio (send_notification)
        success = await send_notification(NotificacionSchema(
            type=type_of_contact,
            data=data_payload,
            user_id=user_id,  ))
        
        if success:
            query_results = {"success": True, "message": f"Notificación de tipo '{type_of_contact}' enviada correctamente."}
        else:
            query_results = {"success": False, "error": f"Error al enviar notificación de tipo '{type_of_contact}'."}
        return query_results
    except Exception as e:
        logging.error(f"Error al contactar a la empresa: {e}")
        return {"error": "Error al contactar a la empresa."}