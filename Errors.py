## Errors

class EmptyDatabaseError(Exception):
    pass

class NoTrackError(Exception):
    pass
##    def __init__(self):
##        return
##
##    def __str__(self):
##        print "\nNo track has been identified"

class UnknownTrackType(Exception):
    pass

class NoMetadataError(Exception):
    pass
