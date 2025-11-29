"""Custom exceptions for TransIt."""


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class APIAuthenticationError(TranslationError):
    """Raised when authentication against the translation API fails."""

    def __init__(self, message: str = "API authentication failed. Check your API key."):
        super().__init__(message)


class CorruptDocumentError(TranslationError):
    """DOCX structure is corrupt."""
    def __init__(self, details: str):
        super().__init__(f"Document structure corrupt: {details}")


class FileIOError(TranslationError):
    """Cannot read/write file."""
    def __init__(self, path: str, operation: str):
        super().__init__(f"Cannot {operation} file: {path}")


class UnsupportedLanguageError(TranslationError):
    """Language not supported."""
    def __init__(self, lang: str):
        super().__init__(f"Language not supported: {lang}")
