
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
load_dotenv(BASE_DIR / '.env.local', override=True)

uri = os.getenv('SQLALCHEMY_DATABASE_URI')
if not uri:
    raise RuntimeError('SQLALCHEMY_DATABASE_URI is not configured')

print(f"Loaded endpoint: {uri.rsplit('@', 1)[-1]}")  # Never print credentials.

try:
    print("Attempting to connect...")
    engine = create_engine(uri)
    with engine.connect() as conn:
        print("Connection successful!")
        result = conn.execute(text("SELECT 1"))
        print(f"Test query result: {result.fetchone()}")
except Exception as e:
    print(f"Connection failed: {e}")
