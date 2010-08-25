## Base class for media players

class MediaPlayer:
    def savePlaylist(self):
        playlist = []
        for trackPosition in range(self.getPlaylistLength()):
            playlist.append(self.getTrackPathAtPos(trackPosition))
        return playlist

## FIXME: sets currently playing track to first track in the list, but continues
##        to play the old track (fixed with work-around)
    def loadPlaylist(self, playlist):
        currentTrackPath = self.getCurrentTrackPath()
        self.clearPlaylist()
        self.addTrack(currentTrackPath)
        for filepath in playlist:
            self.addTrack(filepath)

    def cropPlaylist(self, number):
        for n in range(number):
            self.deleteTrack(0)

## FIXME: gets confused if the playlist is empty (in winamp): sets currently
##        playing track to first track in the list, but continues to play the
##        old track
    def getCurrentTrackPath(self, warnings=True):
        return self.getTrackPathAtPos(self.getCurrentTrackPos(), warnings)
