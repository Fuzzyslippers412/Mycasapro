"""SecondBrain Exceptions"""


class SecondBrainError(Exception):
    """Base exception for SecondBrain operations"""


class ValidationError(SecondBrainError):
    """Raised when note payload fails validation"""


class PermissionError(SecondBrainError):
    """Raised when agent lacks permission for operation"""


class NoteNotFoundError(SecondBrainError):
    """Raised when referenced note doesn't exist"""


class IndexError(SecondBrainError):
    """Raised when ENSUE indexing fails"""
