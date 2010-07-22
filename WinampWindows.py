## Windows, Winamp interface

import ctypes
import os
import string
import subprocess
import win32api
import win32con
import win32process
import winamp as winampImport

class WinampWindows:
## playlistname not used in winamp
    def __init__(self, playlistname=None):
        self.winamp = winampImport.Winamp()
        
    def launch(self):
        if self.winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
        else:
            self.winamp.focus()
##        self.winamp.start()

    def close(self):
        self.winamp.close()

    def addTrack(self, filepath):
        self.winamp.enqueue(filepath)

##    def playTrack(self, filepath):

##    def cropPlaylist(self):

    def nextTrack(self):
        self.winamp.next()

    def pause(self):
        self.winamp.pause()

    def play(self):
        self.winamp.play()

    def previousTrack(self):
        self.winamp.previous()

    def stop(self):
        self.winamp.fadeStop()

    def getCurrentTrackPos(self):
        trackPosition = self.winamp.getCurrentTrack()

## poss insecure?
    def getCurrentTrackPath(self):
        trackPosition = self.winamp.getCurrentTrack()
        winampWindow = self.winamp.hwnd
        memoryPointer = self.winamp.doIpcCommand(211, trackPosition)
        (threadID,
         processID) = win32process.GetWindowThreadProcessId(winampWindow)
        winampProcess = win32api.OpenProcess(win32con.PROCESS_VM_READ, False,
                                             processID)
        memoryBuffer = ctypes.create_string_buffer(256)
        ctypes.windll.kernel32.ReadProcessMemory(winampProcess.handle,
                                                 memoryPointer, memoryBuffer,
                                                 256, 0)
        winampProcess.Close()
        path = os.path.abspath(memoryBuffer.raw.split('\x00')[0])
        return path

    def getTrackPathAtPos(self, relativePosition):
        trackPosition = self.winamp.getCurrentTrack()+relativePosition
        winampWindow = self.winamp.hwnd
        memoryPointer = self.winamp.doIpcCommand(211, trackPosition)
        (threadID,
         processID) = win32process.GetWindowThreadProcessId(winampWindow)
        winampProcess = win32api.OpenProcess(win32con.PROCESS_VM_READ, False,
                                             processID)
        memoryBuffer = ctypes.create_string_buffer(256)
        ctypes.windll.kernel32.ReadProcessMemory(winampProcess.handle,
                                                 memoryPointer, memoryBuffer,
                                                 256, 0)
        winampProcess.Close()
        path = os.path.abspath(memoryBuffer.raw.split('\x00')[0])
        return path
