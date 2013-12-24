# Windows, iTunes interface

import subprocess
import time
import win32com.universal
import win32com.client

import mediaplayer


class iTunes(mediaplayer.MediaPlayer):

    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory, playlistName="\"NQr\""):
        mediaplayer.MediaPlayer.__init__(self, loggerFactory, "NQr.iTunes",
                                         noQueue, configParser, defaultPlayer,
                                         safePlayers, trackFactory)
        self._playlistName = playlistName
        self.launchBackground()

    def _getRunning(self):
        try:
            self._iTunes = win32com.client.gencache.EnsureDispatch(
                "iTunes.Application")
            try:
                self._playlist = (
                    self._iTunes.LibrarySource.Playlists.ItemByName(
                        self._playlistName))
            except AttributeError as err:
                print err  # FIXME: Find specific error.
                self._playlist = self._iTunes.CreatePlaylist(
                    self._playlistName)
#                self._playlist = win32com.client.CastTo(self._playlist,
#                                                        "IITUserPlaylist")
            self._tracks = self._playlist.Tracks
            return True
        except win32com.universal.com_error as err:
            if str(err) != "(-2147221005, 'Invalid class string', None, None)":
                raise
            return False

    def launch(self):
        self._sendDebug("Launching iTunes.")
        if not self._getRunning():
            # FIXME: Untested!!
            PIPE = subprocess.PIPE
            subprocess.Popen("start itunes", stdout=PIPE, shell=True)
            # FIXME: Possibly unnecessary?
            while True:
                time.sleep(.25)
                if self._getRunning():
                    return
        else:
            self._sendInfo("iTunes is already running.")
            self._iTunes.Focus()  # FIXME: Does this work?

    def launchBackground(self):
        if not self._getRunning():
            self._sendDebug("Launching iTunes.")
            # FIXME: Untested!!
            PIPE = subprocess.PIPE
            subprocess.Popen("start itunes", stdout=PIPE, shell=True)
            while True:
                time.sleep(.25)
                if self._getRunning():
                    self._sendInfo("iTunes has been launched.")
                    return

    def close(self):
        self._sendDebug("Closing iTunes.")
        if self._getRunning():
            self._iTunes.close()  # FIXME: Does this work?
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
        # FIXME: Possibly needs track object.
        self._playlist.AddTrack(filepath)

    def _insertTrack(self, filepath, position):
        self.launchBackground()
        self._sendInfo(
            "Inserting \'" + filepath + "\' into playlist position "
            + str(position) + ".")
        # FIXME: Probably doesn't work.
        self._playlist.Insert(filepath, position)

#    def playTrack(self, filepath):

    def deleteTrack(self, position):
        self.launchBackground()
        self._sendDebug(
            "Deleting track in position " + str(position) + " from playlist.")
        self._playlist.Delete(position)  # FIXME: Probably doesn't work.

    def clearPlaylist(self):
        self.launchBackground()
        self._sendDebug("Clearing playlist.")
        self._playlist.Clear()  # FIXME: Probably doesn't work.

    def nextTrack(self):
        self.launchBackground()
        self._sendDebug("Moving to next track in playlist.")
        self._iTunes.NextTrack()

    def pause(self):
        self.launchBackground()
        self._sendDebug("Pausing playback.")
        self._iTunes.Pause()

    def play(self):
        self.launchBackground()
        self._sendDebug("Resuming playback or restarting current track.")
        self._iTunes.Play()

    def playAtPosition(self, position):
        self.launchBackground()
        self._sendDebug("Playing track at position.")
        self._iTunes.setCurrentTrack(position)  # FIXME: Probably doesn't work.
        self._iTunes.Play()

    def previousTrack(self):
        self.launchBackground()
        self._sendDebug("Moving to previous track in playlist.")
        self._iTunes.PreviousTrack()

    def stop(self):
        self.launchBackground()
        self._sendDebug("Stopping playback.")
        self._iTunes.Stop()

    def getShuffle(self):
        self.launchBackground()
        self._sendDebug("Retrieving shuffle status.")
        return self._iTunes.GetShuffle()  # FIXME: Probably doesn't work.

    def setShuffle(self, status):
        self.launchBackground()
        self._sendDebug("Setting shuffle status.")
        if status:
            self._iTunes.SetShuffle(1)  # FIXME: Probably doesn't work.
            self._sendInfo("Shuffle turned on.")
        else:
            self._iTunes.SetShuffle(0)  # FIXME: Probably doesn't work.
            self._sendInfo("Shuffle turned off.")

    def getPlaylistLength(self):
        self.launchBackground()
        self._sendDebug("Retrieving playlist length.")
        return self._tracks.Count

    def getCurrentTrackPos(self):
        self.launchBackground()
        currentTrack = self._iTunes.CurrentTrack
        # currentTrack = win32com.client.CastTo(self._iTunes.CurrentTrack,
        #                                       "IITFileOrCDTrack")
        for pos in range(self.getPlaylistLength()):
            if currentTrack == self._getTrackAtPos(pos):
                return pos
        return None  # Track is not in "NQr" playlist.

    def _getTrackAtPos(self, trackPosition):
        return self._tracks.Item(trackPosition + 1)

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
        # FIXME: Probably doesn't work.
        rawPath = self._getTrackAtPos(trackPosition).FilePath
        if logging:
            self._sendDebug("Converting path into unicode.")
        return unicode(rawPath, "mcbs")
