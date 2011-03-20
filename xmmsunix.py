# XMMS interface

import xmms.control

import mediaplayer


class XMMS(mediaplayer.MediaPlayer):
    
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        mediaplayer.MediaPlayer.__init__(self, loggerFactory, "NQr.XMMS",
                                         noQueue, configParser, defaultPlayer,
                                         safePlayers, trackFactory)

    def getShuffle(self):
        # is_shuffle() returns 0 or 1 instead of True or False.
        return not not xmms.control.is_shuffle()

    def setShuffle(self, status):
        if status != self.getShuffle():
            xmms.control.toggle_shuffle()

    def getPlaylistLength(self):
        return xmms.control.get_playlist_length()

    def _getTrackPathAtPos(self, trackPosition, traceCallback=None,
                           logging=True):
        return xmms.control.get_playlist_file(trackPosition)

    def getCurrentTrackPos(self, traceCallback=None):
        return xmms.control.get_playlist_pos()

    def _addTrack(self, filepath):
        xmms.control.playlist_add([filepath])

    def _insertTrack(self, filepath, pos):
        # XMMS doesn't have an insert, so do this the hard way...
        n = self.getPlaylistLength()
        tracks = [self._getTrackPathAtPos(i) for i in range(0, n)]
        tracks.insert(pos, filepath)
        xmms.control.playlist(tracks, False)

    def playAtPosition(self, pos):
        xmms.control.set_playlist_pos(pos)

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

