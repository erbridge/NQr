## Windows, Winamp interface

import ctypes
import os
import string
import subprocess
import time
import win32api
import win32con
import win32process
import winamp as winampImport

class WinampWindows:
## playlistname not used in winamp
    def __init__(self, playlistname=None):
        self.winamp = winampImport.Winamp()
        self.launchBackground()
        
    def launch(self):
        if self.winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
        else:
            self.winamp.focus()

    def launchBackground(self):
        if self.winamp.getRunning() == False:
            PIPE = subprocess.PIPE
            subprocess.Popen("start winamp", stdout=PIPE, shell=True)
            while True:
                time.sleep(.25)
                if self.winamp.getRunning() == True:
                    print "Winamp has been launched."
                    return

    def close(self):
        if self.winamp.getRunning() == True:
            self.winamp.close()

    def addTrack(self, filepath):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.enqueue(filepath)

##    def playTrack(self, filepath):

##    def cropPlaylist(self):

    def nextTrack(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.next()

    def pause(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.pause()

    def play(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.play()

    def previousTrack(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.previous()

    def stop(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.fadeStop()

    def getCurrentTrackPos(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        trackPosition = self.winamp.getCurrentTrack()
        return trackPosition

## poss insecure: should always be checked for trackness
## os.path.abspath breaks with unicode
    def getCurrentTrackPath(self):
        trackPosition = self.getCurrentTrackPos()
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

## gets track at a playlist position relative to the current track (+ve is
## later)
    def getTrackPathAtPos(self, relativePosition):
        trackPosition = self.getCurrentTrackPos()+relativePosition
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
