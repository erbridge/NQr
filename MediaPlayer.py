## Base class for media players

class MediaPlayer:
    def __init__(self, loggerFactory, name, noQueue):
        self._logger = loggerFactory.getLogger(name, "debug")
        self._noQueue = noQueue

    def savePlaylist(self):
        self._logger.debug("Storing current playlist.")
        playlist = []
        for trackPosition in range(self.getPlaylistLength()):
            playlist.append(self.getTrackPathAtPos(trackPosition))
        return playlist

## FIXME: sets currently playing track to first track in the list, but continues
##        to play the old track (fixed with work-around)
    def loadPlaylist(self, playlist):
        self._logger.debug("Restoring playlist.")
        currentTrackPath = self.getCurrentTrackPath()
        self.clearPlaylist()
        self.addTrack(currentTrackPath)
        for filepath in playlist:
            self.addTrack(filepath)

    def cropPlaylist(self, number):
        if number == 1:
            self._logger.debug("Cropping playlist by "+str(number)+" track.")
        else:
            self._logger.debug("Cropping playlist by "+str(number)+" tracks.")
        for n in range(number):
            self.deleteTrack(0)

## FIXME: gets confused if the playlist is empty (in winamp): sets currently
##        playing track to first track in the list, but continues to play the
##        old track
    def getCurrentTrackPath(self, logging=True):
        return self.getTrackPathAtPos(self.getCurrentTrackPos(), logging)

    def getUnplayedTrackIDs(self, db):
        ids = []
        for pos in range(self.getCurrentTrackPos(), self.getPlaylistLength()):
            path = self.getTrackPathAtPos(pos)
            id = db.maybeGetIDFromPath(path)
            # The track may be one we don't know added directly to the player
            if id is not None:
                ids.append(id)
            else:
                self._logger.info("Skipping unknown unplayed track " + path)
        return ids

    def addTrack(self, filepath):
        if self._noQueue:
            print "Not queueing", filepath
            return
        self._addTrack(filepath)
