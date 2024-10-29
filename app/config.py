from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from pathlib import Path

class Settings(BaseSettings):
    # Zoho Mail IMAP Configuration (existente)
    ZOHO_EMAIL: str
    ZOHO_PASSWORD: str
    ZOHO_IMAP_SERVER: str = "imap.zoho.com"
    ZOHO_IMAP_PORT: int = 993
    ZOHO_FOLDER: str = "Facturas_SAT"
    
    # Zoho Mail SMTP Configuration (nuevo)
    SMTP_SERVER: str = "smtp.zoho.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    NOTIFICATION_EMAIL: str
    ALERT_EMAIL: str
    
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Storage Configuration
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    XML_STORAGE_PATH: Path = BASE_DIR / "data" / "xml_files"
    PROCESSED_DATA_PATH: Path = BASE_DIR / "data" / "processed"
    
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Crear directorios necesarios si no existen
def create_required_directories():
    settings = get_settings()
    os.makedirs(settings.XML_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.PROCESSED_DATA_PATH, exist_ok=True)

# Llamar a la función cuando se importa el módulo
create_required_directories()