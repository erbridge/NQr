## NQr
## TODO: sort out ' in filenames
## TODO: allow use of bpm for music queueing (from ID3)
## TODO: allow user to choose default rating of unheard tracks
## TODO: allow user to change track from media player and have the NQr update
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score

import Database
import GUI
import iTunesMacOS
import Randomizer
import Track
import WinampWindows
import wx

## this info should be read from a settings file
if __name__ == '__main__':
    player = WinampWindows.WinampWindows() ## should be called early
    trackFactory = Track.Factory()
    db = Database.Database(trackFactory)
    randomizer = Randomizer.Randomizer(db)
    app = wx.App(False)
    frame = GUI.MainWindow(None, db=db, randomizer=randomizer, player=player,
                           trackFactory=trackFactory)

    frame.Center()

    app.MainLoop()
