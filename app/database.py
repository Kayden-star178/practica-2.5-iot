import pymysql
from app.config import settings

class Database:
    @staticmethod
    def get_connection():
        return pymysql.connect(
            host=settings.DB_HOST,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            port=settings.DB_PORT,
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )