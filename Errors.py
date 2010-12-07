## Errors

class Error(Exception):
    def __init__(self, trace=None):
        Exception.__init__(self)
        self.trace = trace

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