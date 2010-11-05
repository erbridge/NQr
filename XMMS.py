# XMMS interface

import xmms.control

from MediaPlayer import MediaPlayer

class XMMS(MediaPlayer):
    def __init__(self, loggerFactory, noQueue, configParser):
        MediaPlayer.__init__(self, loggerFactory, "NQr.XMMS", noQueue,
                             configParser)

    def getShuffle(self):
        # is_shuffle() returns 0 or 1 instead of true or false
        return not not xmms.control.is_shuffle()

    def setShuffle(self, status):
        if not status is self.getShuffle():
            xmms.control.toggle_shuffle()

    def getPlaylistLength(self):
        return xmms.control.get_playlist_length()

    def getTrackPathAtPos(self, trackPosition, logging=True):
        return xmms.control.get_playlist_file(trackPosition)

    def getCurrentTrackPos(self):
        return xmms.control.get_playlist_pos()

    def _addTrack(self, filepath):
        xmms.control.playlist_add([filepath])

    def deleteTrack(self, position):
        xmms.control.playlist_delete(position)

    def clearPlaylist(self):
        xmms.control.playlist_clear()

    def play(self):
        xmms.control.play()

    def pause(self):
        xmms.control.pause()

    def nextTrack(self):
        xmms.control.playlist_next()

    def previousTrack(self):
        xmms.control.playlist_prev()

