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
    pass

class UnsafeInputError(Error):
    pass
