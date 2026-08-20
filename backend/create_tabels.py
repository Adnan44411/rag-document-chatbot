import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

DB_URL = os.getenv("DATABASE_URL")

conn = None

try:
    conn = psycopg2.connect(DB_URL)
    print("Connected to the database successfully.")

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            prompt TEXT NOT NULL,
            answer TEXT NOT NULL
        );
    """)

    conn.commit()
    cursor.close()

    print("Tables created successfully.")

except (Exception, psycopg2.DatabaseError) as e:
    print(f"Error connecting to the database: {e}")

finally:
    if conn is not None:
        conn.close()
