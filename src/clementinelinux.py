# Clementine interface

import mediaplayer


class Clementine(mediaplayer.MprisMediaPlayer):

    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        mediaplayer.MprisMediaPlayer.__init__(
            self, loggerFactory, "NQr.Clementine", noQueue, configParser,
            defaultPlayer, safePlayers, trackFactory,
            "org.mpris.clementine", "clementine")
