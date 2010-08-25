## Windows, Winamp interface
##
## Tested on Winamp 5+

import ctypes
from Errors import *
##import os
import subprocess
import time
import win32api
import win32con
import win32process
import winamp as winampImport

from MediaPlayer import MediaPlayer

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

class WinampWindows(MediaPlayer):
## playlistname not used in winamp
    def __init__(self, loggerFactory, playlistname=None):
        self._logger = loggerFactory.getLogger("NQr.Winamp", "debug")
        self._winamp = winampImport.Winamp()
        self.launchBackground()
        
    def launch(self):
        self._logger.debug("Launching Winamp.")
        if self._winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
        else:
            self._logger.info("Winamp is already running.")
            self._winamp.focus()

    def launchBackground(self):
        if self._winamp.getRunning() == False:
            self._logger.debug("Launching Winamp.")
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
            while True:
                time.sleep(.25)
                if self._winamp.getRunning() == True:
                    self._logger.info("Winamp has been launched.")
##                    print "Winamp has been launched."
                    return

    def close(self):
        self._logger.debug("Closing Winamp.")
        if self._winamp.getRunning() == True:
            self._winamp.close()
            while True:
                time.sleep(.25)
                if self._winamp.getRunning() == False:
                    self._logger.info("Winamp has been closed.")
                    return
        else:
            self._logger.debug("Winamp is not running.")

    def addTrack(self, filepath):
        self.launchBackground()
        self._logger.info("Adding \'"+filepath+"\' to playlist.")
        self._winamp.enqueue(filepath)

##    def playTrack(self, filepath):

    def deleteTrack(self, position):
        self._logger.debug("Deleting track in position "+str(position)\
                           +" from playlist.")
        playlistEditorHandle = self._winamp.doIpcCommand(IPC_GETWND,
                                                         IPC_GETWND_PE)
        ctypes.windll.user32.SendMessageA(playlistEditorHandle, WM_WA_IPC,
                                          IPC_PE_DELETEINDEX, position)

    def clearPlaylist(self):
        self._logger.debug("Clearing playlist.")
        self._winamp.clearPlaylist()

    def nextTrack(self):
        self.launchBackground()
        self._logger.debug("Moving to next track in playlist.")
        self._winamp.next()

    def pause(self):
        self.launchBackground()
        self._logger.debug("Pausing playback.")
        self._winamp.pause()

    def play(self):
        self.launchBackground()
        self._logger.debug("Resuming playback or restarting current track.")
        self._winamp.play()

    def previousTrack(self):
        self.launchBackground()
        self._logger.debug("Moving to previous track in playlist.")
        self._winamp.previous()

    def stop(self):
        self.launchBackground()
        self._logger.debug("Stopping playback.")
        self._winamp.fadeStop()

    def getShuffle(self):
        self._logger.debug("Retrieving shuffle status.")
        return self._winamp.getShuffle()

    def setShuffle(self, status):
        self._logger.debug("Setting shuffle status.")
        if status == True or status == 1:
            self._winamp.setShuffle(1)
            self._logger.info("Shuffle turned on.")
        if status == False or status == 0:
            self._winamp.setShuffle(0)
            self._logger.info("Shuffle turned off.")
##        else:
##            self._winamp.setShuffle(status)
##            if type(status) == str:
##                self._logger.info("Shuffle status set to \'"+status+"\'.")
##            else:
##                self._logger.info("Shuffle status set to "+str(status)+".")

    def getPlaylistLength(self):
        self.launchBackground()
        self._logger.debug("Retrieving playlist length.")
        playlistLength = self._winamp.doIpcCommand(IPC_GETLISTLENGTH)
        return playlistLength

    def getCurrentTrackPos(self):
        self.launchBackground()
        trackPosition = self._winamp.getCurrentTrack()
        return trackPosition

## poss insecure: should always be checked for trackness
## gets track at a playlist position
    def getTrackPathAtPos(self, trackPosition):
##        trackPosition = self.getCurrentTrackPos()+relativePosition
        self._logger.debug("Retrieving path of track at position "\
                           +str(trackPosition)+".")
        winampWindow = self._winamp.hwnd
        memoryPointer = self._winamp.doIpcCommand(IPC_GETPLAYLISTFILE,
                                                  trackPosition)
        (threadID,
         processID) = win32process.GetWindowThreadProcessId(winampWindow)
        winampProcess = win32api.OpenProcess(win32con.PROCESS_VM_READ, False,
                                             processID)
        memoryBuffer = ctypes.create_string_buffer(256)
        self._logger.debug("Reading Winamp's memory.")
        ctypes.windll.kernel32.ReadProcessMemory(winampProcess.handle,
                                                 memoryPointer, memoryBuffer,
                                                 256, 0)
        winampProcess.Close()
        self._logger.debug("Retrieving path from memory buffer.")
        hexlist = []
        for n in range(256):
            hexlist.append(hex(n))
##        path = os.path.abspath(memoryBuffer.raw.split('\x00')[0])
        try:
            rawPath = win32api.GetFullPathName(
                memoryBuffer.raw.split("\x00")[0])
        except win32api.error as err:
            (winerror, funcname, strerror) = err
            if winerror != 299:
                raise err
            self._logger.error("Playlist is empty.")
            raise NoTrackError
        self._logger.debug("Converting path into unicode.")
        path = u""
        try:
            path = unicode(rawPath)
        except UnicodeDecodeError:
            self._logger.warning("Found bad characters. Attempting to resolve.")
            for char in rawPath:
                try:
                    path += unicode(char)
                except UnicodeDecodeError as err:
                    errStr = str(err)
                    startIndex = errStr.index("0x")
                    endIndex = errStr.index(" ", startIndex)
                    hexStr = ""
                    for i in range(startIndex, endIndex):
                        hexStr += errStr[i]
                    path += unichr(int(hexStr, 16))
            self._logger.warning("Bad characters resolved.")
        return path
