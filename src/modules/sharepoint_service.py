import asyncio
import json
import os, uuid
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
from src.utils.settings import settings
from src.utils.logger import get_logger
import io, base64
import pandas as pd
from urllib.parse import urlparse, unquote

logger = get_logger(__name__)

class SharePointService:
    """
    A service for interacting with SharePoint, configured for multiple clients.
    """
    _instances = {}

    def __new__(cls, client_name: str):
        if client_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[client_name] = instance
        return cls._instances[client_name]

    def __init__(self, client_name: str):
        if not hasattr(self, '_db_lock'):
            self._db_lock = asyncio.Lock()
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.client_name = client_name
        self._load_config()
        self._authenticate()
        self._initialized = True

    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'sharepoint_config.json')
        with open(config_path, 'r') as f:
            full_config = json.load(f)
            if self.client_name not in full_config:
                raise ValueError(f"Client '{self.client_name}' not found in sharepoint_config.json")
            self.config = full_config[self.client_name]

    def _authenticate(self):
        cert_creds = {
            "tenant": settings.AZURE_TENANT_ID,
            "client_id": settings.AZURE_CLIENT_ID,
            "thumbprint": settings.THUMBPRINT,
            "private_key": base64.b64decode(settings.CERT_KEY_BASE64).decode('utf-8'),
        }
        
        site_url = self.config.get("site_url")
        if not site_url:
            raise ValueError(f"'site_url' not configured for client '{self.client_name}'")

        try:
            self.ctx = ClientContext(site_url).with_client_certificate(**cert_creds)
            logger.info(f"Successfully authenticated to SharePoint for client '{self.client_name}'.")
        except Exception as e:
            logger.error(f"Error authenticating to SharePoint for client '{self.client_name}': {e}")
            raise

    def _ensure_folder_exists(self, folder_path: str):
        """
        Ensures a folder exists at the given server-relative path.
        If it doesn't exist, it attempts to create it.
        Returns the folder object if it exists or was created, otherwise None.
        """
        # First, try to get the folder, assuming it exists.
        try:
            folder = self.ctx.web.get_folder_by_server_relative_url(folder_path)
            self.ctx.load(folder)
            self.ctx.execute_query()
            # If execute_query() succeeds, the folder exists.
            return folder
        except Exception as e:
            # The folder does not exist, so we will try to create it.
            logger.warning(f"Folder '{folder_path}' not found, attempting to create it. Details: {e}")

        # Create the folder since it doesn't exist.
        try:
            # The `folders.add` method creates the folder.
            folder = self.ctx.web.folders.add(folder_path)
            self.ctx.execute_query()
            logger.info(f"Successfully created folder: {folder_path}")
            return folder
        except Exception as e:
            logger.error(f"Failed to create folder '{folder_path}': {e}")
            # If creation fails, return None.
            return None

    def read_file(self, folder_key: str, file_name: str) -> io.BytesIO:
        folder_path = self.config["libraries"]["documents"]["folders"].get(folder_key)
        if not folder_path:
            raise ValueError(f"Folder key '{folder_key}' not found in config for client '{self.client_name}'")
        
        file_url = f"{folder_path}/{file_name}"
        try:
            file_content = io.BytesIO()
            file = self.ctx.web.get_file_by_server_relative_url(file_url)
            file.download(file_content).execute_query()
            file_content.seek(0)
            logger.info(f"Successfully read file '{file_name}' from '{folder_path}'.")
            return file_content
        except Exception as e:
            logger.error(f"Failed to read file '{file_name}' from '{folder_path}': {e}")
            raise

    def upload_file(self, folder_key: str, file_name: str, file_content: bytes) -> str:
        """
        Uploads a file to a specified folder in SharePoint.

        Args:
            folder_key: The key for the folder path in the config.
            file_name: The name of the file to upload.
            file_content: The content of the file in bytes.

        Returns:
            The full URL of the uploaded file.
        """
        folder_path = self.config["libraries"]["documents"]["folders"].get(folder_key)
        target_folder = self._ensure_folder_exists(folder_path)

        if not target_folder:
            fallback_folder_name = self.config.get("fallback_folder", "Error_Handling")
            logger.warning(f"Folder '{folder_path}' missing. Saving '{file_name}' in fallback folder '{fallback_folder_name}'")
            fallback_folder_path = f"Shared Documents/{fallback_folder_name}"
            target_folder = self._ensure_folder_exists(fallback_folder_path)
            if not target_folder:
                logger.error(f"Failed to find or create even the fallback folder. Aborting upload.")
                raise IOError("Could not ensure SharePoint folder existence.")

        try:
            target_file = target_folder.upload_file(file_name, file_content)
            self.ctx.execute_query()
            
            # The ServerRelativeUrl property gives a path like:
            # /sites/Desarrollo/Documentos compartidos/BOT Whatsapp/Staging/file.jpg
            relative_url = target_file.properties['ServerRelativeUrl']

            # The site_url from config is https://tenant.sharepoint.com/sites/Desarrollo
            # We need to get just the base part: https://tenant.sharepoint.com
            parsed_site_url = urlparse(self.config.get("site_url", ""))
            base_url = f"{parsed_site_url.scheme}://{parsed_site_url.netloc}"

            # By combining the base URL and the server-relative URL, we get the correct full path.
            full_url = f"{base_url}{relative_url}"

            logger.info(f"Successfully uploaded '{file_name}'.")
            logger.info(f"The final URL to be stored is: {full_url}")
            return full_url
        except Exception as e:
            logger.error(f"Failed to upload file '{file_name}': {e}")
            raise

    def move_file(self, source_file_url: str, dest_folder_key: str, file_name: str) -> str:
        """
        Moves a file from a source URL to a destination folder.

        Args:
            source_file_url: The server-relative URL of the file to move.
            dest_folder_key: The key for the destination folder path in the config.
            file_name: The name of the file.

        Returns:
            The full URL of the moved file, or None if the move fails.
        """
        dest_folder_path = self.config["libraries"]["documents"]["folders"].get(dest_folder_key)

        dest_folder = self._ensure_folder_exists(dest_folder_path)
        if not dest_folder:
            fallback_folder_name = self.config.get("fallback_folder", "Error_Handling")
            logger.warning(f"Destination folder '{dest_folder_path}' missing. Moving '{file_name}' to fallback folder '{fallback_folder_name}'")
            dest_folder_path = f"Documentos compartidos/{fallback_folder_name}"
            dest_folder = self._ensure_folder_exists(dest_folder_path)
            if not dest_folder:
                logger.error(f"Failed to find or create destination or fallback folder. Aborting move.")
                return None

        dest_file_relative_url = f"{dest_folder.properties['ServerRelativeUrl']}"

        try:
            file_to_move = self.ctx.web.get_file_by_server_relative_url(unquote(urlparse(source_file_url).path))    #get_file_by_server_relative_ur l(source_file_url)
            file_to_move.moveto(dest_file_relative_url, 1).execute_query()
            
            parsed_site_url = urlparse(self.config.get("site_url", ""))
            base_url = f"{parsed_site_url.scheme}://{parsed_site_url.netloc}"
            full_dest_url = f"{base_url}/{dest_file_relative_url.lstrip('/')}/{file_name}"

            logger.info(f"Successfully moved '{file_name}' to '{full_dest_url}'.")
            return full_dest_url
        except Exception as e:
            logger.error(f"Failed to move file '{file_name}': {e}")
            # In case of failure, we might want to return None or raise the exception
            # depending on how the caller should handle it.
            return None

    async def read_worksheet_as_df(self, folder_key: str, file_name: str, worksheet_name: str) -> pd.DataFrame:
        """
        Reads a specific worksheet from an Excel file in SharePoint and returns it as a pandas DataFrame.

        Args:
            folder_key: The key for the folder path in the config.
            file_name: The name of the Excel file.
            worksheet_name: The name of the worksheet to read.

        Returns:
            A pandas DataFrame containing the data from the worksheet.
        """
        logger.info(f"Reading worksheet '{worksheet_name}' from '{file_name}'...")
        try:
            file_content_stream = self.read_file(folder_key=folder_key, file_name=file_name)
            df = pd.read_excel(file_content_stream, sheet_name=worksheet_name, engine='openpyxl')
            logger.info(f"Successfully read worksheet '{worksheet_name}'.")
            return df
        except Exception as e:
            logger.error(f"Failed to read worksheet '{worksheet_name}' from '{file_name}': {e}")
            raise

    async def add_row_to_worksheet(self, folder_key: str, file_name: str, worksheet_name: str, row_data: dict) -> dict:
        """
        Adds a new row to a specific worksheet in an Excel file, ensuring thread-safe operation.
        This method is atomic, preventing race conditions during concurrent writes.

        Args:
            folder_key: The key for the folder path in the config.
            file_name: The name of the Excel file.
            worksheet_name: The name of the worksheet to modify.
            row_data: A dictionary representing the new row to add.

        Returns:
            The dictionary of the row that was added, including a generated ID if one was not provided.
        """
        if not row_data.get('id'):
            row_data['id'] = str(uuid.uuid4())

        async with self._db_lock:
            logger.info(f"Acquired lock to write to '{file_name}'. Adding row to '{worksheet_name}'.")
            try:
                # 1. Read the entire Excel file
                file_content_stream = self.read_file(folder_key=folder_key, file_name=file_name)
                all_sheets = pd.read_excel(file_content_stream, engine='openpyxl', sheet_name=None)

                if worksheet_name not in all_sheets:
                    raise ValueError(f"Worksheet '{worksheet_name}' not found in '{file_name}'.")

                # 2. Modify the target worksheet
                target_df = all_sheets[worksheet_name]
                new_row_df = pd.DataFrame([row_data])
                updated_df = pd.concat([target_df, new_row_df], ignore_index=True)
                all_sheets[worksheet_name] = updated_df

                # 3. Write all sheets back to an in-memory file
                output_stream = io.BytesIO()
                with pd.ExcelWriter(output_stream, engine='openpyxl') as writer:
                    for sheet_name, sheet_df in all_sheets.items():
                        sheet_df.to_excel(writer, index=False, sheet_name=sheet_name)
                
                updated_file_content = output_stream.getvalue()

                # 4. Upload the modified file, overwriting the old one
                self.upload_file(folder_key, file_name, updated_file_content)
                
                logger.info(f"Successfully added row and uploaded updated '{file_name}'.")
                return row_data
            except Exception as e:
                logger.error(f"An error occurred during the locked write operation: {e}")
                raise
            finally:
                logger.info(f"Released lock for '{file_name}'.")