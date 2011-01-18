# Mac OS, iTunes interface
#
# FIXME: Needs to somehow select playlist (possibly see shuffle for hint). 

from appscript import app, k, mactypes, CommandError

import mediaplayer


class iTunes(mediaplayer.MediaPlayer):
    
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory, playlistName="NQr"):
        mediaplayer.MediaPlayer.__init__(self, loggerFactory, "NQr.iTunes",
                                         noQueue, configParser, defaultPlayer,
                                         safePlayers, trackFactory)
        self._playlistName = playlistName
        self._iTunes = app("iTunes")
        self.launchBackground()
    
    def _getRunning(self):
        try:
            if not self._iTunes.exists(
                self._iTunes.user_playlists[self._playlistName]):
                    self._playlist = self._iTunes.make(
                        new=k.user_playlist,
                        with_properties={k.name: self._playlistName})
            else:
                self._playlist = self._iTunes.user_playlists[self._playlistName]
            self._tracks = self._playlist.tracks
            return True
        except CommandError:
            return False
        
    def launch(self):
        self._sendDebug("Launching iTunes.")
        if not self._getRunning():
            self._iTunes.launch()
        else:
            self._sendInfo("iTunes is already running.")
            self._iTunes.Focus() # FIXME: Does this work?

    def launchBackground(self):
        if not self._getRunning():
            self._sendDebug("Launching iTunes.")
            self._iTunes.launch()
            while True:
                time.sleep(.25)
                if self._getRunning():
                    self._sendInfo("iTunes has been launched.")
                    self._iTunes.reveal(self._playlist)
                    return
                
    def close(self):
        self._sendDebug("Closing iTunes.")
        if self._getRunning():
            self._iTunes.quit()
            while True:
                time.sleep(.25)
                if not self._getRunning():
                    self._sendInfo("iTunes has been closed.")
                    return
        else:
            self._sendDebug("iTunes is not running.")
            
    def _addTrack(self, filepath):
        self.launchBackground()
        self._sendInfo("Adding \'" + filepath + "\' to playlist.")
        track = self._iTunes.add(
            mactypes.File(filepath).hfspath, to=self._playlist)

    def _insertTrack(self, filepath, position):
        self.launchBackground()
        self._sendInfo(
            "Inserting \'" + filepath + "\' into playlist position "
            + str(position) + ".")
        self._playlist.Insert(filepath, position) # FIXME: Doesn't work.
        
    def deleteTrack(self, position):
        self.launchBackground()
        self._sendDebug(
            "Deleting track in position " + str(position) + " from playlist.")
        self._iTunes.delete(self._tracks[position + 1])

    def clearPlaylist(self):
        self.launchBackground()
        self._sendDebug("Clearing playlist.")
        self._playlist.delete(self._tracks)

    def nextTrack(self):
        self.launchBackground()
        self._sendDebug("Moving to next track in playlist.")
        self._iTunes.next_track()

    def pause(self):
        self.launchBackground()
        self._sendDebug("Pausing playback.")
        self._iTunes.playpause()

    def play(self):
        self.launchBackground()
        self._sendDebug("Resuming playback or restarting current track.")
        if self._iTunes.player_state() is k.playing:
            self._iTunes.stop()
        self._iTunes.play()
        
    def playAtPosition(self, position):
        self.launchBackground()
        self._sendDebug("Playing track at position.")
        self._iTunes.play(self._tracks[position + 1])

    def previousTrack(self):
        self.launchBackground()
        self._sendDebug("Moving to previous track in playlist.")
        self._iTunes.previous_track()

    def stop(self):
        self.launchBackground()
        self._sendDebug("Stopping playback.")
        self._iTunes.stop()

    def getShuffle(self):
        self.launchBackground()
        self._sendDebug("Retrieving shuffle status.")
        return self._playlist.shuffle() # FIXME: Prob doesn't work.

    def setShuffle(self, status):
        self.launchBackground()
        self._sendDebug("Setting shuffle status.")
        if status:
            self._iTunes.set(self._playlist.shuffle, to=True)
            self._sendInfo("Shuffle turned on.")
        if not status:
            self._iTunes.set(self._playlist.shuffle, to=False)
            self._sendInfo("Shuffle turned off.")

    def getPlaylistLength(self):
        self.launchBackground()
        self._sendDebug("Retrieving playlist length.")
        return len(self._tracks())

    def getCurrentTrackPos(self):
        self.launchBackground()
        try:
            currentTrack = self._iTunes.current_track()
        except CommandError:
            return None
        for pos in range(self.getPlaylistLength()):
            if currentTrack is self._getTrackAtPos(pos):
                return pos
        return None # Track is not in "NQr" playlist.
    
    def _getTrackAtPos(self, trackPosition):
        return self._tracks[trackPosition + 1]()
    
    def _getTrackPathAtPos(self, trackPosition, logging=True):
        """
           Gets filename of track at |trackPosition|.
           
           If |logging| is False, the debug log is not updated.
           
           Result should always be turned into a track object.
        """
        if logging:
            self._sendDebug(
                "Retrieving path of track at position " + str(trackPosition)
                + ".")
        return self._getTrackAtPos(trackPosition).location().path
