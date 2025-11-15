from google.oauth2 import service_account
from googleapiclient.discovery import build
from src.utils.settings import settings

credentials = service_account.Credentials.from_service_account_file(
    settings.GOOGLE_APPLICATION_CREDENTIALS,
    scopes=['https://www.googleapis.com/auth/drive']
    )
drive_service = build('drive', 'v3', credentials=credentials)