## GUI
## TODO: set minimum sizes of windows
## TODO: add library viewer with scoring funcionality
## TODO: remove bottom lines/copy to main
## TODO: debug message window with levels of messages (basic score up/down
##       etc for users and more complex for devs) using "logging" module?
## TODO: add remove file/directory menus, with confirmation
## TODO: add rightclick menu to tracks
## TODO: add requeue feature
## TODO: add support for mulitple selections
## TODO: change play button and menu item to play selected track? and add to
##       right click menu
## TODO: add submenu to player menu and right click menu with e.g. "rate 10"

from Database import Database
from iTunesMacOS import iTunesMacOS
import Track
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
    
    def __init__(self, parent, db, player):
        self.db = db
        self.player = player
        
        wx.Frame.__init__(self, parent, title="NQr")
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
                                                " Add a directory to the library and watch list")
        self.fileMenu.AppendSeparator()
        menuRemoveDirectory = self.fileMenu.Append(-1, "&Remove Directory...",
                                                   "Remove a directory from the watch list")
        self.fileMenu.AppendSeparator()
        menuExit = self.fileMenu.Append(wx.ID_EXIT, "E&xit", " Terminate NQr")
        
        self.Bind(wx.EVT_MENU, self.onAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.onAddFile, menuAddFile)
        self.Bind(wx.EVT_MENU, self.onAddDirectory, menuAddDirectory)
        self.Bind(wx.EVT_MENU, self.onRemoveDirectory, menuRemoveDirectory)
        self.Bind(wx.EVT_MENU, self.onExit, menuExit)

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
                                            " Increase the score of the current track by one")
        menuRateDown = self.playerMenu.Append(-1, "Rate &Down",
                                               " Decrease the score of the current track by one")
        self.playerMenu.AppendSeparator()
        menuResetScore = self.playerMenu.Append(-1, "Reset Sc&ore",
                                                " Reset the score of the current track")
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
        self.Bind(wx.EVT_MENU, self.onRateUp, menuRateUp)
        self.Bind(wx.EVT_MENU, self.onRateDown, menuRateDown)
        self.Bind(wx.EVT_MENU, self.onResetScore, menuResetScore)
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
## TODO: add requeue button and "play this" button to play selected track
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
                                   wx.TE_DONTWRAP, size=(-1,140))

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
        self.trackList.InsertColumn(self.ID_TRACK, "Title",
                                    format=wx.LIST_FORMAT_CENTER, width=170)
        self.trackList.InsertColumn(self.ID_SCORE, "Score",
                                    format=wx.LIST_FORMAT_CENTER, width=40)
        self.trackList.InsertColumn(self.ID_LASTPLAYED, "Last Played",
                                    format=wx.LIST_FORMAT_CENTER, width=120)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelectTrack, self.trackList)
##        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onDeselectTrack, self.trackList)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.onTrackRightClick,
                  self.trackList)

    def initScoreSlider(self):
        self.scoreSlider = wx.Slider(self, self.ID_SCORESLIDER, 0, -10, 10,
                                     style=wx.SL_RIGHT|wx.SL_LABELS|
                                     wx.SL_INVERSE)

        self.Bind(wx.EVT_SCROLL_CHANGED, self.onScoreSliderMove,
                  self.scoreSlider)
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.onScoreSliderMove,
                  self.scoreSlider)
        
    def addTrack(self, track):
##        if IsCurrentTrack()==False:
        if self.db.isScored(track) == False:
            isScored = "+"
        else:
            isScored = ""
        if self.db.getLastPlayed(track) == False:
            lastPlayed = "-"
        else:
            lastPlayed = self.db.getLastPlayed(track) ## should be time from last play
        index = self.trackList.InsertStringItem(0, isScored)
        self.trackList.SetStringItem(index, 1, self.db.getArtist(track))
        self.trackList.SetStringItem(index, 2, self.db.getTitle(track))
        self.trackList.SetStringItem(index, 3, str(self.db.getScore(track)))
        self.trackList.SetStringItem(index, 4, lastPlayed)
        self.trackList.SetItemData(index, self.db.getTrackID(track))

    def addTrackAtPos(self, track, index):
##        if IsCurrentTrack()==False:
        if self.db.isScored(track) == False:
            isScored = "+"
        else:
            isScored = ""
        if self.db.getLastPlayed(track) == False:
            lastPlayed = "-"
        else:
            lastPlayed = self.db.getLastPlayed(track) ## should be time from last play
        self.trackList.InsertStringItem(index, isScored)
        self.trackList.SetStringItem(index, 1, self.db.getArtist(track))
        self.trackList.SetStringItem(index, 2, self.db.getTitle(track))
        self.trackList.SetStringItem(index, 3, str(self.db.getScore(track)))
        self.trackList.SetStringItem(index, 4, lastPlayed)
        self.trackList.SetItemData(index, self.db.getTrackID(track))

    def addDetail(self, detail):
        self.details.AppendText(detail+"\n")

    def clearDetails(self):
        self.details.Clear()

## the first populateDetails seems to produce a larger font than subsequent
## calls
## TODO: should focus on the top of the deatils
    def populateDetails(self, track):
        if self.db.getLastPlayed(track) == False:
            lastPlayed = "-"
        else:
            lastPlayed = self.db.getLastPlayed(track) ## should be time from last play
        self.clearDetails()
        self.addDetail("Artist: "+self.db.getArtist(track))
        self.addDetail("Title: "+self.db.getTitle(track))
        self.addDetail("Album: "+self.db.getAlbum(track))
        self.addDetail("Track: "+self.db.getTrackNumber(track))
        self.addDetail("Score: "+str(self.db.getScore(track))+"     Last Played: "+lastPlayed)
        self.addDetail("Filetrack: "+self.db.getPath(track))

    def setScoreSliderPosition(self, score):
        self.scoreSlider.SetValue(score)

