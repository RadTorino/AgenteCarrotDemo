import logging
import uuid
from datetime import datetime
import pytz
from src.modules.gspread_conexion import leer_google_sheet, crear_pedido_completo, add_phone_to_client
from utils.config import config
from utils.settings import settings
from src.modules.sharepoint_service import SharePointService
from src.modules.file_mapping_service import FileMappingService
from src.modules.gmail_connection import send_notification, NotificacionSchema
from src.utils.db_connection import get_products

logger = logging.getLogger(__name__)

# Instantiate the SharePoint service
# Replace 'your_client_name' with the actual client name from your config
sp_service = SharePointService(client_name='Celula')
EXCEL_FILE_NAME = config["excel_name"] # The name of your Excel file

async def handle_create_purchase(arguments):
    """
    Creates a complete purchase order by adding a record to the 'orders' table
    and corresponding items to the 'orders_detail' table in the SharePoint Excel file.
    """
    try:
        # --- New SharePoint Logic ---
        order_id = str(uuid.uuid4())
        tz_buenos_aires = pytz.timezone('America/Argentina/Buenos_Aires')
        fecha_actual = datetime.now(tz_buenos_aires).strftime("%Y-%m-%d %H:%M:%S")

        products = await get_products()

        # 1. Add the main order row
        order_row = {
            "id": order_id,
            "user_id": arguments["user_id"],
            "fecha": fecha_actual,
            "status": "pending"
        }
        await sp_service.add_row_to_worksheet(
            folder_key="mother",
            file_name=EXCEL_FILE_NAME,
            worksheet_name=config["orders_worksheet_name"],
            row_data=order_row
        )

        # 2. Add each product to the order details
        for product in arguments.get("products", []):
            detail_row = {
                "order_id": order_id,
                "product_id": product.get("product_id"),
                "quantity": product.get("quantity"),
                "unit_price": next((p["price"] for p in products if p["id"] == product.get("product_id")), 0)
                # Assuming unit_price is handled or not needed here for now
            }
            await sp_service.add_row_to_worksheet(
                folder_key="mother",
                file_name=EXCEL_FILE_NAME,
                worksheet_name="orders_detail",
                row_data=detail_row
            )
        
        query_results = {"new_purchase_id": order_id}
        return query_results

        # --- Old Google Sheets Logic ---
        # nuevo_id = crear_pedido_completo(
        #     sheet_id=config["compras_sheet_id"],
        #     user_id=arguments["user_id"],
        #     products=arguments["products"]
        # )
        # query_results = {"new_purchase_id": nuevo_id}
        # return query_results
    except Exception as e:
        logging.error(f"Error al crear la compra: {e}")
        return {"error": "Error al crear la compra."}


async def handle_get_client_orders(arguments):
    """
    Retrieves all orders and their details for a given client from the SharePoint Excel file.
    """
    try:
        # --- New SharePoint Logic ---
        orders_df = await sp_service.read_worksheet_as_df(
            folder_key="mother", file_name=EXCEL_FILE_NAME, worksheet_name="orders"
        )
        orders_detail_df = await sp_service.read_worksheet_as_df(
            folder_key="mother", file_name=EXCEL_FILE_NAME, worksheet_name="orders_detail"
        )

        # Filter orders for the specific user
        client_orders_df = orders_df[orders_df['user_id'].astype(str) == str(arguments["user_id"])]
        compras_cliente = client_orders_df.to_dict('records')

        # Attach order details to each order
        for compra in compras_cliente:
            compra_id = compra.get("id")
            details_df = orders_detail_df[orders_detail_df['order_id'].astype(str) == str(compra_id)]
            # Remove redundant IDs from the details
            compra["details"] = details_df.drop(columns=['id', 'order_id'], errors='ignore').to_dict('records')

        query_results = {"orders": compras_cliente}
        return query_results

        # --- Old Google Sheets Logic ---
        # compras = leer_google_sheet(
        #     sheet_id=config["compras_sheet_id"],
        #     worksheet_name=config["compras_worksheet_name"]
        # )
        # print(f"Compras obtenidas: {compras}")
        # compras_cliente = [c for c in compras if str(c.get("user_id"))== str(arguments["user_id"])]
        # orders_detail = leer_google_sheet(
        #         sheet_id=config["compras_sheet_id"],
        #         worksheet_name="orders_detail")
        # for compra in compras_cliente:
        #     compra_id = compra.get("id")
        #     detalles = [
        #     {k: v for k, v in d.items() if k not in ["id", "order_id"]}
        #     for d in orders_detail
        #     if str(d.get("order_id")) == str(compra_id)
        # ]
        #     compra["details"] = detalles
        # query_results = {"orders": compras_cliente}
        # return query_results
    except Exception as e:
        logging.error(f"Error al obtener las compras del cliente: {e}")
        return {"error": "Error al obtener las compras del cliente."}


