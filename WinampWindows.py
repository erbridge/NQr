## Windows, Winamp interface

import subprocess
import winamp as winampImport

class WinampWindows:
## playlistname not used in winamp
    def __init__(self, playlistname=None):
        self.winamp = winampImport.Winamp()
        
    def launch(self):
        PIPE = subprocess.PIPE
        subprocess.Popen("start winamp", stdout=PIPE, shell=True)
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