## should deal with limited cache size
    def onSelectTrack(self, e):
        self.trackID = e.GetData()
        self.index = e.GetIndex()
        self.track = Track.getTrackFromCache(self.trackID)
        self.populateDetails(self.track)
        self.setScoreSliderPosition(self.db.getScoreValue(self.track))

##    def onDeselectTrack(self, e):
##        path = currentTrack()
##        self.populateDetails(path)

    def onScoreSliderMove(self, e):
        try:
            score = self.scoreSlider.GetValue()
            self.db.setScore(self.track, score)
            self.refreshSelectedTrack()
            self.populateDetails(self.track)
        except AttributeError as err:
            if str(err) != "'mainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def refreshSelectedTrack(self):
        self.trackList.DeleteItem(self.index)
        self.addTrackAtPos(self.track, self.index)
        self.selectTrack(self.index)

    def selectTrack(self, index):
        self.trackList.SetItemState(index, wx.LIST_STATE_SELECTED, -1)

    def onTrackRightClick(self, e):
        point = e.GetPoint()
        trackRightClickMenu = wx.Menu()
        menuTrackRightClickRateUp = trackRightClickMenu.Append(
            -1, "Rate &Up", " Increase the score of the current track by one")
        menuTrackRightClickRateDown = trackRightClickMenu.Append(
            -1, "Rate &Down", " Decrease the score of the current track by one")
##        self.playerMenu.AppendSeparator()
##        menuTrackRightClickResetScore = trackRightClickMenu.Append(
##            -1, "Reset Sc&ore", " Reset the score of the current track")
        self.Bind(wx.EVT_MENU, self.onRateUp, menuTrackRightClickRateUp)
        self.Bind(wx.EVT_MENU, self.onRateDown, menuTrackRightClickRateDown)
        self.Bind(wx.EVT_MENU, self.onResetScore, menuTrackRightClickResetScore)

        self.PopupMenu(trackRightClickMenu, point)
        trackRightClickMenu.Destroy()
    
    def onAbout(self, e):
        dialog = wx.MessageDialog(self, "For all your NQing needs", "NQr",
                                  wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

## TODO: change buttons to say "import" rather than "open"/"choose"
    def onAddFile(self, e):
        defaultDirectory = ''
        dialog = wx.FileDialog(self, "Choose a file", defaultDirectory, "",
                               "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|MP4 files (*.mp4)|*.mp4",
                               wx.FD_OPEN|wx.FD_MULTIPLE|wx.FD_CHANGE_DIR)
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            for f in paths:
                self.db.addTrack(f)
##            f = open(os.path.join(self.dirname, self.filename), 'r')
##            self.control.SetValue(f.read())
##            f.close()
        dialog.Destroy()

    def onAddDirectory(self, e):
        defaultDirectory = ''
        dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                              wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.addDirectory(path)
        dialog.Destroy()

    def onRemoveDirectory(self, e):
        defaultDirectory = ''
        dialog = wx.DirDialog(self, "Choose a directory to remove",
                              defaultDirectory, wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.removeDirectory(path)
        dialog.Destroy()

    def onExit(self, e):
        self.Close(True)

    def onNext(self, e):
        self.player.nextTrack()

    def onPause(self, e):
        self.player.pause()

    def onPlay(self, e):
        self.player.play()

    def onPrevious(self, e):
        self.player.previousTrack()

    def onStop(self, e):
        self.player.stop()

    def onRateUp(self, e):
        try:
            score = self.db.getScoreValue(self.track)
            if score != 10:
                self.db.setScore(self.track, score+1)
                self.refreshSelectedTrack()
                self.populateDetails(self.track) ## poss superfluous
            else:
                print "The track already has the maximum score!"
        except AttributeError as err:
            if str(err) != "'mainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onRateDown(self, e):
        try:
            score = self.db.getScoreValue(self.track)
            if score != -10:
                self.db.setScore(self.track, score-1)
                self.refreshSelectedTrack()
                self.populateDetails(self.track) ## poss superfluous
            else:
                print "The track already has the minimum score!"
        except AttributeError as err:
            if str(err) != "'mainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onResetScore(self, e):
        try:
            self.db.setUnscored(self.track)
            self.refreshSelectedTrack()
            self.populateDetails(self.track) ## poss superfluous
        except AttributeError as err:
            if str(err) != "'mainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return
        
    def onLaunchPlayer(self, e):
        self.player.launch()

    def onExitPlayer(self, e):
        self.player.close()

##    def onPrefs(self, e):

##    def onRescan(self, e):

app = wx.App(False)
frame = mainWindow(None, Database(), iTunesMacOS())

frame.Center()
frame.addTrack(Track.getTrackFromPath(frame.db, "/Users/ben/Documents/Felix/NQr-old/TestDir/01 - Day's End.mp3"))
frame.addTrack(Track.getTrackFromPath(frame.db, "/Users/ben/Documents/Felix/NQr-old/TestDir/02 - Monument.mp3"))
frame.addTrack(Track.getTrackFromPath(frame.db, "/Users/ben/Documents/Felix/NQr-old/TestDir/1/03 - Against My Nature.mp3"))
##frame.addDetail("Test Line 1")
##frame.addDetail("Test Line 2")
##frame.populateDetails("/Users/ben/Documents/Felix/NQr-old/TestDir/01 - Day's End.mp3")

app.MainLoop()
