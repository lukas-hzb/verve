import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.absolute()))

from app import create_app, db
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
                    res = supabase.auth.admin.create_user({
                        "email": user.email,
                        "password": temp_pass,
                        "email_confirm": True,
                        "user_metadata": {"username": user.username}
                    })
                    auth_user_id = res.user.id
                    
                    # 2. Overwrite password hash with old hash using Direct SQL
                    # user.password_hash is the bcrypt string.
                    update_pass_sql = text("""
                        UPDATE auth.users 
                        SET encrypted_password = :hash 
                        WHERE id = :uid
                    """)
                    db.session.execute(update_pass_sql, {'hash': user.password_hash, 'uid': auth_user_id})
                    db.session.commit() # Commit the auth change
                    
                    logger.info(f"User created and password hash synced for {user.email}")

                # 3. Update public.users ID to match auth_user_id
                # This is tricky specifically because of Foreign Keys.
                # If we change the ID of the user, we must update all VocabSets and Cards.
                if str(user.id) != str(auth_user_id):
                    logger.info(f"Updating user ID from {user.id} to {auth_user_id}")
                    
                    # We need to disable FK constraints or update in order? 
                    # Better: Create a new User record with the new ID? 
                    # OR specific SQL Update with CASCADE?
                    # Postgres supports `ON UPDATE CASCADE` if configured.
                    # If not, we do it manually.
                    
                    # Define update logic for dependencies
                    old_id = user.id
                    new_id = auth_user_id
                    
                    # Update related tables
                    # VocabSet
                    db.session.execute(text("UPDATE vocab_sets SET user_id = :new_id WHERE user_id = :old_id"), {'new_id': new_id, 'old_id': old_id})
                    
                    # User table itself? 
                    # We can't update part of the Primary Key easily if it's referenced.
                    # But we can try updating the PK directly if Cascade is on.
                    # If not, the previous command will fail or we do it carefully.
                    
                    # Let's try raw SQL update of the user ID.
                    try:
                        # We might need to handle deferred constraints
                        db.session.execute(text("UPDATE users SET id = :new_id WHERE id = :old_id"), {'new_id': new_id, 'old_id': old_id})
                        db.session.commit()
                        logger.info("ID update successful.")
                    except Exception as e:
                        logger.error(f"Failed to update ID: {e}")
                        db.session.rollback()
                        
            except Exception as e:
                logger.error(f"Error migrating user {user.username}: {e}")
                db.session.rollback()
                continue
                
    logger.info("Migration completed.")

if __name__ == "__main__":
    if input("Are you sure you want to run the migration? (yes/no): ") == "yes":
        migrate_users()
