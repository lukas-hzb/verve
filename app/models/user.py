import uuid

import bcrypt
from flask_login import UserMixin
from sqlalchemy import Index, func
from werkzeug.security import check_password_hash, generate_password_hash

from app.database import db
from app.utils.time import utc_now


_DUMMY_PASSWORD_HASH = generate_password_hash(
    uuid.uuid4().hex,
    method='scrypt:32768:8:1',
)

class User(UserMixin, db.Model):
    """User model for authentication."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utc_now)
    avatar_file = db.Column(db.Text, nullable=True) # Store as Base64 string for now to match previous logic

    __table_args__ = (
        Index('uq_users_username_lower', func.lower(username), unique=True),
        Index('uq_users_email_lower', func.lower(email), unique=True),
    )

    # Relationships
    sets = db.relationship('VocabSet', backref='owner', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        """Store a modern, salted scrypt password hash."""
        self.password_hash = generate_password_hash(
            password,
            method='scrypt:32768:8:1',
        )

    def check_password(self, password: str) -> bool:
        """Verify modern hashes and legacy bcrypt hashes imported from Supabase."""
        if not self.password_hash:
            return False

        try:
            if self.has_legacy_password_hash:
                return bcrypt.checkpw(
                    password.encode('utf-8'),
                    self.password_hash.encode('utf-8'),
                )
            return check_password_hash(self.password_hash, password)
        except (TypeError, ValueError):
            return False

    @staticmethod
    def check_dummy_password(password: str) -> None:
        """Consume the normal password-check cost for unknown accounts."""
        check_password_hash(_DUMMY_PASSWORD_HASH, password)

    @property
    def has_legacy_password_hash(self) -> bool:
        return bool(self.password_hash and self.password_hash.startswith(('$2a$', '$2b$', '$2y$')))

    def __repr__(self):
        return f'<User {self.username}>'
