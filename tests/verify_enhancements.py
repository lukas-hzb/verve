
import unittest
import requests
from app import create_app
from app.database import db
from app.models import User, VocabSet, Card
from app.services import VocabService
from config import Config

class TestEnhancements(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create test user
        self.username = "test_enhancer"
        self.password = "password123"
        self.email = "enhancer@test.com"
        
        user = User.query.filter_by(username=self.username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            
        user = User(username=self.username, email=self.email)
        user.set_password(self.password)
        db.session.add(user)
        db.session.commit()
        self.user_id = user.id
        
        # Login
        self.session = requests.Session()
        # We'll use the test client for requests to avoid running a server
        
    def tearDown(self):
        user = User.query.get(self.user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
        self.app_context.pop()

    def test_import_and_delete_card(self):
        # Create a set
        vocab_set = VocabSet(name="Enhancement_Test_Set", user_id=self.user_id)
        db.session.add(vocab_set)
        db.session.commit()
        set_id = vocab_set.id
        
        # Login via client
        print(f"Attempting login with {self.email} / {self.password}")
        response = self.client.post('/auth/login', data={
            'username_or_email': self.email,
            'password': self.password
        }, follow_redirects=True)
        print(f"Login response status: {response.status_code}")
        if b'Bitte melden Sie sich an' in response.data:
             print("Login failed: Redirected to login page")
        else:
             print("Login successful")
        
        # Test Import
        import io
        data = {
            'file': (io.BytesIO(b'Hello,Hallo\nWorld,Welt'), 'import.csv')
        }
        response = self.client.post(f'/set/{set_id}/import', data=data, follow_redirects=True)
        # Verify cards in DB
        # Re-fetch set to get updated cards
        db.session.expire_all()
        cards = VocabService.get_all_cards(set_id, self.user_id)
        if len(cards) == 0:
            print("DEBUG: No cards found. Response data:")
            print(response.data.decode('utf-8'))
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]['front'], 'Hello')
        # Verify card count in DB
        # We need to get the set again to see updated card count
        s = VocabSet.query.get(set_id)
        # We expect 2 cards to be added
        self.assertEqual(len(s.cards), 2)
        
        # Test Set Renaming
        print("Testing set renaming...")
        response = self.client.post(f'/set/{set_id}/rename', data={
            'new_name': 'Renamed Set'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 200)
        # The flash message might be different or the page content might be different.
        # Let's just check if we are redirected to the set page and the title is updated.
        self.assertIn(b'Renamed Set', response.data)
        
        s = VocabSet.query.get(set_id)
        self.assertEqual(s.name, 'Renamed Set')
        
        # Test Profile Update
        print("Testing profile update...")
        response = self.client.post('/auth/profile/update', data={
            'username': 'updated_user',
            'email': 'updated@test.com'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Profil erfolgreich aktualisiert', response.data)
        
        u = User.query.get(self.user_id)
        self.assertEqual(u.username, 'updated_user')
        self.assertEqual(u.email, 'updated@test.com')

        # Test Delete Card
        # Get a card ID
        card = s.cards[0]
        print(f"Testing delete card {card.id}...")
        response = self.client.delete(f'/api/set/{set_id}/card/{card.id}')
        self.assertEqual(response.status_code, 200)
        
        # Verify card is gone
        db.session.expire_all()
        s = VocabSet.query.get(set_id)
        self.assertEqual(len(s.cards), 1)

    def test_avatar_upload(self):
        # Login first
        self.client.post('/auth/login', data={
            'username_or_email': 'enhancer@test.com',
            'password': 'password123'
        }, follow_redirects=True)
        
        # Create a dummy image
        import io
        img_content = b'fakeimagecontent'
        data = {
            'username': 'enhancer_avatar',
            'email': 'enhancer@test.com',
            'avatar': (io.BytesIO(img_content), 'avatar.jpg')
        }
        
        response = self.client.post('/auth/profile/update', data=data, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Profil erfolgreich aktualisiert', response.data)
        
        u = User.query.get(self.user_id)
        self.assertIsNotNone(u.avatar_file)
        self.assertTrue(u.avatar_file.endswith('.jpg'))       
    def test_delete_shared_set_as_other_user(self):
        # Create a shared set owned by someone else (or no one)
        shared_set = VocabSet(name="Shared_Test_Set", is_shared=True, user_id=None)
        db.session.add(shared_set)
        db.session.commit()
        set_id = shared_set.id
        
        # Login
        self.client.post('/auth/login', data={
            'username_or_email': self.email,
            'password': self.password
        }, follow_redirects=True)
        
        # Try to delete
        response = self.client.post(f'/set/{set_id}/delete', follow_redirects=True)
        self.assertIn(b'Set successfully deleted', response.data)
        
        # Verify gone
        db.session.expire_all()
        s = VocabSet.query.get(set_id)
        self.assertIsNone(s)

    def test_create_set_with_special_chars(self):
        """Test creating a set with German special characters."""
        # Login
        self.client.post('/auth/login', data={
            'username_or_email': self.email,
            'password': self.password
        }, follow_redirects=True)
        
        # Create set with umlauts
        set_name = "München_Groß"
        response = self.client.post('/api/vocab_sets', json={'name': set_name}, follow_redirects=True)
        
        # Check if created in DB
        vocab_set = VocabSet.query.filter_by(name=set_name).first()
        self.assertIsNotNone(vocab_set)
        self.assertEqual(vocab_set.name, set_name)

if __name__ == '__main__':
    unittest.main()
