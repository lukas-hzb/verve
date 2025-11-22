import unittest
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models import User, VocabSet, Card
from app.services import UserService, VocabService

class VerveTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create a test user
        self.user = UserService.create_user('testuser', 'test@example.com', 'password123')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_user_creation(self):
        u = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(u)
        self.assertTrue(u.check_password('password123'))

    def test_vocab_set_creation(self):
        # Create a set
        vs = VocabService.create_user_set(self.user.id, 'My_Test_Set')
        self.assertIsNotNone(vs)
        self.assertEqual(vs.name, 'My_Test_Set')
        self.assertEqual(vs.user_id, self.user.id)
        
        # Check if it appears in user's sets
        sets = VocabService.get_all_set_names(self.user.id)
        self.assertTrue(any(s['name'] == 'My_Test_Set' for s in sets))

    def test_card_operations(self):
        vs = VocabService.create_user_set(self.user.id, 'Card_Test_Set')
        
        # Add a card manually (since service doesn't have add_card yet, assuming it's done via import or direct DB for now)
        card = Card(vocab_set_id=vs.id, front='Hello', back='Hallo', level=1)
        db.session.add(card)
        db.session.commit()
        
        # Test finding card
        found_card = vs.find_card('Hello')
        self.assertIsNotNone(found_card)
        self.assertEqual(found_card.back, 'Hallo')
        
        # Test update performance
        result = VocabService.update_card_performance(vs.id, 'Hello', 5, self.user.id)
        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['new_level'], 1)

    def test_delete_set(self):
        vs = VocabService.create_user_set(self.user.id, 'Delete_Me')
        set_id = vs.id
        
        VocabService.delete_set(set_id, self.user.id)
        
        with self.assertRaises(Exception): # Should raise VocabSetNotFoundError
            VocabService.get_vocab_set(set_id, self.user.id)

if __name__ == '__main__':
    unittest.main()
