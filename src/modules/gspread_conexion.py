import json, base64, gspread, uuid, pytz
from datetime import datetime
from google.oauth2.service_account import Credentials
from src.utils.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
tz_buenos_aires = pytz.timezone('America/Argentina/Buenos_Aires')

def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    cred_base64 = settings.GOOGLE_CREDENTIALS_BASE64.strip("'")
    if not cred_base64:
        raise ValueError("No se encontró GOOGLE_CREDENTIALS_BASE64 en el entorno.")

    # Decodificar base64 y parsear como JSON
    cred_json = json.loads(base64.b64decode(cred_base64).decode("utf-8"))

    credentials = Credentials.from_service_account_info(cred_json, scopes=scopes)
    return gspread.authorize(credentials)


def leer_google_sheet(sheet_id, worksheet_name):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(worksheet_name)
    headers = worksheet.row_values(1)
    data = worksheet.get_all_records(expected_headers=headers)
    return data

def add_phone_to_client(sheet_id, user_id, phone_number):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    phone_worksheet = sheet.worksheet("phones")

    # Generamos un UUID único para el nuevo número de teléfono
    phone_id = str(uuid.uuid4())
    nueva_fila = [
        phone_id,
        user_id,
        phone_number
    ]

    phone_worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
    return phone_id

def insertar_cliente(sheet_id, worksheet_name, nombre_comercial, cuit, direccion, phone_number):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    client_worksheet = sheet.worksheet("clients")

    # Generamos un UUID único para el nuevo cliente
    client_id = str(uuid.uuid4())
    fecha_actual = datetime.now(tz_buenos_aires).strftime("%Y-%m-%d %H:%M:%S")
    nueva_fila = [
        client_id,
        nombre_comercial,
        cuit,
        direccion,
        fecha_actual
    ]

    client_worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
    add_phone_to_client(
        sheet_id=sheet_id,
        user_id=client_id,
        phone_number=phone_number
    )
    return client_id

def insertar_pedido(sheet_id, worksheet_name, user_id, product_id, quantity):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(worksheet_name)

    # Generamos un UUID único para el nuevo pedido
    nuevo_id = str(uuid.uuid4())

    nueva_fila = [
        nuevo_id,
        user_id,
        product_id,
        quantity
    ]

    worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
    return nuevo_id

def buscar_cliente_por_cuit(clientes_data, cuit):
    for fila in clientes_data:
        if fila.get("cuit") == cuit:
            return fila
    return None

def crear_pedido_completo(sheet_id, user_id, products, worksheet_pedidos_name="orders", worksheet_items_name="orders_detail"):
    """
    Crea un pedido completo en dos hojas de Google Sheets: 'Pedidos' e 'Items de Pedido'.
    
    Args:
        sheet_id (str): ID de la hoja de cálculo de Google.
        user_id (str): UUID del cliente.
        products (list): Lista de diccionarios, donde cada uno contiene 'product_id' y 'quantity'.
        worksheet_pedidos_name (str): Nombre de la hoja para los pedidos principales.
        worksheet_items_name (str): Nombre de la hoja para los ítems de cada pedido.
    
    Returns:
        str: El UUID del pedido creado.
    """
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)

    # Paso 1: Generar un UUID único para el nuevo pedido
    pedido_id = str(uuid.uuid4())
    fecha_actual = datetime.now(tz_buenos_aires).strftime("%Y-%m-%d %H:%M:%S")


    # Paso 2: Insertar la fila principal en la hoja de Pedidos
    try:
        worksheet_pedidos = sheet.worksheet(worksheet_pedidos_name)
        fila_pedido = [
            pedido_id,
            user_id,
            fecha_actual,
            "pending" # Estado inicial del pedido
        ]
        worksheet_pedidos.append_row(fila_pedido, value_input_option="USER_ENTERED")
    except Exception as e:
        logger.error(f"Error al insertar en la hoja '{worksheet_pedidos_name}': {e}", exc_info=True)
        return None

    # Paso 3: Recorrer la lista de productos e insertar cada ítem
    try:
        worksheet_items = sheet.worksheet(worksheet_items_name)
        filas_items = []
        products_catalog = leer_google_sheet(sheet_id, "products")
        for item in products:
            item_id = str(uuid.uuid4())
            unit_price = next((prod.get("unit_price") for prod in products_catalog if str(prod.get("id")) == str(item.get("product_id"))), 0)
            if unit_price == 0:
                logger.warning(f"Advertencia: No se encontró el producto con ID {item.get('product_id')} en el catálogo.")
            filas_items.append([
                item_id,
                pedido_id,
                item.get("product_id"),
                item.get("quantity"),
                unit_price
            ])
            logger.debug(f"Preparando ítem para insertar: {filas_items[-1]}")
        if filas_items:
            worksheet_items.append_rows(filas_items, value_input_option="USER_ENTERED")
    except Exception as e:
        logger.error(f"Error al insertar en la hoja '{worksheet_items_name}': {e}", exc_info=True)
        # En una versión de producción, querrías revertir el pedido principal si falla la inserción de ítems.
        return None

    logger.info(f"Pedido completo {pedido_id} creado con {len(products)} ítems.")
    return pedido_id

def get_client_by_phone(phone_number):
    sheet_id = settings.SHEET_ID
    worksheet_name = "phones"
    phones = leer_google_sheet(sheet_id, worksheet_name)
    
    for fila in phones:
        if str(fila.get("phone_number")) in str(phone_number):
            user_id = fila.get("user_id")
            client_info = leer_google_sheet(sheet_id, "clients")
            for client in client_info:
                if client.get("id") == user_id:
                    return client
    return None
