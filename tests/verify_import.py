import unittest
import sys
import os
from io import BytesIO

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, VocabSet, Card

class TestImportImprovements(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        
        with self.app.app_context():
            db.create_all()
            # Create test user
            user = User(username='testuser', email='test@example.com')
            user.set_password('password')
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def login(self):
        return self.client.post('/auth/login', data={
            'email': 'test@example.com',
            'password': 'password'
        }, follow_redirects=True)

    def test_text_import_custom_separators(self):
        self.login()
        
        # Test data: Semicolon for cards, Pipe for fields
        text_content = "Dog|Hund;Cat|Katze;House|Haus"
        
        response = self.client.post('/import', data={
            'set_name': 'Text Import Set',
            'import_type': 'text',
            'text_content': text_content,
            'card_separator': ';',
            'field_separator': '|'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Set &#39;Text Import Set&#39; erfolgreich importiert!", response.data)
        
        with self.app.app_context():
            vocab_set = VocabSet.query.filter_by(name='Text Import Set').first()
            self.assertIsNotNone(vocab_set)
            self.assertEqual(len(vocab_set.cards), 3)
            
            card1 = Card.query.filter_by(front='Dog', vocab_set_id=vocab_set.id).first()
            self.assertIsNotNone(card1)
            self.assertEqual(card1.back, 'Hund')

    def test_file_import_custom_separators(self):
        self.login()
        
        # Test data: Newline for cards, Comma for fields
        content = "Dog,Hund\nCat,Katze"
        file = (BytesIO(content.encode('utf-8')), 'test.txt')
        
        response = self.client.post('/import', data={
            'set_name': 'File Import Set',
            'import_type': 'file',
            'file': file,
            'card_separator': '\\n',
            'field_separator': ','
        }, content_type='multipart/form-data', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Set &#39;File Import Set&#39; erfolgreich importiert!", response.data)
        
        with self.app.app_context():
            vocab_set = VocabSet.query.filter_by(name='File Import Set').first()
            self.assertIsNotNone(vocab_set)
            self.assertEqual(len(vocab_set.cards), 2)

    def test_import_into_existing_set(self):
        self.login()
        
        # Create initial set
        with self.app.app_context():
            vocab_set = VocabSet(name='Existing Set', user_id=self.user_id)
            db.session.add(vocab_set)
            db.session.commit()
            set_id = vocab_set.id
            
        # Import text into existing set
        text_content = "Bird-Vogel"
        
        response = self.client.post(f'/set/{set_id}/import', data={
            'import_type': 'text',
            'text_content': text_content,
            'card_separator': '\\n',
            'field_separator': '-'  # Custom separator
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        
        with self.app.app_context():
            vocab_set = VocabSet.query.get(set_id)
            self.assertEqual(len(vocab_set.cards), 1)
            self.assertEqual(vocab_set.cards[0].front, 'Bird')
            self.assertEqual(vocab_set.cards[0].back, 'Vogel')

if __name__ == '__main__':
    unittest.main()
