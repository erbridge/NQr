# Audacious interface

import dbus
import os
import time
import urllib
import urlparse

import mediaplayer

class Audacious(mediaplayer.MediaPlayer):
    
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        mediaplayer.MediaPlayer.__init__(self, loggerFactory, "NQr.Audacious",
                                         noQueue, configParser, defaultPlayer,
                                         safePlayers, trackFactory)                
        while True:
            try:
                self._initSetupDbus()
                break
            except dbus.exceptions.DBusException:
                import subprocess
                subprocess.Popen("audacious", close_fds=True)
                time.sleep(.25)
            
    def _initSetupDbus(self):
        self._bus = dbus.SessionBus()
        
        root = self._bus.get_object("org.mpris.audacious", "/")
        player = self._bus.get_object("org.mpris.audacious", "/Player")
        tracklist  = self._bus.get_object("org.mpris.audacious", "/TrackList")
#         print player.Introspect()
        org = self._bus.get_object("org.mpris.audacious",
                                  "/org/atheme/audacious")
        
        self._root = dbus.Interface(root, "org.freedesktop.MediaPlayer")
        self._player = dbus.Interface(player, "org.freedesktop.MediaPlayer")
        self._tracklist = dbus.Interface(tracklist,
                                         "org.freedesktop.MediaPlayer")
        self._org = dbus.Interface(org, "org.atheme.audacious")
        
    def _addTrack(self, path):
        path = "file://" + path
        self._tracklist.AddTrack(path, False)
                
    def _getTrackPathAtPos(self, position, traceCallback=None, logging=True):
        metadata = self._tracklist.GetMetadata(position)
        try:
            parsedPath = urlparse.urlparse(metadata[u"location"])
        except KeyError:
            # FIXME: empty tracklist throws errors
            return None
        return urllib.unquote(os.path.realpath(os.path.join(parsedPath.netloc,
                                                            parsedPath.path)))
        
    def deleteTrack(self, position):
        self._tracklist.DelTrack(position)
        
    def getCurrentTrackPos(self, traceCallback=None):
        return self._tracklist.GetCurrentTrack()
    
    def getPlaylistLength(self):
        return self._tracklist.GetLength()
    
    def getShuffle(self):
        status = self._player.GetStatus()
        return bool(status[1])
    
    def nextTrack(self):
        self._player.Next()
    
    def pause(self):
        self._player.Pause()
    
    def play(self):
        self._player.Play()
        
    def previousTrack(self):
        self._player.Prev()
    
    def setShuffle(self, status):
        self._tracklist.Random(status)
        
    def stop(self):
        self._player.Stop()