async def handle_get_client(arguments):
    """
    Finds a client by their CUIT in the SharePoint Excel file.
    """
    try:
        # --- New SharePoint Logic ---
        clients_df = await sp_service.read_worksheet_as_df(
            folder_key="mother", file_name=EXCEL_FILE_NAME, worksheet_name="clients"
        )
        # Find the client row
        client_series = clients_df[clients_df['cuit'].astype(str) == str(arguments["cuit"])].iloc[0]
        cliente = client_series.to_dict()
        query_results = {"client": cliente}
        return query_results

        # --- Old Google Sheets Logic ---
        # clientes = leer_google_sheet(
        #     sheet_id=config["clientes_sheet_id"],
        #     worksheet_name=config["clientes_worksheet_name"]
        # )
        # cliente = next((c for c in clientes if str(c.get("cuit")) == str(arguments["cuit"])), None)
        # query_results = {"client": cliente} if cliente else {"error": "Cliente no encontrado."}
        # return query_results
    except (Exception, IndexError): # IndexError if client not found
        logging.error(f"Error al obtener el cliente o cliente no encontrado: {arguments.get('cuit')}")
        return {"error": "Cliente no encontrado."}


async def handle_link_phone_to_client(arguments):
    """
    Links a phone number to a client by adding a row to the 'phones' table.
    """
    try:
        # --- New SharePoint Logic ---
        phone_row = {
            "user_id": arguments["user_id"],
            "phone_number": arguments["phone_number"]
        }
        added_row = await sp_service.add_row_to_worksheet(
            folder_key="mother",
            file_name=EXCEL_FILE_NAME,
            worksheet_name="phones",
            row_data=phone_row
        )
        query_results = {"phone_id": added_row.get("id")}
        return query_results

        # --- Old Google Sheets Logic ---
        # phone_id = add_phone_to_client(
        #     sheet_id=config["compras_sheet_id"],
        #     user_id = arguments["user_id"],
        #     phone_number=arguments["phone_number"]
        # )
        # query_results = {"phone_id": phone_id}
        # return query_results
    except Exception as e:
        logging.error(f"Error al vincular el teléfono al cliente: {e}")
        return {"error": "Error al vincular el teléfono al cliente."}

async def handle_contact_company(arguments):
    try:
        type_of_contact = arguments.get("type")
        data_payload = arguments.get("data", {})
        user_id = arguments.get("user_id")

        # Define the possible keys for a file ID in a preferred order of checking.
        file_id_keys = [
            "id_de_imagen",
            "id_al_cv",
            "documento_presentacion",
            "id_del_archivo"
        ]

        # Find the first key within data_payload that has a non-empty value.
        file_id = next((data_payload.get(key) for key in file_id_keys if data_payload.get(key)), None)

        logger.info(f"File ID '{file_id}' found for contact type '{type_of_contact}'.")
        logger.info(f"Initiating contact flow for type: {type_of_contact}")

        final_file_url = None
        if file_id:
            logger.info(f"File ID '{file_id}' found, proceeding with file move.")

            # 1. Obtener la URL temporal del archivo en 'staging'
            file_mapping_service = FileMappingService()
            file_info = file_mapping_service.get_link(file_id)

            logger.info(f"File info retrieved: {file_info}")
            
            if not file_info:
                logger.error(f"No file mapping found for file_id: {file_id}")
                return {"error": "File information not found."}

            source_file_url = file_info
            file_name = file_info.split("/")[-1]
            
            site_url_base = f"https://{settings.AZURE_TENANT_ID}.sharepoint.com"
            server_relative_url = source_file_url.replace(site_url_base, "")


            # 2. Mover el archivo a la carpeta de destino
            sharepoint_service = SharePointService(client_name="Celula") ## revisar este hardcoding
            final_file_url = sharepoint_service.move_file(
                source_file_url=server_relative_url,
                dest_folder_key=type_of_contact, # La clave de la carpeta es el tipo de contacto
                file_name=file_name
            )
            
            logger.info(f"File moved to final URL: {final_file_url}")

            if not final_file_url:
                logger.error(f"Failed to move file {file_name} for file_id {file_id}.")
                # Decidir si fallar o continuar sin la URL
                return {"error": "Failed to move the file in SharePoint."}
            
            logger.info(f"File moved successfully. New URL: {final_file_url}")

        # 3. Enviar la notificación por correo
        success = await send_notification(NotificacionSchema(
            type=type_of_contact,
            data=data_payload,
            user_id=user_id,
            file_url=final_file_url # Pasar la URL final
        ))
        
        if success:
            return {"success": True, "message": f"Notificación de tipo '{type_of_contact}' enviada correctamente."}
        else:
            logger.error(f"Error al enviar la notificación de tipo '{type_of_contact}'.")
            return {"error": "Error al enviar la notificación."}

    except Exception as e:
        logger.error(f"Error en handle_contact_company: {e}", exc_info=True)
        return {"error": "Ocurrió un error inesperado al procesar el contacto."}