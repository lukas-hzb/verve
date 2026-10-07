import unittest
import os
import sys
import re
import uuid
from unittest.mock import Mock, patch
from flask import request, g

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models import User, VocabSet, Card
from app.services import UserService, VocabService
from app.services.import_service import ImportService
from app.utils.exceptions import (
    InvalidInputError,
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
        self.user = self.create_user('testuser', 'test@example.com')
        self.app.config['NEON_AUTH_BASE_URL'] = 'https://auth.example/neondb/auth'
        # Tests hold an app context for DB assertions; emulate fresh request caches.
        @self.app.before_request
        def clear_request_caches():
            for key in ('_login_user', 'neon_identity', 'neon_session_response'):
                g.pop(key, None)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_user(self, username, email):
        user = User(id=str(uuid.uuid4()), neon_auth_id=str(uuid.uuid4()),
                    username=username, email=email)
        db.session.add(user)
        db.session.commit()
        return user

    def authenticated_client(self):
        client = self.app.test_client()
        client.set_cookie('verve_neon.session_token', 'test-managed-session')
        identity = {'id': self.user.neon_auth_id, 'email': self.user.email}
        patcher = patch('app.neon_auth.get_identity', side_effect=lambda:
            identity if request.cookies.get('verve_neon.session_token') else None)
        patcher.start()
        self.addCleanup(patcher.stop)
        return client

    @staticmethod
    def upstream(payload, status=200, cookies=()):
        upstream = Mock()
        upstream.status_code = status
        upstream.ok = status < 400
        upstream.json.return_value = payload
        upstream.raw.headers.getlist.return_value = list(cookies)
        return upstream

    def test_google_migration_preserves_application_id_and_learning_data(self):
        self.user.neon_auth_id = None
        self.user.google_sub = 'original-google-subject'
        db.session.commit()
        vocab_set = VocabService.create_user_set(self.user.id, 'Existing_Set')
        original_id = self.user.id
        identity = {'id': str(uuid.uuid4()), 'email': 'changed@example.com',
                    'emailVerified': True, 'name': 'New Google name'}
        with patch.object(UserService, 'google_subject', return_value=self.user.google_sub):
            resolved = UserService.resolve_neon_user(identity)
        self.assertEqual(resolved.id, original_id)
        self.assertEqual(resolved.username, 'testuser')
        self.assertEqual(resolved.neon_auth_id, identity['id'])
        self.assertEqual(vocab_set.user_id, original_id)
        self.assertEqual(User.query.count(), 1)

    def test_unverified_email_cannot_claim_existing_account(self):
        self.user.neon_auth_id = None
        db.session.commit()
        with patch.object(UserService, 'google_subject', return_value=None):
            with self.assertRaises(InvalidCredentialsError):
                UserService.resolve_neon_user({'id': str(uuid.uuid4()),
                    'email': self.user.email, 'emailVerified': False})
        self.assertIsNone(self.user.neon_auth_id)

    def test_different_google_subject_cannot_claim_existing_account(self):
        self.user.neon_auth_id = None
        self.user.google_sub = 'original'
        db.session.commit()
        with patch.object(UserService, 'google_subject', return_value='different'):
            with self.assertRaises(InvalidCredentialsError):
                UserService.resolve_neon_user({'id': str(uuid.uuid4()),
                    'email': self.user.email, 'emailVerified': True})

    def test_linked_identity_cannot_be_replaced(self):
        self.user.google_sub = 'original'
        db.session.commit()
        with patch.object(UserService, 'google_subject', return_value='original'):
            with self.assertRaises(InvalidCredentialsError):
                UserService.resolve_neon_user({'id': str(uuid.uuid4()),
                    'email': self.user.email, 'emailVerified': True})

    def test_new_neon_identity_gets_unique_username_and_default_cards(self):
        with patch.object(UserService, 'google_subject', return_value=None):
            user = UserService.resolve_neon_user({'id': str(uuid.uuid4()),
                'email': 'new@example.com', 'name': 'testuser', 'emailVerified': True})
        self.assertEqual(user.username, 'testuser_1')
        self.assertIsNone(user.password_hash)
        self.assertTrue(VocabService.get_all_set_names(user.id))

    def test_managed_session_revocation_removes_protected_access(self):
        client = self.app.test_client()
        client.set_cookie('verve_neon.session_token', 'managed-session')
        identity = {'id': self.user.neon_auth_id, 'email': self.user.email}
        with patch('app.neon_auth.auth_request', side_effect=[
            self.upstream({'session': {'id': 'session'}, 'user': identity}),
            self.upstream(None),
        ]):
            self.assertEqual(client.get('/api/user/profile').status_code, 200)
            self.assertEqual(client.get('/api/user/profile').status_code, 401)

    def test_legacy_remember_cookie_does_not_block_managed_login(self):
        client = self.authenticated_client()
        client.set_cookie('remember_token', 'legacy-cookie')
        with client.session_transaction() as old_session:
            old_session['_user_id'] = self.user.id
        response = client.get('/api/user/profile')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any('remember_token=;' in cookie for cookie in response.headers.getlist('Set-Cookie')))

    def test_old_flask_session_and_remember_cookie_do_not_authenticate(self):
        client = self.app.test_client()
        with client.session_transaction() as old_session:
            old_session['_user_id'] = self.user.id
        client.set_cookie('remember_token', 'legacy-cookie')
        self.assertEqual(client.get('/api/user/profile').status_code, 401)

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
        other_user = self.create_user('otheruser', 'other@example.com')

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
        client = self.authenticated_client()
        self.assertEqual(client.get('/auth/logout').status_code, 405)
        with patch('app.neon_auth.auth_request', return_value=self.upstream({'success': True})):
            self.assertEqual(client.post('/auth/logout').status_code, 302)
        self.assertEqual(client.get('/api/user/profile').status_code, 401)
        response = client.get('/auth/login?next=https://attacker.example/phishing')
        self.assertNotIn(b'data-next="https://attacker.example', response.data)

    def test_csrf_protects_neon_login(self):
        self.app.config['WTF_CSRF_ENABLED'] = True
        client = self.app.test_client()
        self.assertEqual(client.post('/auth/neon/sign-in/email', json={}).status_code, 400)
        login_page = client.get('/auth/login')
        csrf_token = re.search(rb'data-csrf="([^"]+)"', login_page.data).group(1).decode()
        upstream = self.upstream({'message': 'Invalid credentials'}, status=401)
        upstream.content = b'{"message":"Invalid credentials"}'
        with patch('app.neon_auth.auth_request', return_value=upstream) as transport:
            response = client.post('/auth/neon/sign-in/email',
                json={'email': 'test@example.com', 'password': 'incorrect'},
                headers={'X-CSRFToken': csrf_token})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()['message'], 'Invalid credentials')
        transport.assert_called_once()

    def test_proxy_preserves_oauth_verifier_and_uses_host_only_cookies(self):
        client = self.app.test_client()
        upstream = self.upstream({}, cookies=[
            '__Secure-neon-auth.session_token=signed-token; Domain=neon.tech; Path=/neondb/auth; Secure; HttpOnly; SameSite=None; Partitioned'
        ])
        upstream.content = b'{}'
        with patch('app.neon_auth.auth_request', return_value=upstream) as transport:
            response = client.get('/auth/neon/get-session?neon_auth_session_verifier=verifier')
        self.assertEqual(transport.call_args.kwargs['params']['neon_auth_session_verifier'], 'verifier')
        cookie = response.headers['Set-Cookie']
        self.assertIn('verve_neon.session_token=signed-token', cookie)
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=Lax', cookie)
        self.assertIn('Path=/', cookie)
        self.assertNotIn('Domain=', cookie)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(client.post('/auth/neon/admin/delete-user').status_code, 404)
        self.assertEqual(client.get('/auth/neon/sign-in/email').status_code, 404)

    def test_neon_transport_never_forwards_application_session_or_credentials(self):
        client = self.app.test_client()
        client.set_cookie('verve_neon.session_token', 'signed-token')
        client.set_cookie('unrelated', 'private-data')
        with self.app.test_request_context('/auth/neon/get-session', headers={
            'Cookie': 'verve_neon.session_token=signed-token; session=flask-secret; unrelated=private-data',
            'Authorization': 'Bearer untrusted',
        }):
            from app.neon_auth import auth_request
            with patch('app.neon_auth.requests.request', return_value=self.upstream({})) as send:
                auth_request('get-session')
        headers = send.call_args.kwargs['headers']
        self.assertEqual(headers['Cookie'], '__Secure-neon-auth.session_token=signed-token')
        self.assertNotIn('Authorization', headers)
        self.assertFalse(send.call_args.kwargs['allow_redirects'])

    def test_account_deletion_rolls_back_when_managed_deletion_fails(self):
        client = self.authenticated_client()
        with patch.object(UserService, 'delete_managed_identity', side_effect=ValueError('Deletion failed')):
            response = client.post('/auth/delete-account')
        self.assertEqual(response.status_code, 302)
        self.assertIsNotNone(db.session.get(User, self.user.id))

    def test_account_deletion_removes_application_data_and_cookies(self):
        client = self.authenticated_client()
        user_id, neon_id = self.user.id, self.user.neon_auth_id
        with patch.object(UserService, 'delete_managed_identity') as delete:
            response = client.post('/auth/delete-account')
        delete.assert_called_once_with(neon_id)
        self.assertEqual(response.headers['Location'], '/auth/login')
        self.assertIsNone(db.session.get(User, user_id))
        self.assertTrue(any('verve_neon.' in value and 'Max-Age=0' in value
                            for value in response.headers.getlist('Set-Cookie')))

    def test_profile_email_cannot_diverge_from_managed_identity(self):
        UserService.update_user_profile(self.user.id, 'updated', 'attacker@example.com')
        self.assertEqual(self.user.email, 'test@example.com')

    def test_import_errors_redirect_to_local_route_even_with_untrusted_host(self):
        client = self.authenticated_client()
        client.set_cookie('verve_neon.session_token', 'test-managed-session', domain='attacker.example')
        response = client.post('/import', data={}, headers={'Host': 'attacker.example'})
        self.assertEqual(response.headers['Location'], '/import')

    def test_api_errors_do_not_disclose_exception_details(self):
        client = self.authenticated_client()
        with patch.object(VocabService, 'add_card', side_effect=InvalidInputError('private-field', 'internal-secret')):
            response = client.post('/set/example/add_card', json={'front': 'hello', 'back': 'hallo'})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('internal-secret', response.get_data(as_text=True))
        with patch.object(VocabService, 'get_all_cards', side_effect=RuntimeError('internal-secret')):
            response = client.get('/api/set/example/cards')
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('internal-secret', response.get_data(as_text=True))

    def test_unverified_legacy_user_can_open_verification_page(self):
        client = self.app.test_client()
        identity = {'id': str(uuid.uuid4()), 'email': self.user.email, 'emailVerified': False}
        with patch('app.neon_auth.get_identity', return_value=identity):
            response = client.get('/auth/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn('verification-form', response.get_data(as_text=True))

    def test_redirect_validation_rejects_browser_url_confusion(self):
        from app.security import is_safe_redirect_target
        with self.app.test_request_context('/'):
            for target in ('https://attacker.example', '//attacker.example', '/\\attacker.example', '/\n/attacker.example'):
                self.assertFalse(is_safe_redirect_target(target))
            self.assertTrue(is_safe_redirect_target('/auth/profile'))

    def test_security_headers_are_present(self):
        response = self.app.test_client().get('/auth/login')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response.headers['X-Frame-Options'], 'DENY')

    def test_json_api_contract_still_supports_the_frontend_flow(self):
        client = self.authenticated_client()

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
