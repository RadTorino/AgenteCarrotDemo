from dotenv import load_dotenv
import os
load_dotenv()

SHEET_ID= os.getenv("SHEET_ID")

config = {
    "clientes_sheet_id": SHEET_ID,
    "clientes_worksheet_name": "clients",
    "compras_sheet_id": SHEET_ID,
    "compras_worksheet_name": "orders",
    "products_sheet_id": SHEET_ID,
    "products_worksheet_name": "products",
}

conversations = {}