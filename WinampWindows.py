## Windows, Winamp interface
##
## Tested on Winamp 5+

import ctypes
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
        if self._winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
        else:
            self._winamp.focus()

    def launchBackground(self):
        if self._winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
            while True:
                time.sleep(.25)
                if self._winamp.getRunning() == True:
                    self._logger.debug("Winamp has been launched.")
##                    print "Winamp has been launched."
                    return

    def close(self):
        if self._winamp.getRunning() == True:
            self._winamp.close()

    def addTrack(self, filepath):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        self._winamp.enqueue(filepath)

##    def playTrack(self, filepath):

    def deleteTrack(self, position):
        playlistEditorHandle = self._winamp.doIpcCommand(IPC_GETWND,
                                                         IPC_GETWND_PE)
        ctypes.windll.user32.SendMessageA(playlistEditorHandle, WM_WA_IPC,
                                          IPC_PE_DELETEINDEX, position)

    def clearPlaylist(self):
        self._winamp.clearPlaylist()

    def nextTrack(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        self._winamp.next()

    def pause(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        self._winamp.pause()

    def play(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        self._winamp.play()

    def previousTrack(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        self._winamp.previous()

    def stop(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        self._winamp.fadeStop()

    def getShuffle(self):
        return self._winamp.getShuffle()

    def setShuffle(self, status):
        if status == True:
            self._winamp.setShuffle(1)
        if status == False:
            self._winamp.setShuffle(0)
        else:
            self._winamp.setShuffle(status)

    def getPlaylistLength(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        playlistLength = self._winamp.doIpcCommand(IPC_GETLISTLENGTH)
        return playlistLength

    def getCurrentTrackPos(self):
        if self._winamp.getRunning() == False:
            self.launchBackground()
        trackPosition = self._winamp.getCurrentTrack()
        return trackPosition

## poss insecure: should always be checked for trackness
## gets track at a playlist position
    def getTrackPathAtPos(self, trackPosition):
##        trackPosition = self.getCurrentTrackPos()+relativePosition
        winampWindow = self._winamp.hwnd
        memoryPointer = self._winamp.doIpcCommand(IPC_GETPLAYLISTFILE,
                                                  trackPosition)
        (threadID,
         processID) = win32process.GetWindowThreadProcessId(winampWindow)
        winampProcess = win32api.OpenProcess(win32con.PROCESS_VM_READ, False,
                                             processID)
        memoryBuffer = ctypes.create_string_buffer(256)
        ctypes.windll.kernel32.ReadProcessMemory(winampProcess.handle,
                                                 memoryPointer, memoryBuffer,
                                                 256, 0)
        winampProcess.Close()
        hexlist = []
        for n in range(256):
            hexlist.append(hex(n))
##        path = os.path.abspath(memoryBuffer.raw.split('\x00')[0])
        rawPath = win32api.GetFullPathName(memoryBuffer.raw.split("\x00")[0])
        path = u""
        try:
            path = unicode(rawPath)
        except UnicodeDecodeError:
            for s in rawPath:
                try:
                    path += unicode(s)
                except UnicodeDecodeError as err:
                    errStr = str(err)
                    startIndex = errStr.index("0x")
                    endIndex = errStr.index(" ", startIndex)
                    hexStr = ""
                    for i in range(startIndex, endIndex):
                        hexStr += errStr[i]
                    path += unichr(int(hexStr, 16))
        return path
