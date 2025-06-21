"""
Custom exceptions for htty.
"""


class httyError(Exception):
    """Base exception for htty errors."""

    pass


class HTProcessError(httyError):
    """Raised when there's an error with the HTProcess."""

    pass


class HTTimeoutError(httyError):
    """Raised when an operation times out."""

    pass


class HTCommunicationError(httyError):
    """Raised when communication with ht process fails."""

    pass


class HTSnapshotError(httyError):
    """Raised when taking a snapshot fails."""

    pass
