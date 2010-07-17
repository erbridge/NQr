## GUI
## TODO: set minimum sizes of windows
## TODO: add library viewer with scoring funcionality
## TODO: remove bottom lines/copy to main
## TODO: debug message window with levels of messages (basic score up/down
##       etc for users and more complex for devs) using "logging" module?

from NQr_iTunes_MacOS import iTunesMacOS
##from NQr_Database import Database as db
import wx

class mainWindow(wx.Frame):
    ID_ARTIST = 1
    ID_TRACK = 2
    ID_SCORE = 3
    ID_LASTPLAYED = 4
    ID_SCORESLIDER = 5
    ID_TRACKLIST = 6
    ID_DETAILS = 7
    ID_NOWPLAYING = 8
    ID_ADDDIRECTORY = 9
    ID_ADDFILE = 10
    ID_PREFS = 11
    
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title)
        self.CreateStatusBar()
        self.initMenuBar()
        self.initMainSizer()
        
        self.Show(True)

    def initMenuBar(self):
        self.initFileMenu()
        self.initPlayerMenu()
        self.initOptionsMenu()
        
        menuBar = wx.MenuBar()        
        menuBar.Append(self.fileMenu, "&File")
        menuBar.Append(self.playerMenu, "&Player")
        menuBar.Append(self.optionsMenu, "&Options")

        self.SetMenuBar(menuBar)
        
    def initFileMenu(self):
        self.fileMenu = wx.Menu()        
        menuAbout = self.fileMenu.Append(wx.ID_ABOUT, "&About NQr",
                                         " Information about NQr")
        self.fileMenu.AppendSeparator()
        menuAddFile = self.fileMenu.Append(self.ID_ADDFILE, "Add &File...",
                                           " Add a file to the library")
        menuAddDirectory = self.fileMenu.Append(self.ID_ADDDIRECTORY,
                                                "Add &Directory...",
                                                " Add a directory to the library")
##        menuOpen = self.fileMenu.Append(wx.ID_OPEN, "&Open", " Open a file")
        self.fileMenu.AppendSeparator()
        menuExit = self.fileMenu.Append(wx.ID_EXIT, "E&xit", " Terminate NQr")
        
        self.Bind(wx.EVT_MENU, self.onAbout, menuAbout)
##        self.Bind(wx.EVT_MENU, self.onAddFile, menuAddFile)
##        self.Bind(wx.EVT_MENU, self.onAddDirectory, menuAddDirectory)
        self.Bind(wx.EVT_MENU, self.onExit, menuExit)
##        self.Bind(wx.EVT_MENU, self.onOpen, menuOpen)

    ## TODO: change up in "Rate Up" to an arrow
    def initPlayerMenu(self):
        self.playerMenu = wx.Menu()
        menuPlay = self.playerMenu.Append(-1, "&Play",
                                          " Play or restart the current track")
        menuPause = self.playerMenu.Append(-1, "P&ause",
                                           " Pause or resume the current track")
        menuNext = self.playerMenu.Append(-1, "&Next Track",
                                          " Play the next track")
        menuPrevious = self.playerMenu.Append(-1, "Pre&vious Track",
                                              " Play the previous track")
        menuStop = self.playerMenu.Append(-1, "&Stop",
                                          " Stop the current track")
        self.playerMenu.AppendSeparator()
        menuRateUp = self.playerMenu.Append(-1, "Rate &Up",
                                            " Increase the score of the current track")
        menuRateDown = self.playerMenu. Append(-1, "Rate &Down",
                                               " Decrease the score of the current track")
        self.playerMenu.AppendSeparator()
        menuLaunchPlayer = self.playerMenu.Append(-1, "&Launch Player",
                                                  " Launch the selected media player")
        menuExitPlayer = self.playerMenu.Append(-1, "E&xit Player",
                                                " Terminate the selected media player")

        self.Bind(wx.EVT_MENU, self.onPlay, menuPlay)
        self.Bind(wx.EVT_MENU, self.onPause, menuPause)
        self.Bind(wx.EVT_MENU, self.onStop, menuStop)
        self.Bind(wx.EVT_MENU, self.onPrevious, menuPrevious)
        self.Bind(wx.EVT_MENU, self.onNext, menuNext)
##        self.Bind(wx.EVT_MENU, self.onRateUp, menuRateUp)
##        self.Bind(wx.EVT_MENU, self.onRateDown, menuRateDown)
        self.Bind(wx.EVT_MENU, self.onLaunchPlayer, menuLaunchPlayer)
        self.Bind(wx.EVT_MENU, self.onExitPlayer, menuExitPlayer)

    def initOptionsMenu(self):
        self.optionsMenu = wx.Menu()        
        menuPrefs = self.optionsMenu.Append(self.ID_PREFS, "&Preferences...",
                                            " Change NQr's settings")
        menuRescan = self.optionsMenu.Append(-1, "&Rescan Library",
                                             " Search previously added directories for new files")

##        self.Bind(wx.EVT_MENU, self.onPrefs, menuPrefs)
##        self.Bind(wx.EVT_MENU, self.onRescan, menuRescan)
        
    def initMainSizer(self):
        self.initPlayerControls()
        self.initDetails()
        self.initTrackSizer()
        
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)        
        self.mainSizer.Add(self.playerControls, 0, wx.EXPAND)
        self.mainSizer.Add(self.trackSizer, 1,
                           wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, 4)
        self.mainSizer.Add(self.details, 0, wx.EXPAND|wx.ALL, 3)
        
        self.SetSizer(self.mainSizer)
        self.SetAutoLayout(True)
        self.mainSizer.Fit(self)
                
