"""
Custom exceptions for the Verve application.

This module defines application-specific exceptions for better
error handling and clearer error messages.
"""


class VerveException(Exception):
    """Base exception class for all Verve exceptions."""
    pass


class VocabSetNotFoundError(VerveException):
    """Raised when a requested vocabulary set does not exist."""
    
    def __init__(self, set_name: str):
        self.set_name = set_name
        super().__init__(f"Vocabulary set '{set_name}' not found")


class CardNotFoundError(VerveException):
    """Raised when a requested card does not exist in a set."""
    
    def __init__(self, card_front: str, set_name: str):
        self.card_front = card_front
        self.set_name = set_name
        super().__init__(f"Card '{card_front}' not found in set '{set_name}'")


class InvalidInputError(VerveException):
    """Raised when invalid input is provided."""
    
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Invalid {field}: {message}")


class InvalidQualityScoreError(InvalidInputError):
    """Raised when an invalid quality score is provided."""
    
    def __init__(self, score: int):
        super().__init__("quality score", f"Score must be between 0 and 5, got {score}")


class FileOperationError(VerveException):
    """Raised when a file operation fails."""
    
    def __init__(self, operation: str, file_path: str, reason: str):
        self.operation = operation
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Failed to {operation} '{file_path}': {reason}")


class UnauthorizedAccessError(VerveException):
    """Raised when a user tries to access a resource they don't own."""
    
    def __init__(self, resource_type: str, resource_id: int):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"Unauthorized access to {resource_type} with ID {resource_id}")


class UserAlreadyExistsError(VerveException):
    """Raised when trying to create a user that already exists."""
    
    def __init__(self, field: str, value: str):
        self.field = field
        self.value = value
        super().__init__(f"User with {field} '{value}' already exists")


class InvalidCredentialsError(VerveException):
    """Raised when login credentials are invalid."""
    
    def __init__(self, message=None):
        super().__init__(message or "Invalid username/email or password")

