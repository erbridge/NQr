## Windows, iTunes interface

import subprocess
import time
import win32com.universal
import win32com.client

from MediaPlayer import MediaPlayer

class iTunesWindows(MediaPlayer):
    def __init__(self, loggerFactory, noQueue, configParser,
                 playlistName="\"NQr\""):
        MediaPlayer.__init__(self, loggerFactory, "NQr.iTunes", noQueue,
                             configParser)
        self._playlistName = playlistName
        self.launchBackground()
    
    def _getRunning(self):
        try:
            self._iTunes = win32com.client.gencache.EnsureDispatch(
                "iTunes.Application")
            self._playlist = self._iTunes.LibrarySource.Playlists.ItemByName(
                self._playlistName)
            return True
        except win32com.universal.com_error as err:
            if str(err) != "(-2147221005, 'Invalid class string', None, None)":
                raise err
            return False
        
    def launch(self):
        self._logger.debug("Launching iTunes.")
        if self._getRunning() == False:
            # FIXME: untested!!
            PIPE = subprocess.PIPE
            subprocess.Popen("start itunes", stdout=PIPE, shell=True)
            # FIXME: poss unnecessary?
            while True:
                time.sleep(.25)
                if self._getRunning() == True:
                    return
        else:
            self._logger.info("iTunes is already running.")
            self._iTunes.Focus() # FIXME: does this work?

    def launchBackground(self, debug=True):
        if self._getRunning() == False:
            self._logger.debug("Launching iTunes.")
            # FIXME: untested!!
            PIPE = subprocess.PIPE
            subprocess.Popen("start itunes", stdout=PIPE, shell=True)
            while True:
                time.sleep(.25)
                if self._getRunning() == True:
                    self._logger.info("iTunes has been launched.")
                    return
                
    def close(self):
        self._logger.debug("Closing iTunes.")
        if self._getRunning() == True:
            self._iTunes.close() # FIXME: does this work?
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
        self._playlist.Enqueue(filepath) # FIXME: prob doesn't work
        
    def _insertTrack(self, filepath, position):
        self.launchBackground()
        self._logger.info("Inserting \'"+filepath+"\' into playlist position "\
                          +str(position)+".")
        self._playlist.Insert(filepath, position) # FIXME: prob doesn't work
            
##    def playTrack(self, filepath):

    def deleteTrack(self, position):
        self.launchBackground()
        self._logger.debug("Deleting track in position "+str(position)\
                           +" from playlist.")
        self._playlist.Delete(position) # FIXME: prob doesn't work

    def clearPlaylist(self):
        self.launchBackground()
        self._logger.debug("Clearing playlist.")
        self._playlist.Clear() # FIXME: prob doesn't work

    def nextTrack(self):
        self.launchBackground()
        self._logger.debug("Moving to next track in playlist.")
        self._iTunes.NextTrack()

    def pause(self):
        self.launchBackground()
        self._logger.debug("Pausing playback.")
        self._iTunes.Pause()

    def play(self):
        self.launchBackground()
        self._logger.debug("Resuming playback or restarting current track.")
        self._iTunes.Play()
        
    def playAtPosition(self, position):
        self.launchBackground()
        self._logger.debug("Playing track at position.")
        self._iTunes.setCurrentTrack(position) # FIXME: prob doesn't work
        self._iTunes.Play()

    def previousTrack(self):
        self.launchBackground()
        self._logger.debug("Moving to previous track in playlist.")
        self._iTunes.PreviousTrack()

    def stop(self):
        self.launchBackground()
        self._logger.debug("Stopping playback.")
        self._iTunes.Stop()

    def getShuffle(self):
        self.launchBackground()
        self._logger.debug("Retrieving shuffle status.")
        return self._iTunes.GetShuffle() # FIXME: prob doesn't work

    def setShuffle(self, status):
        self.launchBackground()
        self._logger.debug("Setting shuffle status.")
        if status == True or status == 1:
            self._iTunes.SetShuffle(1) # FIXME: prob doesn't work
            self._logger.info("Shuffle turned on.")
        if status == False or status == 0:
            self._iTunes.SetShuffle(0) # FIXME: prob doesn't work
            self._logger.info("Shuffle turned off.")

    def getPlaylistLength(self):
        self.launchBackground()
        self._logger.debug("Retrieving playlist length.")
        return self._playlist.GetPlaylistLength() # FIXME: prob doesn't work

    def getCurrentTrackPos(self):
        self.launchBackground()
        currentTrack = self._iTunes.CurrentTrack
        # or:
        # currentTrack = win32com.client.CastTo(self._iTunes.CurrentTrack, 
        #                                       "IITFileOrCDTrack")
        return currentTrack.GetPos() # FIXME: prob doesn't work

    ## poss insecure: should always be checked for trackness
    ## gets track at a playlist position
    ## Has logging option so track monitor can call it without spamming the
    ## debug log.
    def _getTrackPathAtPos(self, trackPosition, logging=True):
        if logging == True:
            self._logger.debug("Retrieving path of track at position "\
                               +str(trackPosition)+".")
        # FIXME: prob doesn't work
        rawPath = self._iTunes.GetPathFromPos(trackPosition)
        if logging == True:
            self._logger.debug("Converting path into unicode.")
        return convertToUnicode(rawPath, self._logger, logging)