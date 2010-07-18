##NQr
## TODO: sort out ' in filenames
## TODO: allow use of bpm for music queuing (from ID3)
## TODO: allow user to choose default rating of unheard tracks and mark them as "unrated"
## TODO: allow user to change track from media player and have the NQr update
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score

from mutagen.easyid3 import EasyID3
from GUI import mainWindow
from iTunesMacOS import iTunesMacOS
import os
import wx

print EasyID3.valid_keys.keys()

fileList=[]

##def addDirectory(directory):
##    contents = os.listdir(directory)
##    for n in range(0, len(contents)):
##        path = directory+'/'+contents[n]
##        if os.path.isdir(path):
##            addDirectory(path)
##        elif contents[n][-4:]=='.mp3':
##            if fileList.__contains__(path)==False:
##                fileList.append(path)
    
##class Track:
##    def __init__(self, sql, fn):
##        self.filename = fn
##    def getFilename(self):
##        return self.filename
##    def store(self, sql):
##        stat = "INSERT FileName INTO Tracks VALUES ('" + self.getFilename() + "')"
##        sql.execute(stat)

player = iTunesMacOS()

app = wx.App(False)
frame = mainWindow(None, "NQr")

frame.Center()
frame.addTrack("TestArtist", "TestTrack", "0", "TestLastPlayed")
frame.addDetail("Test Line 1")
frame.addDetail("Test Line 2")

app.MainLoop()

