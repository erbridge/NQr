# Errors


class Error(Exception):

    """Base class for errors. A subclass of `Exception`."""

    def __init__(self, trace=None):
        """Extend Exception.__init__() to hold a traceback.
        
        Keyword arguments:
        
        - trace=None: a traceback usually created by `util.getTrace()` or None.
        
        """
        Exception.__init__(self)
        self._trace = trace

    def getTrace(self):
        """Return the traceback associated with the exception."""
        return self._trace


class EmptyDatabaseError(Error):

    """A subclass of `Error` raised on an empty database."""

    pass


class EmptyQueueError(Error):

    """A subclass of `Error` raised on an empty queue."""

    pass


class NoTrackError(Error):

    """A subclass of `Error` raised if no track is available."""

    pass


class UnknownTrackType(Error):

    """A subclass of `Error` raised if a file is of an unsupported type."""

    pass


class NoMetadataError(Error):

    """A subclass of `Error` raised if a file has no accessible metadata."""

    pass


class NoResultError(Error):

    """A subclass of `Error` raised if database operation returns no result."""

    pass


class UnsafeInputError(Error):

    """A subclass of `Error` raised if user input is possibly insecure."""

    pass


class MultiCompletionPutError(Error):

    """A subclass of `Error` raised when trying to fill an argument twice."""

    pass


class AbortThreadSignal(Exception):

    """A subclass of `Exception` raised to signal that a thread should abort."""

    pass


class BadMessageError(Error):

    """A subclass of `Error` raised when an unknown message is received."""

    pass


class DuplicateTagError(Error):

    """A subclass of `Error` raised when a duplicate tag is set."""

    pass


class PlayerNotRunningError(Error):

    """A subclass of `Error` raised when the player is not running."""

    pass


class NoEventHandlerError(Error):

    """A subclass of `Error` raised when the target of a `wx.PostEvent()`
    has been destroyed.
    
    """

    pass


class InvalidIDError(Error):

    """A subclass of `Error` raised when a non-integer trackID is given."""

    pass
