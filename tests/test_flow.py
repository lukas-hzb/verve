import unittest
import os
import sys
import bcrypt
import re

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models import User, VocabSet, Card
from app.services import UserService, VocabService
from app.services.import_service import ImportService
from app.utils.exceptions import (
    InvalidCredentialsError,
    UnauthorizedAccessError,
    UserAlreadyExistsError,
)

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

    def test_user_authentication_rejects_wrong_password(self):
        authenticated = UserService.authenticate_user('test@example.com', 'password123')
        self.assertEqual(authenticated.id, self.user.id)

        with self.assertRaises(InvalidCredentialsError):
            UserService.authenticate_user('test@example.com', 'wrong-password')

    def test_usernames_and_emails_are_case_insensitive(self):
        self.assertEqual(
            UserService.authenticate_user('TESTUSER', 'password123').id,
            self.user.id,
        )
        self.assertEqual(
            UserService.authenticate_user('TEST@EXAMPLE.COM', 'password123').id,
            self.user.id,
        )

        with self.assertRaises(UserAlreadyExistsError):
            UserService.create_user('TESTUSER', 'another@example.com', 'password123')

    def test_imported_bcrypt_password_is_upgraded_after_login(self):
        self.user.password_hash = bcrypt.hashpw(b'password123', bcrypt.gensalt()).decode('utf-8')
        db.session.commit()
        self.assertTrue(self.user.has_legacy_password_hash)

        authenticated = UserService.authenticate_user('testuser', 'password123')

        self.assertFalse(authenticated.has_legacy_password_hash)
        self.assertTrue(authenticated.check_password('password123'))

    def test_password_change_invalidates_old_password(self):
        UserService.change_password(self.user.id, 'password123', 'new-password123')

        with self.assertRaises(InvalidCredentialsError):
            UserService.authenticate_user('testuser', 'password123')

        authenticated = UserService.authenticate_user('testuser', 'new-password123')
        self.assertEqual(authenticated.id, self.user.id)

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

    def test_private_sets_cannot_be_accessed_by_another_user(self):
        vocab_set = VocabService.create_user_set(self.user.id, 'Private_Set')
        other_user = UserService.create_user('otheruser', 'other@example.com', 'password123')

        with self.assertRaises(UnauthorizedAccessError):
            VocabService.get_vocab_set(vocab_set.id, other_user.id)
        with self.assertRaises(UnauthorizedAccessError):
            VocabService.add_card(vocab_set.id, 'front', 'back', other_user.id)

    def test_shared_template_is_read_only_for_regular_users(self):
        shared_set = VocabSet.query.filter_by(is_shared=True).first()
        self.assertIsNotNone(VocabService.get_vocab_set(shared_set.id, self.user.id))

        with self.assertRaises(UnauthorizedAccessError):
            VocabService.add_card(shared_set.id, 'front', 'back', self.user.id)
        with self.assertRaises(UnauthorizedAccessError):
            VocabService.reset_set(shared_set.id, self.user.id)
        with self.assertRaises(UnauthorizedAccessError):
            VocabService.delete_set(shared_set.id, self.user.id)

    def test_import_deduplicates_cards_atomically(self):
        set_id = ImportService.import_set(
            self.user.id,
            'Imported_Set',
            text_content='one\teins\none\tduplicate\ntwo\tzwei',
        )

        cards = Card.query.filter_by(vocab_set_id=set_id).order_by(Card.front).all()
        self.assertEqual([(card.front, card.back) for card in cards], [
            ('one', 'eins'),
            ('two', 'zwei'),
        ])

    def test_login_rejects_external_redirect_and_logout_requires_post(self):
        client = self.app.test_client()
        response = client.post(
            '/auth/login?next=https://attacker.example/phishing',
            data={'username_or_email': 'testuser', 'password': 'password123'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')

        self.assertEqual(client.get('/auth/logout').status_code, 405)
        self.assertEqual(client.post('/auth/logout').status_code, 302)
        api_response = client.get('/api/user/profile')
        self.assertEqual(api_response.status_code, 401)
        self.assertEqual(api_response.get_json()['status'], 'error')

    def test_csrf_protects_login_form(self):
        self.app.config['WTF_CSRF_ENABLED'] = True
        client = self.app.test_client()

        rejected = client.post(
            '/auth/login',
            data={'username_or_email': 'testuser', 'password': 'password123'},
        )
        self.assertEqual(rejected.status_code, 400)

        login_page = client.get('/auth/login')
        token_match = re.search(
            rb'name="csrf_token" value="([^"]+)"',
            login_page.data,
        )
        self.assertIsNotNone(token_match)
        accepted = client.post(
            '/auth/login',
            data={
                'csrf_token': token_match.group(1).decode(),
                'username_or_email': 'testuser',
                'password': 'password123',
            },
        )
        self.assertEqual(accepted.status_code, 302)

    def test_security_headers_are_present(self):
        response = self.app.test_client().get('/auth/login')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')

    def test_json_api_contract_still_supports_the_frontend_flow(self):
        client = self.app.test_client()
        client.post(
            '/auth/login',
            data={'username_or_email': 'testuser', 'password': 'password123'},
        )

        created = client.post('/api/vocab_sets', json={'name': 'API_Set'})
        self.assertEqual(created.status_code, 201)
        created_data = created.get_json()
        self.assertEqual(created_data['status'], 'success')
        set_id = created_data['id']

        added = client.post(
            f'/set/{set_id}/add_card',
            json={'front': 'hello', 'back': 'hallo'},
        )
        self.assertEqual(added.status_code, 200)

        cards = client.get(f'/api/set/{set_id}/cards').get_json()['cards']
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]['front'], 'hello')

        rated = client.post(
            f'/api/set/{set_id}/rate',
            json={'card_front': 'hello', 'quality': 5},
        )
        self.assertEqual(rated.status_code, 200)
        self.assertEqual(rated.get_json()['status'], 'success')

if __name__ == '__main__':
    unittest.main()
