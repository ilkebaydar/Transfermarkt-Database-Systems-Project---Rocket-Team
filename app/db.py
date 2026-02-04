import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
from pathlib import Path 

base_dir = Path(__file__).resolve().parent.parent
env_file = base_dir / '.env'

load_dotenv(dotenv_path=env_file)

def get_db_connection():
    """Establishes a connection to the MySQL database."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
        return connection
    except Error as e:
        print(f"[DB] Connection error: {e}")
        return None
