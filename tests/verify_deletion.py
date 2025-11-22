import unittest
import requests
from app import create_app
from app.database import db
from app.models import User, VocabSet

# Assuming the server is running on localhost:8084
BASE_URL = "http://localhost:8084"

class TestDeletion(unittest.TestCase):
    def setUp(self):
        self.app = create_app('development')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        self.session = requests.Session()
        import time
        unique_id = int(time.time())
        self.username = f"test_deleter_{unique_id}"
        self.password = "password123"
        self.email = f"test_del_{unique_id}@example.com"
        
        # Register
        self.session.post(f"{BASE_URL}/auth/register", data={
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "password_confirm": self.password
        })
            
        # Login
        self.session.post(f"{BASE_URL}/auth/login", data={
            "username_or_email": self.username,
            "password": self.password
        })

    def tearDown(self):
        self.app_context.pop()

    def test_delete_shared_set(self):
        # Create a shared set directly in DB
        set_name = f"Shared_Example_{self.username}" # unique name
        shared_set = VocabSet(name=set_name, is_shared=True)
        db.session.add(shared_set)
        db.session.commit()
        set_id = shared_set.id
        print(f"Created shared set {set_id}: {set_name}")
        
        # Verify it exists via API
        response = self.session.get(f"{BASE_URL}/")
        self.assertIn(f"/set/{set_id}", response.text)
        
        # Delete it
        print(f"Deleting set {set_id}...")
        response = self.session.post(f"{BASE_URL}/set/{set_id}/delete")
        
        # Check if redirected (success usually redirects to index)
        self.assertEqual(response.status_code, 200) # requests follows redirects and returns 200 OK from index
        self.assertIn("Set successfully deleted", response.text)
        
        # Verify it's gone from DB
        db.session.expire_all()
        deleted_set = VocabSet.query.get(set_id)
        self.assertIsNone(deleted_set)
        print("Set successfully deleted from DB")

if __name__ == "__main__":
    unittest.main()
