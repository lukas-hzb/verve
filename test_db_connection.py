
import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text

load_dotenv()

uri = os.getenv('SQLALCHEMY_DATABASE_URI')
print(f"Loaded URI: {uri.split('@')[1] if '@' in uri else 'INVALID URI'}") # Don't print password

try:
    print("Attempting to connect...")
    engine = create_engine(uri)
    with engine.connect() as conn:
        print("Connection successful!")
        result = conn.execute(text("SELECT 1"))
        print(f"Test query result: {result.fetchone()}")
except Exception as e:
    print(f"Connection failed: {e}")
