import os
from supabase import create_client, Client
from flask import current_app

class SupabaseClient:
    _instance = None
    _client = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create the Supabase client instance.
        Uses environment variables for configuration.
        """
        if cls._client is None:
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_ANON_KEY")
            
            if not url or not key:
                # Fallback or error logging - but allowing app to start if not needed immediately
                # This is important during the migration phase where keys might be missing
                if current_app:
                    current_app.logger.warning("Supabase credentials missing! Auth features will fail.")
                return None
                
            cls._client = create_client(url, key)
            
        return cls._client

    @classmethod
    def get_service_role_client(cls) -> Client:
        """
        Get a client with SERVICE ROLE privileges.
        DANGER: Only use this for backend administration and migration scripts.
        """
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required for administrative actions")
            
        return create_client(url, key)
