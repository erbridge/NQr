# XMMS interface

import xmms.control

from MediaPlayer import MediaPlayer

class XMMS(MediaPlayer):
    def getCurrentTrackPath(self):
        return xmms.control.get_playlist_file(xmms.control.get_playlist_pos())

    def getShuffle(self):
        # is_shuffle() returns 0 or 1 instead of true or false
        return not not xmms.control.is_shuffle()

    def setShuffle(self, status):
        if not status is self.getShuffle():
            xmms.control.toggle_shuffle()

    def getPlaylistLength(self):
        return xmms.control.get_playlist_length()

    def getTrackPathAtPos(self, trackPosition):
        return xmms.control.get_playlist_file(trackPosition)

