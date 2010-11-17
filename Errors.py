## Errors

class Error(Exception):
    pass

class EmptyDatabaseError(Error):
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
    def __init__(self, trace=None):
        Error.__init__(self)
        self.trace = trace

class UnsafeInputError(Error):
    pass