## TODO: use svg or gd to create button images via wx.Bitmap and wx.BitmapButton
    def initPlayerControls(self):
        self.playerControls = wx.Panel(self)        
        previousButton = wx.Button(self.playerControls, wx.ID_ANY, "Prev")
        playButton = wx.Button(self.playerControls, wx.ID_ANY, "Play")
        pauseButton = wx.Button(self.playerControls, wx.ID_ANY, "Pause")
        stopButton = wx.Button(self.playerControls, wx.ID_ANY, "Stop")
        nextButton = wx.Button(self.playerControls, wx.ID_ANY, "Next")
        
        buttonPanel = wx.BoxSizer(wx.HORIZONTAL)
        buttonPanel.Add(previousButton, 0, wx.ALL, 4)
        buttonPanel.Add(playButton, 0, wx.ALL, 4)
        buttonPanel.Add(pauseButton, 0, wx.ALL, 4)
        buttonPanel.Add(stopButton, 0, wx.ALL, 4)
        buttonPanel.Add(nextButton, 0, wx.ALL, 4)
        
        self.playerControls.SetSizer(buttonPanel)

        self.Bind(wx.EVT_BUTTON, self.onPrevious, previousButton)
        self.Bind(wx.EVT_BUTTON, self.onPlay, playButton)
        self.Bind(wx.EVT_BUTTON, self.onPause, pauseButton)
        self.Bind(wx.EVT_BUTTON, self.onStop, stopButton)
        self.Bind(wx.EVT_BUTTON, self.onNext, nextButton)

    def initDetails(self):
        self.details = wx.TextCtrl(self, self.ID_DETAILS,
                                   style=wx.TE_READONLY|wx.TE_MULTILINE|
                                   wx.TE_DONTWRAP)

    def initTrackSizer(self):
        self.initTrackList()
        self.initScoreSlider()
        
        self.trackSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.trackSizer.Add(self.trackList, 1, wx.EXPAND|wx.RIGHT, 5)
        self.trackSizer.Add(self.scoreSlider, 0, wx.EXPAND)

    # first column for displaying "Now Playing" or a "+"
    def initTrackList(self):
        self.trackList = wx.ListCtrl(self, self.ID_TRACKLIST,
                                     style=wx.LC_REPORT|wx.LC_VRULES,
                                     size=(448,-1))
        self.trackList.InsertColumn(self.ID_NOWPLAYING, "",
                                    format=wx.LIST_FORMAT_CENTER, width=18)
        self.trackList.InsertColumn(self.ID_ARTIST, "Artist",
                                    format=wx.LIST_FORMAT_CENTER, width=100)
        self.trackList.InsertColumn(self.ID_TRACK, "Track",
                                    format=wx.LIST_FORMAT_CENTER, width=170)
        self.trackList.InsertColumn(self.ID_SCORE, "Score",
                                    format=wx.LIST_FORMAT_CENTER, width=40)
        self.trackList.InsertColumn(self.ID_LASTPLAYED, "Last Played",
                                    format=wx.LIST_FORMAT_CENTER, width=120)

    def initScoreSlider(self):
        self.scoreSlider = wx.Slider(self, self.ID_SCORESLIDER, 0, -10, 10,
                                     style=wx.SL_RIGHT|wx.SL_LABELS|
                                     wx.SL_INVERSE)
        
    def addDetail(self, detail):
        self.details.AppendText(detail+"\n")

    def addTrack(self, artist, track, score, lastPlayed):
##        if track.IsCurrentTrack()==False:
        index = self.trackList.InsertStringItem(0, "")
        self.trackList.SetStringItem(index, 1, artist)
        self.trackList.SetStringItem(index, 2, track)
        self.trackList.SetStringItem(index, 3, score)
        self.trackList.SetStringItem(index, 4, lastPlayed)

    def onAbout(self, e):
        dialog = wx.MessageDialog(self, "For all your NQing needs", "NQr",
                                  wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

##    def onAddFile(self, e):

##    def onAddDirectory(self, e):
        
##    def onOpen(self, e):
##        self.dirname = ''
##        dialog = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.*",
##                               wx.OPEN)
##        if dialog.ShowModal() == wx.ID_OK:
##            self.filename = dialog.GetFilename()
##            self.dirname = dialog.GetDirectory()
##            f = open(os.path.join(self.dirname, self.filename), 'r')
##            self.control.SetValue(f.read())
##            f.close()
##        dialog.Destroy()

    def onExit(self, e):
        self.Close(True)

    def onNext(self, e):
        player.nextTrack()

    def onPause(self, e):
        player.pause()

    def onPlay(self, e):
        player.play()

    def onPrevious(self, e):
        player.previousTrack()

    def onStop(self, e):
        player.stop()

##    def onRateUp(self, e):

##    def onRateDown(self, e):

    def onLaunchPlayer(self, e):
        player.launch()

    def onExitPlayer(self, e):
        player.close()

##    def onPrefs(self, e):

##    def onRescan(self, e):


player = iTunesMacOS()
app = wx.App(False)
frame = mainWindow(None, "NQr")

frame.Center()
frame.addTrack("TestArtist", "TestTrack", "0", "TestLastPlayed")
frame.addTrack("TestArtist2", "TestTrack2", "1", "TestLastPlayed2")
frame.addDetail("Test Line 1")
frame.addDetail("Test Line 2")

app.MainLoop()
