"""Personal folders group existing sets without copying cards or progress."""
import uuid
from app.database import db


class Folder(db.Model):
    __tablename__ = 'folders'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='uq_folders_user_name'),)
    memberships = db.relationship('FolderSet', cascade='all, delete-orphan', backref='folder')


class FolderSet(db.Model):
    __tablename__ = 'folder_sets'
    set_id = db.Column(db.String(36), db.ForeignKey('vocab_sets.id', ondelete='CASCADE'), primary_key=True)
    folder_id = db.Column(db.String(36), db.ForeignKey('folders.id', ondelete='CASCADE'), nullable=False, index=True)
