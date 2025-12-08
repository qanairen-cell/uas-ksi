import psycopg2
import os
from dotenv import load_dotenv

# Load .env
load_dotenv()

def get_db():
    try:
        conn = psycopg2.connect(
            host=os.getenv("PGHOST"),
            port=os.getenv("PGPORT"),
            user=os.getenv("PGUSER"),
            password=os.getenv("PGPASSWORD"),
            database=os.getenv("PGDATABASE"),
            sslmode="require"   # Railway WAJIB pakai SSL!
        )
        return conn
    except Exception as e:
        print("Database connection error:", e)
        return None
