class LogForgeError(Exception):
    """Base exception for LogForge."""


class StorageError(LogForgeError):
    """Storage-related failure."""


class CorruptionError(StorageError):
    """Stored data is corrupted."""


class InvalidRecord(LogForgeError):
    """A record cannot be stored or processed."""


class QueryError(LogForgeError):
    """Invalid query."""


class ParseError(LogForgeError):
    """Input parsing failure."""