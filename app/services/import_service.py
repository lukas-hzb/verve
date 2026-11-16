"""
Import Service - Business Logic Layer.

This module provides the business logic for importing vocabulary sets
from external files (CSV, TSV).
"""

import csv
import uuid
from collections import defaultdict
from io import StringIO
from typing import List, NamedTuple, Tuple
from werkzeug.datastructures import FileStorage

from app.database import db
from app.models import Card
from app.services.vocab_service import VocabService
from app.services.verve_format import VerveFormat
from app.utils.time import utc_now
from app.utils.validators import encode_card_line_breaks, validate_card_source
from app.utils.exceptions import InvalidInputError


class ImportResult(NamedTuple):
    added: int
    updated: int
    ambiguous: int


class ImportService:
    """Service class for import operations."""

    @staticmethod
    def _read_cards(file, text_content, card_separator, field_separator, content_format):
        if file and file.filename.lower().endswith('.verve'):
            try:
                return VerveFormat.loads(file.stream.read().decode('utf-8-sig'))
            except UnicodeDecodeError:
                raise InvalidInputError('file', 'File must be UTF-8 encoded') from None
        if file:
            pairs = ImportService.parse_file(file, card_separator, field_separator, content_format=content_format)
        elif text_content:
            pairs = ImportService.parse_content(text_content, card_separator, field_separator,
                                                encode_line_breaks=True, content_format=content_format)
        else:
            raise InvalidInputError('input', 'Either File or Text Content must be provided')
        return [{'front': front, 'back': back, 'front_format': content_format, 'back_format': content_format}
                for front, back in pairs]

    @staticmethod
    def _unique_records(records):
        seen = set()
        result = []
        for record in records:
            if record['front'] not in seen:
                seen.add(record['front'])
                result.append(record)
        return result
    
    @staticmethod
    def parse_content(content: str, card_separator: str = '\n', field_separator: str = '\t', *,
                      encode_line_breaks: bool = False, content_format='plain') -> List[Tuple[str, str]]:
        """
        Parse string content into a list of (front, back) tuples.
        
        Args:
            content: The string content to parse
            card_separator: Separator between cards (default: newline)
            field_separator: Separator between front and back (default: tab)
            encode_line_breaks: Store line endings as card codes for typed input
            
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
        # Textareas submit CRLF, including when a custom separator uses blank lines.
        quoted_rows = card_separator == '\n' and len(field_separator) == 1 and field_separator not in '\r\n"'
        if not quoted_rows and any('\n' in separator and '\r' not in separator
                                   for separator in (card_separator, field_separator)):
            content = content.replace('\r\n', '\n')
        
        # Split into lines/cards
        # If card_separator is newline, we should handle universal newlines
        if quoted_rows:
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
                if content_format == 'plain':
                    row = row.strip()
                if not row.strip():
                    continue
                parts = row.split(field_separator)
            
            if len(parts) < 2:
                continue
                
            # Take the first two parts, ignoring extra columns if any
            front, back = parts[:2]
            if front.strip() and back.strip():
                if encode_line_breaks and content_format == 'plain':
                    front = encode_card_line_breaks(front)
                    back = encode_card_line_breaks(back)
                cards.append((
                    validate_card_source(front, content_format, front=True),
                    validate_card_source(back, content_format),
                ))
                
        if not cards:
            raise InvalidInputError("content", "No valid Vocabulary Cards found")
            
        return cards

    @staticmethod
    def parse_file(file: FileStorage, card_separator: str = None, field_separator: str = None, *,
                   content_format='plain') -> List[Tuple[str, str]]:
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
            
            return ImportService.parse_content(content, card_separator, field_separator, content_format=content_format)
            
        except UnicodeDecodeError:
            raise InvalidInputError("file", "File must be UTF-8 encoded")
        except InvalidInputError:
            raise
        except Exception:
            raise InvalidInputError("file", "The File could not be parsed")

    @staticmethod
    def import_set(user_id: str, set_name: str, file: FileStorage = None, text_content: str = None,
                  card_separator: str = '\n', field_separator: str = '\t', *, content_format='plain') -> int:
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
        cards = ImportService._read_cards(file, text_content, card_separator, field_separator, content_format)
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
        """Import cards and return the number of newly added cards."""
        return ImportService.merge_into_set(
            user_id, set_id, file, text_content, card_separator, field_separator
        ).added

    @staticmethod
    def merge_into_set(
        user_id: str, set_id: str, file: FileStorage = None, text_content: str = None,
        card_separator: str = '\n', field_separator: str = '\t', *, content_format='plain', preview_only=False,
    ) -> ImportResult:
        """Add new fronts and update the back of uniquely matching cards."""
        records = ImportService._read_cards(file, text_content, card_separator, field_separator, content_format)
        typed_import = file is None and bool(text_content)
        new_records = []
        updates = []
        ambiguous = 0
        try:
            vocab_set = VocabService.get_vocab_set(set_id, user_id, require_owner=True, for_update=not preview_only)
            cards_by_front = defaultdict(list)
            cards_by_source = defaultdict(list)
            for card in Card.query.filter_by(vocab_set_id=set_id):
                front = (encode_card_line_breaks(card.front)
                         if typed_import and card.front_format == 'plain' else card.front)
                cards_by_front[(card.front_format, front)].append(card)
                cards_by_source[card.import_key or card.id].append(card)

            existing_targets = set()
            for record in ImportService._unique_records(records):
                source_id = record.get('import_key')
                identity_matches = cards_by_source.get(source_id, [])
                front_matches = cards_by_front[(record['front_format'], record['front'])]
                matches = identity_matches or front_matches
                if not matches:
                    new_records.append(record)
                    continue
                if (len(matches) > 1 or matches[0].id in existing_targets
                        or (identity_matches and any(card.id != matches[0].id for card in front_matches))):
                    ambiguous += 1
                    continue

                card = matches[0]
                existing_targets.add(card.id)
                changes = {key: record[key] for key in ('back', 'back_format')}
                if identity_matches:
                    changes.update(front=record['front'], front_format=record['front_format'])
                elif source_id and not card.import_key and source_id != card.id:
                    changes['import_key'] = source_id
                if any(getattr(card, key) != value for key, value in changes.items()):
                    updates.append((card, changes))

            result = ImportResult(len(new_records), len(updates), ambiguous)
            if preview_only:
                return result
            db.session.add_all(Card(vocab_set_id=set_id, **record) for record in new_records)
            for card, changes in updates:
                for key, value in changes.items():
                    setattr(card, key, value)
            if result.added or result.updated:
                vocab_set.updated_at = utc_now()
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return result

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
