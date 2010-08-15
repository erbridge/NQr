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

from MediaPlayer import MediaPlayer

WM_USER = 0x400
WM_WA_IPC = WM_USER
IPC_GETWND_PE = 1
IPC_GETWND = 260
IPC_PE_DELETEINDEX = 104
IPC_GETLISTLENGTH = 124
IPC_GETPLAYLISTFILE = 211

class WinampWindows(MediaPlayer):
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

    def cropPlaylist(self, number):
        for n in range(number):
            playlistEditorHandle = self.winamp.doIpcCommand(IPC_GETWND,
                                                            IPC_GETWND_PE)
            ctypes.windll.user32.SendMessageA(playlistEditorHandle, WM_WA_IPC,
                                              IPC_PE_DELETEINDEX, 0)

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

    def getShuffle(self):
        return self.winamp.getShuffle()

    def setShuffle(self, status):
        if status == True:
            self.winamp.setShuffle(1)
        if status == False:
            self.winamp.setShuffle(0)
        else:
            self.winamp.setShuffle(status)

    def getPlaylistLength(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        playlistLength = self.winamp.doIpcCommand(IPC_GETLISTLENGTH)
        return playlistLength

    def getCurrentTrackPos(self):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        trackPosition = self.winamp.getCurrentTrack()
        return trackPosition

## poss insecure: should always be checked for trackness
## os.path.abspath breaks with unicode poss use win32api.GetFullPathName
    def getCurrentTrackPath(self):
        trackPosition = self.getCurrentTrackPos()
        winampWindow = self.winamp.hwnd
        memoryPointer = self.winamp.doIpcCommand(IPC_GETPLAYLISTFILE,
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
        path = os.path.abspath(memoryBuffer.raw.split('\x00')[0])
        return path

## gets track at a playlist position
    def getTrackPathAtPos(self, trackPosition):
##        trackPosition = self.getCurrentTrackPos()+relativePosition
        winampWindow = self.winamp.hwnd
        memoryPointer = self.winamp.doIpcCommand(IPC_GETPLAYLISTFILE,
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
        path = os.path.abspath(memoryBuffer.raw.split('\x00')[0])
        return path

## FIXME: sets currently playing track to first track in the list, but continues
##        to play the old track
    def loadPlaylist(self, playlist):
        if self.winamp.getRunning() == False:
            self.launchBackground()
        self.winamp.clearPlaylist()
        for filepath in playlist:
            self.winamp.enqueue(filepath)
