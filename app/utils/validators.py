"""
Input validation utilities for the Verve application.

This module provides functions to validate user input and prevent
security vulnerabilities like path traversal attacks.
"""

import re
from typing import Optional
from pathlib import Path

from app.utils.exceptions import InvalidInputError, InvalidQualityScoreError


def validate_set_name(set_name: str) -> str:
    """
    Validate a vocabulary set name.
    
    Args:
        set_name: The set name to validate
        
    Returns:
        The validated set name
        
    Raises:
        InvalidInputError: If the set name is invalid
    """
    if not isinstance(set_name, str):
        raise InvalidInputError("set_name", "Set Name must be Text")

    set_name = set_name.strip()
    if not set_name:
        raise InvalidInputError("set_name", "Set Name cannot be empty")

    if len(set_name) > 100:
        raise InvalidInputError("set_name", "Set Name is too long (max 100 Characters)")
    
    # Prevent path traversal attacks
    if ".." in set_name or "/" in set_name or "\\" in set_name:
        raise InvalidInputError("set_name", "Set Name contains illegal Characters")
    
    # Allow alphanumeric characters, Underscores, Hyphens, spaces, and German special characters
    if not re.match(r'^[a-zA-Z0-9_\- äöüÄÖÜß]+$', set_name):
        raise InvalidInputError(
            "set_name", 
            "Set Name must contain only Letters, Numbers, Underscores, Hyphens, Spaces, and German special Characters"
        )
    
    return set_name


def validate_quality_score(quality: int) -> int:
    """
    Validate a quality score for the SM2 algorithm.
    
    Args:
        quality: The quality score (0-5)
        
    Returns:
        The validated quality score
        
    Raises:
        InvalidQualityScoreError: If the score is out of range
    """
    if not isinstance(quality, int):
        try:
            quality = int(quality)
        except (ValueError, TypeError):
            raise InvalidInputError("quality", "Quality must be an integer")
    
    if quality < 0 or quality > 5:
        raise InvalidQualityScoreError(quality)
    
    return quality


def validate_card_front(card_front: str) -> str:
    """
    Validate a card front text.
    
    Args:
        card_front: The card front text to validate
        
    Returns:
        The validated card front text
        
    Raises:
        InvalidInputError: If the card front is invalid
    """
    if not isinstance(card_front, str):
        raise InvalidInputError("card_front", "Card Front must be Text")

    card_front = card_front.strip()
    if not card_front:
        raise InvalidInputError("card_front", "Card Front cannot be empty")

    if len(card_front) > 255:
        raise InvalidInputError("card_front", "Card Front Text is too long (max 255 Characters)")

    return card_front


def validate_card_back(card_back: str) -> str:
    """Validate the answer side of a vocabulary card."""
    if not isinstance(card_back, str):
        raise InvalidInputError("card_back", "Card Back must be Text")

    card_back = card_back.strip()
    if not card_back:
        raise InvalidInputError("card_back", "Card Back cannot be empty")
    if len(card_back) > 10_000:
        raise InvalidInputError("card_back", "Card Back Text is too long (max 10000 Characters)")
    return card_back


def validate_card_level(level: int) -> int:
    """Validate a persisted learning level."""
    try:
        level = int(level)
    except (TypeError, ValueError):
        raise InvalidInputError("level", "Level must be an integer")

    if level < 1 or level > 1000:
        raise InvalidInputError("level", "Level must be between 1 and 1000")
    return level


def sanitize_path(base_dir: Path, filename: str) -> Path:
    """
    Sanitize a file path to prevent path traversal attacks.
    
    Args:
        base_dir: The base directory that the file must be within
        filename: The filename to sanitize
        
    Returns:
        The sanitized absolute path
        
    Raises:
        InvalidInputError: If the path is invalid or outside base_dir
    """
    # Resolve to absolute path
    file_path = (base_dir / filename).resolve()
    
    # Ensure the path is within base_dir
    try:
        file_path.relative_to(base_dir.resolve())
    except ValueError:
        raise InvalidInputError(
            "filename", 
            f"Path traversal detected: {filename} is outside allowed directory"
        )
    
    return file_path


def validate_username(username: str) -> str:
    """
    Validate a username.
    
    Args:
        username: The username to validate
        
    Returns:
        The validated username
        
    Raises:
        InvalidInputError: If the username is invalid
    """
    if not isinstance(username, str):
        raise InvalidInputError("username", "Username must be Text")

    username = username.strip()
    if not username:
        raise InvalidInputError("username", "Username cannot be empty")
    
    if len(username) < 3:
        raise InvalidInputError("username", "Username must be at least 3 Characters long")
    
    if len(username) > 50:
        raise InvalidInputError("username", "Username must be at most 50 Characters long")
    
    # Allow only alphanumeric characters and Underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise InvalidInputError(
            "username",
            "Username must contain only Letters, Numbers, and Underscores"
        )
    
    return username


def validate_email(email: str) -> str:
    """
    Validate an email address.
    
    Args:
        email: The email address to validate
        
    Returns:
        The validated email address
        
    Raises:
        InvalidInputError: If the email is invalid
    """
    if not isinstance(email, str):
        raise InvalidInputError("email", "Email must be Text")

    email = email.strip().lower()
    if not email:
        raise InvalidInputError("email", "Email cannot be empty")
    
    # Basic email validation with regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise InvalidInputError("email", "Invalid Email Address Format")
    
    if len(email) > 120:
        raise InvalidInputError("email", "Email Address is too long (max 120 Characters)")
    
    return email


def validate_set_ownership(user_id: str, vocab_set) -> None:
    """
    Validate that a user owns or has access to a vocabulary set.
    
    Args:
        user_id: The ID of the user
        vocab_set: The VocabSet instance to check
        
    Raises:
        UnauthorizedAccessError: If the user doesn't own the set and it's not shared
    """
    from app.utils.exceptions import UnauthorizedAccessError
    
    # Allow access if the set is shared or if the user owns it
    if not vocab_set.is_shared and vocab_set.user_id != user_id:
        raise UnauthorizedAccessError("vocabulary set", vocab_set.id)
