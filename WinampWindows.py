## Windows, Winamp interface
##
## Tested on Winamp 5+

import ctypes
from Errors import NoTrackError, PlayerNotRunningError
from MediaPlayer import MediaPlayer
import subprocess
import time
from Util import convertToUnicode
import win32api
import win32con
import win32process
import winamp as winampImport

WM_USER = 0x400
WM_WA_IPC = WM_USER

IPC_PE_DELETEINDEX = 104

IPC_GETLISTLENGTH = 124
## (requires Winamp 2.0+)
## int length = SendMessage(hwnd_winamp,WM_WA_IPC,0,IPC_GETLISTLENGTH);
## IPC_GETLISTLENGTH returns the length of the current playlist, in tracks.

IPC_GETPLAYLISTFILE = 211
## (requires Winamp 2.04+, only usable from plug-ins (not external apps))
## char *name=SendMessage(hwnd_winamp,WM_WA_IPC,index,IPC_GETPLAYLISTFILE);
## IPC_GETPLAYLISTFILE gets the filename of the playlist entry [index].
## returns a pointer to it. returns NULL on error.

IPC_GETWND = 260
## (requires Winamp 2.9+)
## HWND h=SendMessage(hwnd_winamp,WM_WA_IPC,IPC_GETWND_xxx,IPC_GETWND);
## returns the HWND of the window specified.
IPC_GETWND_PE = 1

# FIXME: make class hold on to handle for winamp and recreate it if error
#        (poss already does this...)
class WinampWindows(MediaPlayer):
    def __init__(self, loggerFactory, noQueue, configParser, defaultPlayer,
                 safePlayers, trackFactory):
        MediaPlayer.__init__(self, loggerFactory, "NQr.Winamp", noQueue,
                             configParser, defaultPlayer, safePlayers,
                             trackFactory)
        self._winamp = winampImport.Winamp()
        self.launchBackground()
        
    def launch(self):
        self._sendDebug("Launching Winamp.")
        if self._winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
        else:
            self._sendInfo("Winamp is already running.")
            self._winamp.focus()

    def launchBackground(self):
        if self._winamp.getRunning() == False:
            self._sendDebug("Launching Winamp.")
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
            while True:
                time.sleep(.25)
                if self._winamp.getRunning() == True:
                    self._sendInfo("Winamp has been launched.")
                    return

    def close(self):
        self._sendDebug("Closing Winamp.")
        if self._winamp.getRunning() == True:
            self._winamp.close()
            while True:
                time.sleep(.25)
                if self._winamp.getRunning() == False:
                    self._sendInfo("Winamp has been closed.")
                    return
        else:
            self._sendDebug("Winamp is not running.")

    def _addTrack(self, filepath):
        self.launchBackground()
        self._sendInfo("Adding \'"+filepath+"\' to playlist.")
        self._winamp.enqueue(filepath)
        
    def _insertTrack(self, filepath, position):
        self.launchBackground()
        self._sendInfo("Inserting \'"+filepath+"\' into playlist position "\
                          +str(position)+".")
        playlist = self.savePlaylist()
        for pos in range(len(playlist), position - 1, -1):
            self.deleteTrack(pos)
#        self.cropPlaylist(len(playlist) - position - 1)
        self._winamp.enqueue(filepath)
        for path in playlist[position:]:
            self._winamp.enqueue(path)
            
##    def playTrack(self, filepath):

    def deleteTrack(self, position):
        self.launchBackground()
        self._sendDebug("Deleting track in position "+str(position)\
                           +" from playlist.")
        playlistEditorHandle = self._winamp.doIpcCommand(IPC_GETWND,
                                                         IPC_GETWND_PE)
        ctypes.windll.user32.SendMessageA(playlistEditorHandle, WM_WA_IPC,
                                          IPC_PE_DELETEINDEX, position)

    def clearPlaylist(self):
        self.launchBackground()
        self._sendDebug("Clearing playlist.")
        self._winamp.clearPlaylist()

    def nextTrack(self):
        self.launchBackground()
        self._sendDebug("Moving to next track in playlist.")
        self._winamp.next()
        if self._winamp.getStatus() != "playing":
            self.play()

    def pause(self):
        self.launchBackground()
        self._sendDebug("Pausing playback.")
        self._winamp.pause()

    def play(self):
        self.launchBackground()
        self._sendDebug("Resuming playback or restarting current track.")
        self._winamp.play()
        
    def playAtPosition(self, position):
        self.launchBackground()
        self._sendDebug("Playing track at position.")
        self._winamp.setCurrentTrack(position)
        self._winamp.play()

    def previousTrack(self):
        self.launchBackground()
        self._sendDebug("Moving to previous track in playlist.")
        self._winamp.previous()
        if self._winamp.getStatus() != "playing":
            self.play()

    def stop(self):
        self.launchBackground()
        self._sendDebug("Stopping playback.")
        self._winamp.fadeStop()

    def getShuffle(self):
        self.launchBackground()
        self._sendDebug("Retrieving shuffle status.")
        return self._winamp.getShuffle()

    def setShuffle(self, status):
        self.launchBackground()
        self._sendDebug("Setting shuffle status.")
        if status == True or status == 1:
            self._winamp.setShuffle(1)
            self._sendInfo("Shuffle turned on.")
        if status == False or status == 0:
            self._winamp.setShuffle(0)
            self._sendInfo("Shuffle turned off.")

    def getPlaylistLength(self):
        self.launchBackground()
        self._sendDebug("Retrieving playlist length.")
        return self._winamp.getPlaylistLength()

    def getCurrentTrackPos(self):
        if self._winamp.getRunning() == False:
            raise PlayerNotRunningError
        return self._winamp.getCurrentTrack()

    ## poss insecure: should always be checked for trackness
    ## gets track at a playlist position
    ## Has logging option so track monitor can call it without spamming the
    ## debug log.
    def _getTrackPathAtPos(self, trackPosition, logging=True):
        if self._winamp.getRunning() == False:
            raise PlayerNotRunningError
        if logging == True:
            self._sendDebug("Retrieving path of track at position "\
                               +str(trackPosition)+".")
        winampWindow = self._winamp.hwnd
        memoryPointer = self._winamp.doIpcCommand(IPC_GETPLAYLISTFILE,
                                                  trackPosition)
        (threadID,
         processID) = win32process.GetWindowThreadProcessId(winampWindow)
        winampProcess = win32api.OpenProcess(win32con.PROCESS_VM_READ, False,
                                             processID)
        memoryBuffer = ctypes.create_string_buffer(256)
        if logging == True:
            self._sendDebug("Reading Winamp's memory.")
        ctypes.windll.kernel32.ReadProcessMemory(winampProcess.handle,
                                                 memoryPointer, memoryBuffer,
                                                 256, 0)
        winampProcess.Close()
        if logging == True:
            self._sendDebug("Retrieving path from memory buffer.")
        try:
            rawPath = win32api.GetFullPathName(
                memoryBuffer.raw.split("\x00")[0])
        except win32api.error as err:
            (winerror, funcname, strerror) = err
            if winerror != 299:
                raise err
            self._sendError("Playlist is empty.")
            raise NoTrackError
        if logging == True:
            self._sendDebug("Converting path into unicode.")
        return convertToUnicode(rawPath, self._sendWarning, logging)
