## NQr
## TODO: sort out ' in filenames
## TODO: allow use of bpm for music queuing (from ID3)
## TODO: allow user to choose default rating of unheard tracks
## TODO: allow user to change track from media player and have the NQr update
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score

import GUI

app = wx.App(False)
frame = GUI.mainWindow(None, Database(), iTunesMacOS())
frame.Center()
app.MainLoop()
