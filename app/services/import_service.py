"""
Import Service - Business Logic Layer.

This module provides the business logic for importing vocabulary sets
from external files (CSV, TSV).
"""

import csv
import io
from typing import List, Dict, Tuple
from werkzeug.datastructures import FileStorage

from app.services.vocab_service import VocabService
from app.utils.exceptions import InvalidInputError


class ImportService:
    """Service class for import operations."""
    
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
        
        cards = []
        
        # Split into lines/cards
        # If card_separator is newline, we should handle universal newlines
        if card_separator == '\n':
            rows = content.splitlines()
        else:
            rows = content.split(card_separator)
            
        for row in rows:
            row = row.strip()
            if not row:
                continue
                
            # Split into front/back
            parts = row.split(field_separator)
            
            if len(parts) < 2:
                continue
                
            # Take the first two parts, ignoring extra columns if any
            front = parts[0].strip()
            back = parts[1].strip()
            
            if front and back:
                cards.append((front, back))
                
        if not cards:
            raise InvalidInputError("content", "No valid vocabulary cards found")
            
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
            raise InvalidInputError("file", "Only CSV, TSV and TXT files are supported")
        
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
        except Exception as e:
            raise InvalidInputError("file", f"Error parsing file: {str(e)}")

    @staticmethod
    def import_set(user_id: int, set_name: str, file: FileStorage = None, text_content: str = None, 
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
        if file:
            cards = ImportService.parse_file(file, card_separator, field_separator)
        elif text_content:
            cards = ImportService.parse_content(text_content, card_separator, field_separator)
        else:
            raise InvalidInputError("input", "Either file or text content must be provided")
        
        # Create set
        vocab_set = VocabService.create_user_set(user_id, set_name)
        
        # Add cards to set
        from app.models import Card
        from app.database import db
        
        for front, back in cards:
            card = Card(
                front=front,
                back=back,
                vocab_set_id=vocab_set.id
            )
            db.session.add(card)
            
        db.session.commit()
        
        return vocab_set.id

    @staticmethod
    def import_into_set(user_id: int, set_id: int, file: FileStorage = None, text_content: str = None,
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
        if file:
            cards = ImportService.parse_file(file, card_separator, field_separator)
        elif text_content:
            cards = ImportService.parse_content(text_content, card_separator, field_separator)
        else:
            raise InvalidInputError("input", "Either file or text content must be provided")
        
        # Verify set access
        vocab_set = VocabService.get_vocab_set(set_id, user_id)
        
        # Add cards to set
        from app.models import Card
        from app.database import db
        
        count = 0
        for front, back in cards:
            # Check if card already exists in this set
            existing = vocab_set.find_card(front)
            if not existing:
                card = Card(
                    front=front,
                    back=back,
                    vocab_set_id=vocab_set.id
                )
                db.session.add(card)
                count += 1
            
        db.session.commit()
        
        return count
