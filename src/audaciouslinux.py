# Audacious interface

import mediaplayer


class Audacious(mediaplayer.MprisMediaPlayer):

    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        mediaplayer.MprisMediaPlayer.__init__(
            self, loggerFactory, "NQr.Audacious", noQueue, configParser,
            defaultPlayer, safePlayers, trackFactory, "org.mpris.audacious",
            "audacious")

    def setShuffle(self, status):
        self._tracklist.Random(status)
