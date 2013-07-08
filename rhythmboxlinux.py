# Rhythmbox interface

import dbus

import mediaplayer
import util

class Rhythmbox(mediaplayer.MediaPlayer):
    
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        mediaplayer.MediaPlayer.__init__(self, loggerFactory, "NQr.Rhythmbox",
                                         noQueue, configParser, defaultPlayer,
                                         safePlayers, trackFactory)
        self._playerPath = "org.mpris.MediaPlayer2.Player"
        bus = dbus.SessionBus()
        rhythmbox = bus.get_object("org.gnome.Rhythmbox3",
                                   "/org/mpris/MediaPlayer2")
        self._player = dbus.Interface(rhythmbox, self._playerPath)
        self._playerProperties = dbus.Interface(
            rhythmbox, "org.freedesktop.DBus.Properties")
        
    def _get(self, *cmds):
        return self._playerProperties.Get(self._playerPath, *cmds)
    
    def _set(self, *cmds):
        self._playerProperties.Set(self._playerPath, *cmds)
    
    def getShuffle(self):
        return self._get("Shuffle")
    
    def setShuffle(self, status):
        self._set("Shuffle", status)