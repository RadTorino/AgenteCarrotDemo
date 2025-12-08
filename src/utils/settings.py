from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Sheet
    SHEET_ID: str
    EXCEL_NAME:str
    
    # Redis
    REDIS_HOST: str
    REDIS_PORT: int 
    REDIS_USERNAME: Optional[str] = None
    REDIS_PASSWORD: Optional[str] = None
    
    # OpenAI
    OPENAI_API_KEY: str
    
    
    # Google
    GOOGLE_CREDENTIALS_BASE64: str
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None
    
    # Gmail
    SENDER_EMAIL: str
    SENDER_PASSWORD: str
    SMTP_SERVER: str  
    SALES_EMAIL: str
    PROCUREMENT_EMAIL: str
    HR_EMAIL: str
    ORDERS_EMAIL: str
    BILLING_EMAIL: str
    SUPPORT_EMAIL: str
    
    # Whatsapp
    WHATSAPP_VERIFY_TOKEN: str = "abcd"
    APP_SECRET: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: str
    PHONE_NUMBER_ID: str
    WHATSAPP_API_VERSION: str = "v24.0"

    # Azure
    AZURE_TENANT_ID: str
    AZURE_CLIENT_ID: str
    AZURE_SECRET_ID: str 
    AZURE_CLIENT_SECRET: str
    SHAREPOINT_SITE_URL: str
    CERT_KEY:str
    THUMBPRINT: str

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
