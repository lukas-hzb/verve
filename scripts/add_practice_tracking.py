#!/usr/bin/env python3
"""
Migration script to add practice mode wrong answer tracking.
Run this with: python run_migration.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.database import db
from sqlalchemy import text

def run_migration():
    """Add last_practice_wrong column to cards table."""
    app = create_app()
    
    with app.app_context():
        print("🔧 Adding 'last_practice_wrong' column to cards table...")
        
        try:
            # Check if column already exists
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='cards' AND column_name='last_practice_wrong'
                """)).fetchone()
                
                if result:
                    print("✅ Column 'last_practice_wrong' already exists. Skipping.")
                    return
            
            # Add the column
            with db.engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE cards 
                    ADD COLUMN last_practice_wrong BOOLEAN DEFAULT FALSE
                """))
                conn.commit()
            
            print("✅ Successfully added 'last_practice_wrong' column")
            
        except Exception as e:
            print(f"❌ Error adding column: {e}")
            raise

if __name__ == "__main__":
    run_migration()
    print("\n✨ Migration complete!")
