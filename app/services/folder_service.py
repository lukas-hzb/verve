"""Owner-scoped folder operations and cross-set study queries."""
from collections import Counter
from sqlalchemy.exc import IntegrityError
from app.database import db
from app.models import Card, VocabSet
from app.models.folder import Folder, FolderSet
from app.services.vocab_service import VocabService
from app.utils.exceptions import InvalidInputError, VocabSetNotFoundError
from app.utils.time import utc_now
from app.utils.validators import validate_set_name


class FolderService:
    @staticmethod
    def get(folder_id, user_id):
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if folder is None:
            raise VocabSetNotFoundError(folder_id)
        return folder

    @staticmethod
    def listing(user_id):
        folders = Folder.query.filter_by(user_id=user_id).order_by(Folder.name, Folder.id).all()
        memberships = dict(db.session.query(FolderSet.set_id, FolderSet.folder_id)
                           .join(Folder).filter(Folder.user_id == user_id).all())
        sets = VocabService.get_all_set_names(user_id)
        result = []
        for folder in folders:
            contents = [item for item in sets if memberships.get(item['id']) == folder.id]
            result.append(dict(id=folder.id, name=folder.name, sets=contents,
                               card_count=sum(item['card_count'] for item in contents),
                               due_count=sum(item['due_count'] for item in contents),
                               color=FolderService.average_set_color(contents)))
        return result, memberships

    @staticmethod
    def average_set_color(sets):
        """Mix each set's displayed level color equally, using the shared CSS palette."""
        if not sets:
            return 'var(--color-primary-muted)'
        counts = Counter(max(1, min(5, item['max_level'])) for item in sets)
        color = None
        total = 0
        for level, count in sorted(counts.items()):
            next_color = f'var(--color-accent-{level})'
            if color is None:
                color = next_color
            else:
                weight = total / (total + count) * 100
                color = f'color-mix(in srgb, {color} {weight:.6f}%, {next_color})'
            total += count
        return color

    @staticmethod
    def save(user_id, name, folder_id=None):
        name = validate_set_name(name)
        folder = FolderService.get(folder_id, user_id) if folder_id else Folder(user_id=user_id)
        duplicate = Folder.query.filter_by(user_id=user_id, name=name).first()
        if duplicate and duplicate.id != folder.id:
            raise InvalidInputError('name', 'Folder already exists')
        folder.name = name
        db.session.add(folder)
        try:
            VocabService._commit()
        except IntegrityError:
            raise InvalidInputError('name', 'Folder already exists') from None
        return folder

    @staticmethod
    def assign(folder_id, set_id, user_id):
        VocabService.get_vocab_set(set_id, user_id, require_owner=True)
        if folder_id:
            FolderService.get(folder_id, user_id)
        membership = db.session.get(FolderSet, set_id)
        if membership:
            db.session.delete(membership)
            db.session.flush()
        if folder_id:
            db.session.add(FolderSet(set_id=set_id, folder_id=folder_id))
        VocabService._commit()

    @staticmethod
    def replace_sets(folder_id, user_id, set_ids, name):
        """Validate the entire selection before changing any membership or name."""
        folder = FolderService.get(folder_id, user_id)
        if (not isinstance(set_ids, list) or not all(isinstance(item, str) for item in set_ids)
                or len(set_ids) != len(set(set_ids))):
            raise InvalidInputError('set_ids', 'A unique list of Set IDs is required')
        name = validate_set_name(name)
        duplicate = Folder.query.filter_by(user_id=user_id, name=name).first()
        if duplicate and duplicate.id != folder.id:
            raise InvalidInputError('name', 'Folder already exists')
        owned_ids = {row.id for row in VocabSet.query.filter(
            VocabSet.user_id == user_id, VocabSet.id.in_(set_ids)).all()}
        if owned_ids != set(set_ids):
            raise InvalidInputError('set_ids', 'Select your own Sets')
        try:
            folder.name = name
            # Remove old contents and move selected sets from any previous folder.
            for membership in FolderSet.query.filter(
                    (FolderSet.folder_id == folder.id) | FolderSet.set_id.in_(set_ids)).all():
                db.session.delete(membership)
            db.session.flush()
            db.session.add_all(FolderSet(set_id=item, folder_id=folder.id) for item in set_ids)
            VocabService._commit()
        except IntegrityError:
            db.session.rollback()
            raise InvalidInputError('set_ids', 'Could not save Folder selection') from None
        return folder

    @staticmethod
    def delete(folder_id, user_id):
        db.session.delete(FolderService.get(folder_id, user_id))
        VocabService._commit()

    @staticmethod
    def cards(folder_id, user_id, mode='learn'):
        FolderService.get(folder_id, user_id)
        query = Card.query.join(VocabSet).join(FolderSet, FolderSet.set_id == VocabSet.id).filter(
            FolderSet.folder_id == folder_id, VocabSet.user_id == user_id)
        if mode == 'learn':
            query = query.filter(Card.next_review <= utc_now())
        elif mode == 'mistakes':
            query = query.filter(Card.last_practice_wrong.is_(True))
        rows = query.add_columns(VocabSet.name, VocabSet.text_alignment).order_by(Card.next_review, Card.id)
        return [dict(card.to_dict(), set_name=name, text_alignment=alignment)
                for card, name, alignment in rows]
