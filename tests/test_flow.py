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
    def test_profile_keeps_password_action_visible_for_google_accounts(self):
        client = self.authenticated_client()
        page = client.get('/auth/profile').get_data(as_text=True)
        self.assertIn('id="change-password-btn" href="/auth/change-password"', page)
        self.assertIn('id="change-password-btn"', page.split('<!-- Danger Zone -->')[1])

        self.user.google_sub = 'test-google-subject'
        db.session.commit()
        page = client.get('/auth/profile').get_data(as_text=True)
        self.assertIn('id="change-password-btn" class="btn-danger-secondary" disabled', page)
        self.assertIn('popovertarget="password-provider-info"', page)
        self.assertIn('id="password-provider-info" class="study-mode-info-panel" popover', page)
        self.assertIn('This account is linked to Google.', page)
        self.assertIn('https://myaccount.google.com/signinoptions/password', page)
        self.assertNotIn('href="/auth/change-password"', page)

    def test_wrong_filter_includes_last_wrong_answer_in_both_modes_and_undo(self):
        from datetime import timedelta
        from app.utils.time import utc_now
        client = self.authenticated_client()
        vocab_set = VocabService.create_user_set(self.user.id, 'Wrong_Filter')
        future = utc_now() + timedelta(days=8)
        card = Card(vocab_set_id=vocab_set.id, front='known', back='answer', level=4,
                    next_review=future, last_practice_wrong=True)
        new_card = Card(vocab_set_id=vocab_set.id, front='new', back='new answer', level=1,
                        next_review=future)
        db.session.add_all([card, new_card])
        db.session.commit()
        url = f'/api/set/{vocab_set.id}'
        self.assertEqual({c['front'] for c in client.get(url + '/cards?wrong_only=true').get_json()['cards']}, {'known', 'new'})
        response = client.post(url + '/rate', json={'card_front': 'known', 'quality': 5})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(card.last_practice_wrong)
        self.assertEqual([c['front'] for c in client.get(url + '/cards?wrong_only=true').get_json()['cards']], ['new'])
        self.assertEqual(client.post('/api/restore_card', json={'set_id': vocab_set.id,
            'card_front': 'known', 'level': 4, 'next_review': future.isoformat(),
            'last_answer_wrong': True}).status_code, 200)
        self.assertTrue(card.last_practice_wrong)
        self.assertEqual(card.level, 4)
        self.assertEqual(card.next_review, future)
        self.assertEqual(client.post(url + '/mark_correct', json={'card_front': 'known'}).status_code, 200)
        self.assertFalse(card.last_practice_wrong)
        self.assertEqual((card.level, card.next_review), (4, future))
        self.assertEqual(client.post(url + '/rate', json={'card_front': 'known', 'quality': 2}).status_code, 200)
        self.assertTrue(card.last_practice_wrong)
        self.assertTrue(card.to_dict()['last_answer_wrong'])

    def test_overview_practice_modes_do_not_change_learning_progress(self):
        from datetime import timedelta
        from app.utils.time import utc_now
        client = self.authenticated_client()
        vocab_set = VocabService.create_user_set(self.user.id, 'Practice_Modes')
        future = utc_now() + timedelta(days=8)
        cards = [Card(vocab_set_id=vocab_set.id, front=front, back='answer', level=level,
                      next_review=future, last_practice_wrong=wrong)
                 for front, level, wrong in [('new', 1, False), ('mistake', 4, True), ('known', 3, False)]]
        db.session.add_all(cards); db.session.commit()
        path = f'/set/{vocab_set.id}'
        overview = client.get(path + '/overview').get_data(as_text=True)
        self.assertIn('mode=practice', overview)
        self.assertIn('mode=mistakes', overview)
        self.assertIn('id="study-mode-picker"', overview)
        self.assertIn('Learn with Flashcards', overview)
        self.assertNotIn('mode=practice', overview.split('<dialog')[0])
        self.assertNotIn('mode=mistakes', overview.split('<dialog')[0])
        for mode in ('learn', 'practice', 'mistakes'):
            page = client.get(path + '?mode=' + mode).get_data(as_text=True)
            self.assertIn(f'data-study-mode="{mode}"', page)
            self.assertIn('aria-label="Change Learning Mode"', page)
            self.assertNotIn('practice-mode-checkbox', page)
            self.assertNotIn('wrong-answers-checkbox', page)
        self.assertIn('data-study-mode="learn"', client.get(path + '?mode=invalid').get_data(as_text=True))
        api = f'/api/set/{vocab_set.id}'
        self.assertEqual([c['front'] for c in client.get(api + '/cards?last_wrong_only=true').get_json()['cards']], ['mistake'])
        baseline = VocabService.get_statistics(vocab_set.id, self.user.id)
        for card in cards:
            state = (card.level, card.next_review)
            for endpoint in ('mark_wrong', 'mark_correct'):
                self.assertEqual(client.post(api + '/' + endpoint, json={'card_front':card.front}).status_code, 200)
                self.assertEqual((card.level, card.next_review), state)
        self.assertEqual(VocabService.get_statistics(vocab_set.id, self.user.id), baseline)
        self.assertEqual(client.get(api + '/cards?last_wrong_only=true').get_json()['cards'], [])

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
        self.assert_default_capitals(user)

    def assert_default_capitals(self, user):
        from app.data.standard_sets import HAUPTSTAEDTE_DATA
        from app.utils.time import utc_now
        sets = VocabSet.query.filter_by(user_id=user.id, name='Hauptstädte', is_shared=False).all()
        self.assertEqual(len(sets), 1)
        self.assertEqual({(card.front, card.back) for card in sets[0].cards},
                         {(item['front'], item['back']) for item in HAUPTSTAEDTE_DATA})
        self.assertTrue(all(card.level == 1 and card.next_review < utc_now()
                            for card in sets[0].cards))
        from app.data.standard_sets import default_vocabularies
        flags = VocabSet.query.filter_by(user_id=user.id, name='Flaggen der Welt', is_shared=False).one()
        self.assertEqual([(card.front, card.back) for card in flags.get_all_cards()],
                         default_vocabularies()['Flaggen der Welt'])

    def test_new_account_gets_capitals_without_database_seed(self):
        for template in VocabSet.query.filter_by(is_shared=True).all():
            db.session.delete(template)
        db.session.commit()
        with patch.object(UserService, 'google_subject', return_value=None):
            user = UserService.resolve_neon_user({'id': str(uuid.uuid4()),
                'email': 'unseeded@example.com', 'name': 'Unseeded'})
        self.assert_default_capitals(user)

    def test_default_assignment_preserves_existing_learning_progress(self):
        UserService.assign_default_vocab_set(self.user.id)
        db.session.commit()
        capitals = VocabSet.query.filter_by(user_id=self.user.id, name='Hauptstädte').one()
        card = capitals.cards[0]
        card.level = 4
        db.session.commit()
        UserService.assign_default_vocab_set(self.user.id)
        db.session.commit()
        self.assertEqual(VocabSet.query.filter_by(user_id=self.user.id, name='Hauptstädte').count(), 1)
        self.assertEqual(db.session.get(Card, card.id).level, 4)

    def test_flags_standard_backfill_is_private_and_preserves_existing_sets(self):
        UserService.assign_default_vocab_set(self.user.id, set_names={'Flaggen der Welt'})
        db.session.commit()
        flags = VocabSet.query.filter_by(user_id=self.user.id, name='Flaggen der Welt').one()
        card = flags.get_all_cards()[0]
        card.level = 4
        card.back = 'Edited answer'
        db.session.commit()
        UserService.assign_default_vocab_set(self.user.id, set_names={'Flaggen der Welt'})
        db.session.commit()
        self.assertEqual(flags.cards.count(), 254)
        self.assertFalse(flags.is_shared)
        self.assertEqual(VocabSet.query.filter_by(user_id=self.user.id, name='Flaggen der Welt').count(), 1)
        self.assertEqual((card.level, card.back), (4, 'Edited answer'))
        self.assertNotIn(flags.id, {v['id'] for v in VocabService.get_all_set_names('other-user')})

    def test_standard_seed_adds_flags_when_capitals_already_exist(self):
        from app.database import create_default_vocab_set
        flags = VocabSet.query.filter_by(name='Flaggen der Welt', is_shared=True).one()
        db.session.delete(flags)
        db.session.commit()
        create_default_vocab_set()
        create_default_vocab_set()
        self.assertEqual(VocabSet.query.filter_by(name='Hauptstädte', is_shared=True).count(), 1)
        flags = VocabSet.query.filter_by(name='Flaggen der Welt', is_shared=True).one()
        self.assertEqual(flags.cards.count(), 254)

    def test_flags_standard_recognizes_existing_underscore_name(self):
        existing = VocabService.create_user_set(self.user.id, 'Flaggen_der_Welt')
        UserService.assign_default_vocab_set(self.user.id, set_names={'Flaggen der Welt'})
        db.session.commit()
        self.assertEqual(VocabSet.query.filter_by(user_id=self.user.id, name='Flaggen der Welt').count(), 0)
        self.assertEqual(db.session.get(VocabSet, existing.id).name, 'Flaggen_der_Welt')

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

    def test_overview_statistics_color_matches_dominant_home_level(self):
        client = self.authenticated_client()
        for levels in ([], [1, 4, 4], [2, 2, 5], [6, 6, 1], [4, 4, 4, 5, 5, 6, 6]):
            with self.subTest(levels=levels):
                vs = VocabService.create_user_set(self.user.id, 'Color_' + uuid.uuid4().hex)
                db.session.add_all([
                    Card(vocab_set_id=vs.id, front=f'word_{index}', back='answer', level=level)
                    for index, level in enumerate(levels)
                ])
                db.session.commit()
                summary = next(item for item in VocabService.get_all_set_names(self.user.id) if item['id'] == vs.id)
                response = client.get(f'/set/{vs.id}/overview')
                self.assertEqual(response.status_code, 200)
                self.assertIn(f'--stats-color: var(--color-accent-{summary["max_level"]})', response.get_data(as_text=True))

    def test_shared_overview_statistics_color_uses_shared_card_levels(self):
        vs = VocabSet(id=str(uuid.uuid4()), name='Shared_Color', is_shared=True)
        db.session.add(vs)
        db.session.flush()
        db.session.add_all([
            Card(vocab_set_id=vs.id, front=f'word_{index}', back='answer', level=level)
            for index, level in enumerate((4, 4, 4, 5, 5, 6, 6))
        ])
        db.session.commit()
        response = self.authenticated_client().get(f'/set/{vs.id}/overview')
        self.assertEqual(response.status_code, 200)
        self.assertIn('--stats-color: var(--color-accent-5)', response.get_data(as_text=True))
        stats = VocabService.get_statistics(vs.id, self.user.id)
        self.assertEqual(stats['level_counts'], {4: 3, 5: 4})
        self.assertEqual(stats['total_cards'], 7)

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

    def test_edit_card_preserves_progress_and_validates_input(self):
        vs = VocabService.create_user_set(self.user.id, 'Edit_Cards')
        card = VocabService.add_card(vs.id, 'old front', 'old back', self.user.id)
        VocabService.add_card(vs.id, 'duplicate', 'another back', self.user.id)
        card.level = 4
        card.last_practice_wrong = True
        card.shuffle_order = 7
        db.session.commit()
        progress = (card.level, card.next_review, card.last_practice_wrong, card.shuffle_order)
        client = self.authenticated_client()
        path = f'/api/set/{vs.id}/card/{card.id}'
        response = client.patch(path, json={'front': ' <b>edited</b> ', 'back': 'first line\nsecond line'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['card']['front'], '<b>edited</b>')
        self.assertEqual(card.back, 'first line\nsecond line')
        self.assertEqual((card.level, card.next_review, card.last_practice_wrong, card.shuffle_order), progress)
        for payload in [{'front': 'duplicate', 'back': 'changed'},
                        {'front': 'valid', 'back': '  '},
                        {'front': 'x' * 256, 'back': 'valid'},
                        {'front': 12, 'back': 'valid'}, []]:
            self.assertEqual(client.patch(path, json=payload).status_code, 400)
            self.assertEqual((card.front, card.back), ('<b>edited</b>', 'first line\nsecond line'))
        other_set = VocabService.create_user_set(self.user.id, 'Other_Cards')
        self.assertEqual(client.patch(f'/api/set/{other_set.id}/card/{card.id}',
                                     json={'front': 'x', 'back': 'y'}).status_code, 404)

    def test_edit_card_requires_ownership(self):
        other_user = self.create_user('cardowner', 'cardowner@example.com')
        other_set = VocabService.create_user_set(other_user.id, 'Private_Edit')
        card = VocabService.add_card(other_set.id, 'front', 'back', other_user.id)
        client = self.authenticated_client()
        path = f'/api/set/{other_set.id}/card/{card.id}'
        self.assertEqual(client.patch(path, json={'front': 'changed', 'back': 'changed'}).status_code, 403)
        self.assertEqual((card.front, card.back), ('front', 'back'))
        shared = VocabSet.query.filter_by(is_shared=True).first()
        shared_card = Card.query.filter_by(vocab_set_id=shared.id).first()
        self.assertEqual(client.patch(f'/api/set/{shared.id}/card/{shared_card.id}',
                                     json={'front': 'changed', 'back': 'changed'}).status_code, 403)

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

    def test_profile_avatar_fallback_and_custom_image(self):
        client = self.authenticated_client()
        response = client.get('/auth/profile')
        self.assertIn('id="avatar-preview-img" src="/static/img/default-avatar.png"', response.get_data(as_text=True))
        self.user.avatar_file = 'https://example.test/custom-avatar.png'
        db.session.commit()
        response = client.get('/auth/profile')
        self.assertIn('id="avatar-preview-img" src="https://example.test/custom-avatar.png"', response.get_data(as_text=True))
        response = client.post('/auth/profile/update', data={
            'username': self.user.username,
            'email': self.user.email,
            'remove_avatar': 'true',
        }, headers={'Accept': 'application/json'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['avatar_url'], '/static/img/default-avatar.png')
        self.assertIsNone(self.user.avatar_file)

    def test_import_errors_redirect_to_local_route_even_with_untrusted_host(self):
        client = self.authenticated_client()
        client.set_cookie('verve_neon.session_token', 'test-managed-session', domain='attacker.example')
        response = client.post('/import', data={}, headers={'Host': 'attacker.example'})
        self.assertEqual(response.headers['Location'], '/import')

    def test_api_errors_do_not_disclose_exception_details(self):
        client = self.authenticated_client()
        with patch.object(VocabService, 'edit_card', side_effect=InvalidInputError('private-field', 'internal-secret')):
            response = client.patch('/api/set/example/card/example', json={'front': 'hello', 'back': 'hallo'})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('internal-secret', response.get_data(as_text=True))
        self.assertNotIn('private-field', response.get_data(as_text=True))
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

    def test_postgres_configuration_selects_installed_driver(self):
        from config import database_uri_with_driver
        from sqlalchemy import create_engine
        from sqlalchemy.pool import NullPool
        for scheme in ('postgres', 'postgresql'):
            uri = database_uri_with_driver(f'{scheme}://user:password@localhost/database')
            engine = create_engine(uri, poolclass=NullPool)
            self.assertEqual(engine.dialect.driver, 'psycopg2')
            engine.dispose()
        self.assertEqual(database_uri_with_driver('sqlite:///:memory:'), 'sqlite:///:memory:')

    def test_oauth_verifier_survives_protected_page_redirect(self):
        from urllib.parse import urlparse, parse_qs
        client = self.app.test_client()
        response = client.get('/?neon_auth_session_verifier=one-time-code&filter=due')
        self.assertEqual(response.status_code, 302)
        callback = urlparse(response.headers['Location'])
        self.assertEqual(callback.path, '/auth/callback')
        self.assertEqual(parse_qs(callback.query), {
            'neon_auth_session_verifier': ['one-time-code'], 'next': ['/?filter=due'],
        })
        response = client.get(response.headers['Location'])
        self.assertEqual(response.status_code, 200)
        self.assertIn('/static/js/neon-auth.js', response.get_data(as_text=True))

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
