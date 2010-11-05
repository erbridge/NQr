## Mac OS, iTunes interface
##
## TODO: talk applescript directly
## TODO: allow user to choose playlistname

import subprocess

from MediaPlayer import MediaPlayer

class iTunesMacOS(MediaPlayer):
    def __init__(self, playlistname="\"NQr\""):
        self.playlistname = playlistname

    def runCommand(self, command):
        PIPE = subprocess.PIPE
        osa = subprocess.Popen('osascript', shell=True, stdin=PIPE,
                               stdout=PIPE, stderr=PIPE)
        (out, err) = osa.communicate(command)
        print out
        print err

    def launch(self):
        command = "tell application \"iTunes\"\n launch\n end tell"
        self.runCommand(command)

    def close(self):
        command = "tell application \"iTunes\"\n quit\n end tell"
        self.runCommand(command)

    ## for example: filepath =
    ## 'Macintosh HD:Users:ben:Documents:Felix:NQr:TestDir:02 - Monument.mp3'
    def addTrack(self, filepath):
        filepath = '"'+filepath+'"'
        command = "tell application \"iTunes\"\n add "+filepath\
                  +" to user playlist "+self.playlistname+"\n end tell"
        self.runCommand(command)

    def playTrack(self, filepath):
        filepath = '"'+filepath+'"'
        command = "tell application \"iTunes\"\n play "+filepath+"\n end tell"
        self.runCommand(command)

    def deleteTrack(self, position):
        command = "tell application \"iTunes\"\n delete track "+str(position+1)\
                  +" of "+self.playlistname+"\n end tell"
        self.runCommand(command)

    def nextTrack(self):
        command = "tell application \"iTunes\"\n next track\n play\n end tell"
        self.runCommand(command)

    def pause(self):
        command = """tell application \"iTunes\"
                     if player state is playing then
                     pause
                     else if player state is paused then
                     play
                     end if
                     end tell"""
        self.runCommand(command)

    def play(self):
        command = """tell application \"iTunes\"
                     if player state is playing then stop
                     play
                     end tell"""
        self.runCommand(command)

    def previousTrack(self):
        command = """tell application \"iTunes\"
                     previous track
                     play
                     end tell"""
        self.runCommand(command)
    
    def stop(self):
        command = "tell application \"iTunes\"\n stop\n end tell"
        self.runCommand(command)

##    def addTrack(self, trackname):
##        trackname = '"'+trackname+'"'
##        command = """tell application "iTunes"
##                    duplicate track """+trackname+""" to user playlist """\
##                    +self.playlistname+"""
##                    end tell"""
##        self.runCommand(command)

##    def playTrack(self, trackname):
##        trackname = '"'+trackname+'"'
##        command = """tell application "iTunes"
##                     play track """+trackname+"""
##                     end tell"""
##        self.runCommand(command)
