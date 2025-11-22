import unittest
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.database import db
from app.models import User
from app.services import UserService
from app.utils.exceptions import InvalidCredentialsError, InvalidInputError

class PasswordChangeTestCase(unittest.TestCase):
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

    def test_change_password_success(self):
        # Change password
        UserService.change_password(self.user.id, 'password123', 'newpassword123')
        
        # Verify new password works
        u = User.query.get(self.user.id)
        self.assertTrue(u.check_password('newpassword123'))
        
        # Verify old password fails
        self.assertFalse(u.check_password('password123'))

    def test_change_password_incorrect_current(self):
        # Try to change with wrong current password
        with self.assertRaises(InvalidCredentialsError):
            UserService.change_password(self.user.id, 'wrongpassword', 'newpassword123')
            
        # Verify password hasn't changed
        u = User.query.get(self.user.id)
        self.assertTrue(u.check_password('password123'))

    def test_change_password_invalid_new(self):
        # Try to change to empty password (assuming validation exists)
        with self.assertRaises(InvalidInputError):
            UserService.change_password(self.user.id, 'password123', '')
            
        # Verify password hasn't changed
        u = User.query.get(self.user.id)
        self.assertTrue(u.check_password('password123'))

if __name__ == '__main__':
    unittest.main()
