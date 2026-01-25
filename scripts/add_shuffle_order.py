
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from sqlalchemy import text

def add_column():
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    with app.app_context():
        print("Adding shuffle_order column to cards table...")
        try:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE cards ADD COLUMN shuffle_order INTEGER"))
                conn.commit()
            print("Successfully added shuffle_order column.")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("Column shuffle_order already exists.")
            else:
                print(f"Error adding column: {e}")

if __name__ == "__main__":
    add_column()
