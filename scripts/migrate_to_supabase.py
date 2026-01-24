import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.database import db
from app.models import User
from app.supabase_client import SupabaseClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_users():
    """
    Migrate users from local database to Supabase Auth.
    
    Strategy:
    1. Fetch all local users.
    2. For each user:
       - Check if they exist in Supabase Auth (by email).
       - If not, create them using their existing email and password hash.
       - Update the local User record to match the Supabase Auth ID (UUID).
    """
    app = create_app('production')
    
    # We need the Service Role Key to manage users and import hashes
    # Check for key manually since the client helper might return the anon client
    service_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not service_key:
        logger.error("SUPABASE_SERVICE_ROLE_KEY is required for migration!")
        print("Please add SUPABASE_SERVICE_ROLE_KEY to your .env file.")
        return

    supabase = SupabaseClient.get_service_role_client()
    
    with app.app_context():
        users = User.query.all()
        logger.info(f"Found {len(users)} users to migrate.")
        
        for user in users:
            logger.info(f"Processing user: {user.username} ({user.email})")
            
            try:
                # 1. Check if user already exists in Supabase
                # We can't search by email directly with admin API easily without listing?
                # Actually create_user will fail if exists.
                
                # Prepare attributes
                # Note: Supabase Auth expects bcrypt hashes to be imported specifically.
                # If we use create_user with 'password', it hashes it AGAIN.
                # We need to use `import_users` if we want to preserve hashes, 
                # OR we just set a temporary password and ask them to reset (Not ideal user experience).
                # Supabase Python SDK/GoTrue client supports creating users.
                
                # Check if we can import the hash.
                # The python supabase client maps to GoTrue. 
                # admin.create_user doesn't easily support passing a pre-hashed password in standard params.
                # HOWEVER, we can try to just create them. 
                
                # Only way to preserve password without knowing it is to use the import endpoint (often not exposed in simple SDKs)
                # OR simply re-create them with a temporary password if import isn't feasible.
                # Let's try to see if we can just create them. 
                
                # BETTER STRATEGY FOR NOW: 
                # Create user with a dummy password if we can't import hash?
                # User said: "Ohne Änderung für den Nutzer". This implies keeping passwords.
                # If we can't import hashes via Python SDK easily, we might fallback.
                # BUT, Supabase allows `invite_user_by_email` or similar.
                
                # Let's try to create user.
                # Using a dummy password "ChangeMe123!" if we can't port the hash.
                # Wait, if we use Supabase Auth, we WANT to use the hash.
                
                # Let's look at the User model. It has `password_hash`.
                # If it's standard bcrypt, Supabase supports it.
                # We might need to use raw SQL on the `auth.users` table? 
                # We have the connection string! We have `postgres` user!
                # We can INSERT directly into `auth.users`!
                # This is the most robust way if we have direct DB access.
                
                # Direct SQL Insert Strategy
                from sqlalchemy import text
                
                # Check if user exists in auth.users
                check_sql = text("SELECT id FROM auth.users WHERE email = :email")
                result = db.session.execute(check_sql, {'email': user.email}).fetchone()
                
                auth_user_id = None
                
                if result:
                    logger.info(f"User {user.email} already in Supabase Auth.")
                    auth_user_id = result[0]
                else:
                    logger.info(f"Migrating {user.email} to Supabase Auth...")
                    # Insert into auth.users
                    # This requires knowing the schema. 
                    # Generally: id, email, encrypted_password, email_confirmed_at, etc.
                    
                    # If we don't dare direct INSERT (risky if schema changes), use SDK.
                    # SDK `admin.create_user` takes `password` (plaintext).
                    # We don't have plaintext.
                    
                    # Compromise: Check if we can just update the `public.users` table to MATCH the existing ID if it exists,
                    # If not, we might have to ask the user to reset password OR we assume the user already did something?
                    # No, the user expects smooth transition.
                    
                    # Let's assume we use the SDK to create the user with a RANDOM password,
                    # and then we UPDATE the record in `auth.users` with the OLD hash using SQL? 
                    # Yes! That bridges the gap.
                    
                    # 1. Create with random password
                    import secrets
                    temp_pass = secrets.token_urlsafe(12)
                    try:
                        res = supabase.auth.admin.create_user({
                            "email": user.email,
                            "password": temp_pass,
                            "email_confirm": True,
                            "user_metadata": {"username": user.username}
                        })
                        auth_user_id = res.user.id
                        
                        # Only update password hash if we just created them
                        # 2. Overwrite password hash with old hash using Direct SQL
                        update_pass_sql = text("""
                            UPDATE auth.users 
                            SET encrypted_password = :hash 
                            WHERE id = :uid
                        """)
                        db.session.execute(update_pass_sql, {'hash': user.password_hash, 'uid': auth_user_id})
                        db.session.commit() # Commit the auth change
                        logger.info(f"User created and password hash synced for {user.email}")
                        
                    except Exception as e:
                        # If user exists, we need to find their ID. 
                        # We try querying again or assume we found it in step 1 BUT step 1 returned None earlier?
                        # Maybe partial failure.
                        # Let's try querying auth.users again.
                        logger.warning(f"Could not create user (maybe exists?): {e}")
                        
                        existing = db.session.execute(check_sql, {'email': user.email}).fetchone()
                        if existing:
                             auth_user_id = existing[0]
                             logger.info(f"Found existing Auth ID: {auth_user_id}")
                        else:
                             logger.error("Failed to create user and could not find ID.")
                             continue

                # 3. Update public.users ID to match auth_user_id
                if str(user.id) != str(auth_user_id):
                    logger.info(f"Updating user ID from {user.id} to {auth_user_id}")
                    
                    # Define update logic for dependencies
                    old_id = str(user.id)
                    new_id = str(auth_user_id)
                    
                    # Strategy: Insert NEW user -> Move FKs -> Delete OLD user
                    # This avoids FK violation constraints.
                    
                    # 1. Create new user row in public.users
                    # Check if it exists first (partial migration)
                    existing_new = db.session.execute(text("SELECT id FROM users WHERE id = :new_id"), {'new_id': new_id}).fetchone()
                    if not existing_new:
                        logger.info("Temporarily renaming old user to avoid unique usage...")
                        # We append a modification to the old user so we can insert the new one
                        # and then delete the old one.
                        db.session.execute(text("""
                            UPDATE users 
                            SET email = email || '.migrated', username = username || '_migrated'
                            WHERE id = :old_id
                        """), {'old_id': old_id})
                        
                        logger.info("Creating new public user row...")
                        # Copy attributes from old user (stripping the suffix we just added? No, select original?)
                        # We just modified the DB. So we should have selected BEFORE modifying OR strip suffix.
                        # Easier: Input the values from the `user` object we already loaded!
                        # `user` object in the loop still has the original values in memory (unless we refreshed).
                        
                        db.session.execute(text("""
                            INSERT INTO users (id, username, email, password_hash, created_at, avatar_file)
                            VALUES (:new_id, :username, :email, :password_hash, :created_at, :avatar_file)
                        """), {
                            'new_id': new_id, 
                            'username': user.username, # From memory
                            'email': user.email, # From memory
                            'password_hash': user.password_hash,
                            'created_at': user.created_at,
                            'avatar_file': user.avatar_file
                        })
                    
                    # 2. Update VocabSets (which have FK to users)
                    logger.info("Moving VocabSets...")
                    db.session.execute(text("UPDATE vocab_sets SET user_id = :new_id WHERE user_id = :old_id"), 
                                     {'new_id': new_id, 'old_id': old_id})
                                     
                    # 3. Delete old user
                    # We need to ensure no other FKs are hanging. 
                    # Cards depend on VocabSets, not Users directly.
                    logger.info("Deleting old user row...")
                    db.session.execute(text("DELETE FROM users WHERE id = :old_id"), {'old_id': old_id})
                    
                    db.session.commit()
                    logger.info("ID update successful.")
                        
            except Exception as e:
                logger.error(f"Error migrating user {user.username}: {e}")
                db.session.rollback()
                continue
                
    logger.info("Migration completed.")

if __name__ == "__main__":
    if input("Are you sure you want to run the migration? (yes/no): ") == "yes":
        migrate_users()
