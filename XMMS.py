# XMMS interface

import xmms.control

class XMMS:
    def getCurrentTrackPath(self):
        return xmms.control.get_playlist_file(xmms.control.get_playlist_pos())

