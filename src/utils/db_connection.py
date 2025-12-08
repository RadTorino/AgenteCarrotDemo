from src.modules.sharepoint_service import SharePointService
from utils.logger import get_logger 

logger = get_logger(__name__)

sp_client= SharePointService(client_name='Celula')

async def get_client_by_phone(phone_number: str):
    """
    Retrieve client information from SharePoint based on phone number.
    """
    try:
        client_info = await sp_client.read_worksheet_as_df(folder_key="mother",
                        file_name="db_celula.xlsx", worksheet_name="clients")
        client_record = client_info[client_info['phone_number'] == phone_number]
        if not client_record.empty:
            logger.info(f"Client found: {client_record.to_dict(orient='records')[0]}")
            return client_record.to_dict(orient='records')[0]
        else:
            logger.info(f"No client found with phone number: {phone_number}")
            return None
    except Exception as e:
        logger.error(f"Error retrieving client by phone number {phone_number}: {e}")
    
        return None
    
async def get_products():
    """
    Retrieve products from SharePoint.
    """
    try:
        products_df = await sp_client.read_worksheet_as_df(folder_key="mother",
                        file_name="db_celula.xlsx", worksheet_name="products")
        products_list = products_df.to_dict(orient='records')
        logger.info(f"Retrieved {len(products_list)} products.")
        logger.debug(f"Products data: {products_list}")
        return products_list
    except Exception as e:
        logger.error(f"Error retrieving products: {e}")
        return []