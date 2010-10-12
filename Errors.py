## Errors

class Error(Exception):
    pass

class EmptyDatabaseError(Error):
    pass

class NoTrackError(Error):
    pass
##    def __init__(self):
##        return
##
##    def __str__(self):
##        print "\nNo track has been identified"

class UnknownTrackType(Error):
    pass

class NoMetadataError(Error):
    pass

class PathNotFoundError(Error):
    pass
