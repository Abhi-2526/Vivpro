import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration loaded from environment variables"""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "database.db")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_TITLE: str = os.getenv("API_TITLE", "Music Playlist API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    
    # Data Configuration
    DEFAULT_JSON_FILE: str = os.getenv("DEFAULT_JSON_FILE", "playlist.json")

# Create a global config instance
config = Config() 