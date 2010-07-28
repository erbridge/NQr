# XMMS interface

import xmms

class XMMS:
    def getCurrentTrackPath(self):
        return xmms.get_playlist_file(xmms.get_playlist_pos())

