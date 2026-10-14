import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_USER: str = os.getenv("DB_USER", "root")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
        self.DB_NAME: str = os.getenv("DB_NAME", "vehiculo_iot")
        self.DB_PORT: int = int(os.getenv("DB_PORT", 3306))

settings = Settings()