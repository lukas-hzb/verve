import firebase_admin
from firebase_admin import credentials, firestore
from flask import current_app
import os

_db = None

def init_firestore(app):
    """Initialize Firebase Admin SDK and Firestore client."""
    global _db
    
    cred_path = app.config.get('FIREBASE_CREDENTIALS')
    if not cred_path or not os.path.exists(cred_path):
        app.logger.warning(f"Firebase credentials not found at {cred_path}")
        return

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
        
        _db = firestore.client()
        app.logger.info("Firebase Firestore initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize Firebase: {e}")
        raise e

def get_db():
    """Get the Firestore client instance."""
    global _db
    return _db
