## Base class for media players

class MediaPlayer:
    def savePlaylist(self):
        playlist = []
        for trackPosition in range(self.getPlaylistLength()):
            playlist.append(self.getTrackPathAtPos(trackPosition))
        return playlist

## FIXME: sets currently playing track to first track in the list, but continues
##        to play the old track
    def loadPlaylist(self, playlist):
        self.clearPlaylist()
        for filepath in playlist:
            self.addTrack(filepath)

    def getCurrentTrackPath(self):
        return self.getTrackPathAtPos(self.getCurrentTrackPos())
