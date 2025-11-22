import unittest
import requests
from app import create_app
from app.database import db
from app.models import User, VocabSet, Card

# Assuming the server is running on localhost:8084
BASE_URL = "http://localhost:8084"

class TestLearning(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        import time
        unique_id = int(time.time())
        self.username = f"test_learner_{unique_id}"
        self.password = "password123"
        self.email = f"test_{unique_id}@example.com"
        
        print(f"Registering user: {self.username}")
        
        # Register
        resp = self.session.post(f"{BASE_URL}/auth/register", data={
            "username": self.username,
            "email": self.email,
            "password": self.password,
            "password_confirm": self.password
        })
        if resp.status_code >= 400 or "/register" in resp.url:
            print(f"Register failed: {resp.status_code}")
            print("Register Content:", resp.text[:500])
            
        # Login
        print(f"Logging in user: {self.username}")
        resp = self.session.post(f"{BASE_URL}/auth/login", data={
            "username_or_email": self.username,
            "password": self.password
        })
        print(f"Login Response Status: {resp.status_code}")
        print(f"Login Response URL: {resp.url}")
        if "/login" in resp.url or resp.status_code >= 400:
            print("Login failed!")
            # Extract flash messages
            import re
            alerts = re.findall(r'class="alert alert-([^"]+)">([^<]+)', resp.text)
            print("Flash Messages:", alerts)
            # Also print full text if no alerts found
            if not alerts:
                print("Content:", resp.text[:2000])
        
        # Check if logged in (e.g. access a protected page)
        resp = self.session.get(f"{BASE_URL}/")
        if "/login" in resp.url:
             print("Login check failed (redirected to login)")

    def test_add_card_and_learn(self):
        # Create a set
        response = self.session.post(f"{BASE_URL}/api/vocab_sets", json={"name": "Test_Set"})
        if response.status_code != 201:
            print(f"Create Set failed: {response.status_code} {response.text}")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        set_id = data['id']
        print(f"Testing with Set ID: {set_id}")
        
        # Add Card
        response = self.session.post(f"{BASE_URL}/set/{set_id}/add_card", json={
            "front": "Hello",
            "back": "Hallo"
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Card added successfully", response.text)
        
        # Get Next Card
        response = self.session.get(f"{BASE_URL}/api/set/{set_id}/next_card")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data['card'])
        self.assertEqual(data['card']['front'], "Hello")
        
        # Rate Card
        response = self.session.post(f"{BASE_URL}/api/set/{set_id}/rate", json={
            "card_front": "Hello",
            "quality": 5
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertGreater(data['new_level'], 1)

if __name__ == "__main__":
    unittest.main()
