## Base class for media players

class MediaPlayer:
    def savePlaylist(self):
        playlist = []
        for trackPosition in range(self.getPlaylistLength()):
            playlist.append(self.getTrackPathAtPos(trackPosition))
        return playlist

    def getCurrentTrackPath(self):
        return self.getTrackPathAtPos(self.getCurrentTrackPos())
