## NQr
## TODO: sort out ' in filenames
## TODO: allow use of bpm for music queuing (from ID3)
## TODO: allow user to choose default rating of unheard tracks
## TODO: allow user to change track from media player and have the NQr update
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score

from Database import Database
import GUI
from iTunesMacOS import iTunesMacOS
import Track
from WinampWindows import WinampWindows
import wx

if __name__ == '__main__':
    app = wx.App(False)
    frame = GUI.MainWindow()

    frame.Center()

    frame.addTrack(Track.getTrackFromPath(frame.db, "C:/Users/Felix/Documents/Projects/TestDir/01 - Arctic Monkeys - Brianstorm.mp3"))
    frame.addTrack(Track.getTrackFromPath(frame.db, "C:/Users/Felix/Documents/Projects/TestDir/02 - Arctic Monkeys - Teddy Picker.mp3"))
    frame.addTrack(Track.getTrackFromPath(frame.db, frame.player.getCurrentTrackPath()))

    app.MainLoop()
