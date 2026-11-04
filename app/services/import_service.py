"""
Import Service - Business Logic Layer.

This module provides the business logic for importing vocabulary sets
from external files (CSV, TSV).
"""

import csv
import uuid
from io import StringIO
from typing import List, Tuple
from werkzeug.datastructures import FileStorage

from app.database import db
from app.models import Card
from app.services.vocab_service import VocabService
from app.services.verve_format import VerveFormat
from app.utils.time import utc_now
from app.utils.validators import validate_card_back, validate_card_front
from app.utils.exceptions import InvalidInputError


class ImportService:
    """Service class for import operations."""

    @staticmethod
    def _read_cards(file, text_content, card_separator, field_separator):
        if file and file.filename.lower().endswith('.verve'):
            try:
                return VerveFormat.loads(file.stream.read().decode('utf-8-sig'))
            except UnicodeDecodeError:
                raise InvalidInputError('file', 'File must be UTF-8 encoded') from None
        if file:
            pairs = ImportService.parse_file(file, card_separator, field_separator)
        elif text_content:
            pairs = ImportService.parse_content(text_content, card_separator, field_separator)
        else:
            raise InvalidInputError('input', 'Either File or Text Content must be provided')
        return [{'front': front, 'back': back} for front, back in pairs]

    @staticmethod
    def _unique_records(records, existing_fronts=()):
        seen = set(existing_fronts)
        result = []
        for record in records:
            if record['front'] not in seen:
                seen.add(record['front'])
                result.append(record)
        return result
    
    @staticmethod
    def parse_content(content: str, card_separator: str = '\n', field_separator: str = '\t') -> List[Tuple[str, str]]:
        """
        Parse string content into a list of (front, back) tuples.
        
        Args:
            content: The string content to parse
            card_separator: Separator between cards (default: newline)
            field_separator: Separator between front and back (default: tab)
            
        Returns:
            List of (front, back) tuples
            
        Raises:
            InvalidInputError: If content is malformed
        """
        # Handle escaped characters in separators
        card_separator = card_separator.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        field_separator = field_separator.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
        
        content = content.lstrip('\ufeff')
        cards = []
        
        # Split into lines/cards
        # If card_separator is newline, we should handle universal newlines
        if card_separator == '\n' and len(field_separator) == 1 and field_separator not in '\r\n"':
            # Respect quoted separators, doubled quotes and multiline fields in exports.
            rows = csv.reader(StringIO(content, newline=''), delimiter=field_separator)
        elif card_separator == '\n':
            rows = content.splitlines()
        else:
            rows = content.split(card_separator)
            
        for row in rows:
            if isinstance(row, list):
                parts = row
            else:
                row = row.strip()
                if not row:
                    continue
                parts = row.split(field_separator)
            
            if len(parts) < 2:
                continue
                
            # Take the first two parts, ignoring extra columns if any
            front = parts[0].strip()
            back = parts[1].strip()
            
            if front and back:
                cards.append((validate_card_front(front), validate_card_back(back)))
                
        if not cards:
            raise InvalidInputError("content", "No valid Vocabulary Cards found")
            
        return cards

    @staticmethod
    def parse_file(file: FileStorage, card_separator: str = None, field_separator: str = None) -> List[Tuple[str, str]]:
        """
        Parse an uploaded file into a list of (front, back) tuples.
        
        Args:
            file: The uploaded file object
            card_separator: Optional custom card separator
            field_separator: Optional custom field separator
            
        Returns:
            List of (front, back) tuples
        """
        filename = file.filename.lower()
        
        if not (filename.endswith('.csv') or filename.endswith('.tsv') or filename.endswith('.txt')):
            raise InvalidInputError("file", "Only CSV, TSV and TXT Files are supported")
        
        try:
            # Read file content
            content_bytes = file.stream.read()
            content = content_bytes.decode("UTF-8")
            
            # Determine defaults if not provided
            if not card_separator:
                card_separator = '\n'
                
            if not field_separator:
                if filename.endswith('.csv'):
                    field_separator = ','
                else:
                    field_separator = '\t'
            
            return ImportService.parse_content(content, card_separator, field_separator)
            
        except UnicodeDecodeError:
            raise InvalidInputError("file", "File must be UTF-8 encoded")
        except InvalidInputError:
            raise
        except Exception:
            raise InvalidInputError("file", "The File could not be parsed")

    @staticmethod
    def import_set(user_id: str, set_name: str, file: FileStorage = None, text_content: str = None,
                  card_separator: str = '\n', field_separator: str = '\t') -> int:
        """
        Import a vocabulary set from a file or text content.
        
        Args:
            user_id: ID of the user
            set_name: Name for the new set
            file: The uploaded file (optional)
            text_content: Direct text input (optional)
            card_separator: Separator between cards
            field_separator: Separator between front and back
            
        Returns:
            ID of the created set
        """
        cards = ImportService._read_cards(file, text_content, card_separator, field_separator)
        unique_cards = ImportService._unique_records(cards)

        try:
            vocab_set = VocabService.create_user_set(user_id, set_name, commit=False)
            db.session.add_all([
                Card(
                    id=str(uuid.uuid4()),
                    **record,
                    vocab_set_id=vocab_set.id,
                )
                for record in unique_cards
            ])
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return vocab_set.id

    @staticmethod
    def import_into_set(user_id: str, set_id: str, file: FileStorage = None, text_content: str = None,
                       card_separator: str = '\n', field_separator: str = '\t') -> int:
        """
        Import vocabulary cards into an existing set.
        
        Args:
            user_id: ID of the user
            set_id: ID of the existing set
            file: The uploaded file (optional)
            text_content: Direct text input (optional)
            card_separator: Separator between cards
            field_separator: Separator between front and back
            
        Returns:
            Number of cards added
        """
        cards = ImportService._read_cards(file, text_content, card_separator, field_separator)
        
        # Verify set access
        vocab_set = VocabService.get_vocab_set(set_id, user_id, require_owner=True)

        # Get existing fronts to check for duplicates
        existing_fronts = {
            front for (front,) in db.session.query(Card.front).filter_by(vocab_set_id=vocab_set.id).all()
        }

        # Filter out duplicates first
        new_cards = ImportService._unique_records(cards, existing_fronts)

        card_objects = [
            Card(
                id=str(uuid.uuid4()),
                **record,
                vocab_set_id=vocab_set.id,
            )
            for record in new_cards
        ]
        try:
            db.session.add_all(card_objects)
            vocab_set.updated_at = utc_now()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return len(card_objects)

    @staticmethod
    def _deduplicate(cards) -> List[Tuple[str, str]]:
        """Keep the first occurrence of each card front while preserving order."""
        unique_cards = []
        seen_fronts = set()
        for front, back in cards:
            if front in seen_fronts:
                continue
            seen_fronts.add(front)
            unique_cards.append((front, back))
        return unique_cards
