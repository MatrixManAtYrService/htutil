"""
Custom exceptions for htutil.
"""


class HTUtilError(Exception):
    """Base exception for htutil errors."""

    pass


class HTProcessError(HTUtilError):
    """Raised when there's an error with the HTProcess."""

    pass


class HTTimeoutError(HTUtilError):
    """Raised when an operation times out."""

    pass


class HTCommunicationError(HTUtilError):
    """Raised when communication with ht process fails."""

    pass


class HTSnapshotError(HTUtilError):
    """Raised when taking a snapshot fails."""

    pass
