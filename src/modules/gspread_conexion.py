import os
import json
import base64
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1ulA9lcflYyrA76GkUsGluOynjOD-dELM8qLjD92HhY8"

def get_gspread_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]

    cred_base64 = os.getenv("GOOGLE_CREDENTIALS_BASE64").strip("'")
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
    data = worksheet.get_all_records()
    return data

import uuid

def insertar_cliente(sheet_id, worksheet_name, nombre_comercial, cuit, direccion):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(worksheet_name)

    nuevo_id = obtener_siguiente_id(sheet_id, worksheet_name)

    nueva_fila = [
        nuevo_id,
        nombre_comercial,
        cuit,
        direccion
    ]

    worksheet.append_row(nueva_fila, value_input_option="USER_ENTERED")
    return nuevo_id

def insertar_pedido(sheet_id, worksheet_name, user_id, product_id, quantity):
    client = get_gspread_client()
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.worksheet(worksheet_name)

    nuevo_id = obtener_siguiente_id(sheet_id, worksheet_name)

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


def obtener_siguiente_id(sheet_id, worksheet_name):
    data = leer_google_sheet(sheet_id, worksheet_name)
    ids = []

    for fila in data:
        try:
            id_val = int(fila.get("id", 0))
            ids.append(id_val)
        except (ValueError, TypeError):
            continue

    max_id = max(ids) if ids else 0
    return str(max_id + 1)

