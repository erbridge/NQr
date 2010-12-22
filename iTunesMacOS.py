## Mac OS, iTunes interface
##
## FIXME: needs to somehow select the playlist (poss see shuffle stuff for hint) 

from appscript import app, k, mactypes, CommandError
from MediaPlayer import MediaPlayer

class iTunesMacOS(MediaPlayer):
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, playlistName="NQr"):
        MediaPlayer.__init__(self, loggerFactory, "NQr.iTunes", noQueue,
                             configParser, defaultPlayer, safePlayers)
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
            self._iTunes.reveal(self._playlist)
            return True
        except CommandError:
            return False
        
    def launch(self):
        self._logger.debug("Launching iTunes.")
        if self._getRunning() == False:
            self._iTunes.launch()
        else:
            self._logger.info("iTunes is already running.")
            self._iTunes.Focus() # FIXME: does this work?

    def launchBackground(self, debug=True):
        if self._getRunning() == False:
            self._logger.debug("Launching iTunes.")
            self._iTunes.launch()
            while True:
                time.sleep(.25)
                if self._getRunning() == True:
                    self._logger.info("iTunes has been launched.")
                    return
                
    def close(self):
        self._logger.debug("Closing iTunes.")
        if self._getRunning() == True:
            self._iTunes.quit()
            while True:
                time.sleep(.25)
                if self._getRunning() == False:
                    self._logger.info("iTunes has been closed.")
                    return
        else:
            self._logger.debug("iTunes is not running.")
            
    def _addTrack(self, filepath):
        self.launchBackground()
        self._logger.info("Adding \'"+filepath+"\' to playlist.")
        track = self._iTunes.add(
            mactypes.File(filepath).hfspath, to=self._playlist)

    def _insertTrack(self, filepath, position):
        self.launchBackground()
        self._logger.info("Inserting \'"+filepath+"\' into playlist position "\
                          +str(position)+".")
        self._playlist.Insert(filepath, position) # FIXME: doesn't work
        
    def deleteTrack(self, position):
        self.launchBackground()
        self._logger.debug("Deleting track in position "+str(position)\
                           +" from playlist.")
        self._iTunes.delete(self._tracks[position + 1])

    def clearPlaylist(self):
        self.launchBackground()
        self._logger.debug("Clearing playlist.")
        self._playlist.delete(self._tracks)

    def nextTrack(self):
        self.launchBackground()
        self._logger.debug("Moving to next track in playlist.")
        self._iTunes.next_track()

    def pause(self):
        self.launchBackground()
        self._logger.debug("Pausing playback.")
        self._iTunes.playpause()

    def play(self):
        self.launchBackground()
        self._logger.debug("Resuming playback or restarting current track.")
        if self._iTunes.player_state() == k.playing:
            self._iTunes.stop()
        self._iTunes.play()
        
    def playAtPosition(self, position):
        self.launchBackground()
        self._logger.debug("Playing track at position.")
        self._iTunes.play(self._tracks[position + 1])

    def previousTrack(self):
        self.launchBackground()
        self._logger.debug("Moving to previous track in playlist.")
        self._iTunes.previous_track()

    def stop(self):
        self.launchBackground()
        self._logger.debug("Stopping playback.")
        self._iTunes.stop()

    def getShuffle(self):
        self.launchBackground()
        self._logger.debug("Retrieving shuffle status.")
        return self._playlist.shuffle() # FIXME: prob doesn't work

    def setShuffle(self, status):
        self.launchBackground()
        self._logger.debug("Setting shuffle status.")
        if status == True or status == 1:
            self._iTunes.set(self._playlist.shuffle, to=True)
            self._logger.info("Shuffle turned on.")
        if status == False or status == 0:
            self._iTunes.set(self._playlist.shuffle, to=False)
            self._logger.info("Shuffle turned off.")

    def getPlaylistLength(self):
        self.launchBackground()
        self._logger.debug("Retrieving playlist length.")
        return len(self._tracks())

    def getCurrentTrackPos(self):
        self.launchBackground()
        try:
            currentTrack = self._iTunes.current_track()
        except CommandError:
            return None
        for pos in range(self.getPlaylistLength()):
            if currentTrack == self._getTrackAtPos(pos):
                return pos
        return None # track is not in "NQr" playlist
    
    def _getTrackAtPos(self, trackPosition):
        return self._tracks[trackPosition + 1]()
    
    ## poss insecure: should always be checked for trackness
    ## gets track at a playlist position
    ## Has logging option so track monitor can call it without spamming the
    ## debug log.
    def _getTrackPathAtPos(self, trackPosition, logging=True):
        if logging == True:
            self._logger.debug("Retrieving path of track at position "\
                               +str(trackPosition)+".")
        return self._getTrackAtPos(trackPosition).location().path
##        if logging == True:
##            self._logger.debug("Converting path into unicode.")
##        return convertToUnicode(rawPath, self._logger, logging)
