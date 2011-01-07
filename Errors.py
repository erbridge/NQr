## Errors

class Error(Exception):
    def __init__(self, trace=None):
        Exception.__init__(self)
        self._trace = trace
        
    def getTrace(self):
        return self._trace

class EmptyDatabaseError(Error):
    pass

class EmptyQueueError(Error):
    pass

class NoTrackError(Error):
    pass

class UnknownTrackType(Error):
    pass

class NoMetadataError(Error):
    pass

class PathNotFoundError(Error):
    pass

class NoResultError(Error):
    pass

class UnsafeInputError(Error):
    pass

class MultiCompletionPutError(Error):
    pass

class AbortThreadError(Error):
    pass

class BadMessageError(Error):
    pass

class DuplicateTagError(Error):
    pass

class PlayerNotRunningError(Error):
    pass

class NoEventHandlerError(Error):
    pass

class InvalidIDError(Error):
    pass
