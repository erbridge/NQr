## GUI
## TODO: set minimum sizes of windows
## TODO: add library viewer with scoring and queueing funcionality
## TODO: remove bottom lines/copy to main
## TODO: debug message window with levels of messages (basic score up/down
##       etc for users and more complex for devs) using "logging" module?
## TODO: add delete file/directory menus, with confirmation?
## TODO: add support for mulitple selections
## TODO: add play button and menu item to play selected track? and add to
##       right click menu
## TODO: add menu option to turn NQr queueing on/off. When off change trackList
##       behaviour to only show played tracks, not to represent unplayed tracks,
##       or show only 3 future tracks?
## TODO: set up rescan on startup?
## TODO: make add/rescan directory/files a background operation: poss create a
##       thread to check the directory and queue the database to add the file.
## TODO: poss create delay before counting a play (to ignore skips)
## TODO: deal with tracks played not in database (ignore them?)
## TODO: add keyboard shortcuts
## TODO: when nothing is selected NQr should act as if the currently playing
##       track is selected
## TODO: remember playlist contents for when NQr is toggled off.
## TODO: leftmost column of track list no longer needed

from collections import deque
import os
from threading import *
import time
import wx

ID_EVT_TRACK_CHANGE = wx.NewId()
##ID_EVT_TRACK_QUEUE = wx.NewId()

def EVT_TRACK_CHANGE(window, func):
    window.Connect(-1, -1, ID_EVT_TRACK_CHANGE, func)

class TrackChangeEvent(wx.PyEvent):
    def __init__(self, db, trackFactory, path):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_TRACK_CHANGE)
        self.db = db
        self.trackFactory = trackFactory
        self.path = path

    def getTrack(self):
        return self.trackFactory.getTrackFromPath(self.db, self.path)

##def EVT_TRACK_QUEUE(window, func):
##    window.Connect(-1, -1, ID_EVT_TRACK_QUEUE, func)
##
##class TrackQueueEvent(wx.PyEvent):
##    def __init__(self):
##        wx.PyEvent.__init__(self)
##        self.SetEventType(ID_EVT_TRACK_QUEUE)

## must be aborted before closing!
class TrackChangeThread(Thread):
    def __init__(self, window, db, player, trackFactory):
        Thread.__init__(self)
##        self.setDaemon(True)
        self.window = window
        self.db = db
        self.player = player
        self.trackFactory = trackFactory
        self.abortFlag = False
        self.start()

## poss should use position rather than filename?
## FIXME: sometimes gets the wrong track if skipped too fast: should return the
##        path with the event (poss fixed). Also happens if track changes while
##        scoring
    def run(self):
        currentTrack = self.player.getCurrentTrackPath()
##        changeCount = 3
        while True:
            time.sleep(.5)
            newTrack = self.player.getCurrentTrackPath()
            if newTrack != currentTrack:
                currentTrack = newTrack
                wx.PostEvent(self.window, TrackChangeEvent(self.db,
                                                           self.trackFactory,
                                                           currentTrack))
##                changeCount += 1
##            if changeCount == 3:
##                wx.PostEvent(self.window, TrackQueueEvent())
##                changeCount = 0
            if self.abortFlag == True:
                return

    def abort(self):
        self.abortFlag = True


## doesn't yet unlock GUI
class DatabaseThread(Thread):
    def __init__(self, db):
        Thread.__init__(self)
        self.db = db
        self.start()

    def run(self):
        pass

    def rescanDirectories(self):
        self.db.rescanDirectories()

#### TODO: poss create popup dialog when complete
#### continues even if NQr is closed
##class DatabaseOperationThread(Thread):
##    def __init__(self, db, operation, path):
##        Thread.__init__(self)
##        self.setDaemon(True)
##        self.db = db
##        self.operation = operation
##        self.path = path
##        self.start()
##
##    def run(self):
##        if self.operation == 0 or self.operation == "addTrack":
##            self.db.addTrack(self.path)
##        if self.operation == 1 or self.operation == "addDirectory":
##            self.db.addDirectory(self.path)
##        if self.operation == 2 or self.operation == "addDirecoryOnce":
##            self.db.addDirectoryNoWatch(self.path)
##        if self.operation == 3 or self.operation == "removeDirectory":
##            self.db.removeDirectory(self.path)
##        if self.operation == 4 or self.operation == "rescanDirectories":
##            self.db.rescanDirectories()
##        else:
##            print "No such operation."

class MainWindow(wx.Frame):
    ID_ARTIST = wx.NewId()
    ID_TRACK = wx.NewId()
    ID_SCORE = wx.NewId()
    ID_LASTPLAYED = wx.NewId()
    ID_SCORESLIDER = wx.NewId()
    ID_TRACKLIST = wx.NewId()
    ID_DETAILS = wx.NewId()
    ID_NOWPLAYING = wx.NewId()
    ID_ADDDIRECTORY = wx.NewId()
    ID_ADDFILE = wx.NewId()
    ID_PREFS = wx.NewId()
    ID_TOGGLENQR = wx.NewId()

    def __init__(self, parent, db, randomizer, player, trackFactory, system,
                 title="NQr", restorePlaylist=True, enqueueOnStartup=True,
                 rescanOnStartup=False, defaultPlaylistLength=11):
##        self.db = DatabaseThread(db).database
        self.db = db
        self.randomizer = randomizer
        self.player = player
        self.trackFactory = trackFactory
        self.system = system
        self.restorePlaylist = restorePlaylist
        self.enqueueOnStartup = enqueueOnStartup
        self.rescanOnStartup = rescanOnStartup
        self.defaultPlaylistLength = defaultPlaylistLength
        self.defaultTrackPosition = int(round(self.defaultPlaylistLength/2))
        self.trackChangeThread = TrackChangeThread(self, self.db, self.player,
                                                   self.trackFactory)
##        self.trackChangeThread = None
        self.index = None

        wx.Frame.__init__(self, parent, title=title)
        self.CreateStatusBar()
        self.initMenuBar()
        self.initMainSizer()

        EVT_TRACK_CHANGE(self, self.onTrackChange)
##        EVT_TRACK_QUEUE(self, self.onEnqueueTracks)
        self.Bind(wx.EVT_CLOSE, self.onClose, self)

        if self.restorePlaylist == True:
            self.oldPlaylist = None

        if self.enqueueOnStartup == True:
            self.optionsMenu.Check(self.ID_TOGGLENQR, True)
            self.onToggleNQr()

        if self.rescanOnStartup == True:
            self.onRescan()

## TODO: if current track is None or there is only one track, NQr should queue
##       a load of tracks
        self.addTrack(
            self.trackFactory.getTrackFromPath(
                self.db, self.player.getCurrentTrackPath())
            )

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
        menuAbout = self.fileMenu.Append(
            wx.ID_ABOUT, "&About NQr", " Information about NQr")
        self.fileMenu.AppendSeparator()
        menuAddFile = self.fileMenu.Append(
            self.ID_ADDFILE, "Add &File...", " Add a file to the library")
        menuAddDirectory = self.fileMenu.Append(
            self.ID_ADDDIRECTORY, "Add &Directory...",
            " Add a directory to the library and watch list")
        menuAddDirectoryOnce = self.fileMenu.Append(
            -1, "Add Directory &Once...",
            " Add a directory to the library but not the watch list")
        self.fileMenu.AppendSeparator()
        menuRemoveDirectory = self.fileMenu.Append(
            -1, "&Remove Directory...",
            " Remove a directory from the watch list")
        self.fileMenu.AppendSeparator()
        menuLinkTracks = self.fileMenu.Append(
            -1, "&Link Tracks...",
            " Link two tracks so they always play together")
        menuRemoveLink = self.fileMenu.Append(
            -1, "Remo&ve Link...",
            " Remove the link between two tracks")
        self.fileMenu.AppendSeparator()
        menuExit = self.fileMenu.Append(wx.ID_EXIT, "E&xit", " Terminate NQr")

        self.Bind(wx.EVT_MENU, self.onAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.onAddFile, menuAddFile)
        self.Bind(wx.EVT_MENU, self.onAddDirectory, menuAddDirectory)
        self.Bind(wx.EVT_MENU, self.onAddDirectoryOnce, menuAddDirectoryOnce)
        self.Bind(wx.EVT_MENU, self.onRemoveDirectory, menuRemoveDirectory)
        self.Bind(wx.EVT_MENU, self.onLinkTracks, menuLinkTracks)
        self.Bind(wx.EVT_MENU, self.onRemoveLink, menuRemoveLink)
        self.Bind(wx.EVT_MENU, self.onExit, menuExit)

    ## TODO: change up in "Rate Up" to an arrow
    def initPlayerMenu(self):
        self.initRateMenu()

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
        menuRateUp = self.playerMenu.Append(
            -1, "Rate &Up", " Increase the score of the selected track by one")
        menuRateDown = self.playerMenu.Append(
            -1, "Rate &Down",
            " Decrease the score of the selected track by one")
        self.playerMenu.AppendMenu(-1, "&Rate", self.rateMenu)
        self.playerMenu.AppendSeparator()
        menuRequeue = self.playerMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
        menuResetScore = self.playerMenu.Append(
            -1, "Reset Sc&ore", " Reset the score of the selected track")
        self.playerMenu.AppendSeparator()
        menuLaunchPlayer = self.playerMenu.Append(
            -1, "&Launch Player", " Launch the selected media player")
        menuExitPlayer = self.playerMenu.Append(
            -1, "E&xit Player", " Terminate the selected media player")

        self.Bind(wx.EVT_MENU, self.onPlay, menuPlay)
        self.Bind(wx.EVT_MENU, self.onPause, menuPause)
        self.Bind(wx.EVT_MENU, self.onStop, menuStop)
        self.Bind(wx.EVT_MENU, self.onPrevious, menuPrevious)
        self.Bind(wx.EVT_MENU, self.onNext, menuNext)
        self.Bind(wx.EVT_MENU, self.onRateUp, menuRateUp)
        self.Bind(wx.EVT_MENU, self.onRateDown, menuRateDown)
        self.Bind(wx.EVT_MENU, self.onRequeue, menuRequeue)
        self.Bind(wx.EVT_MENU, self.onResetScore, menuResetScore)
        self.Bind(wx.EVT_MENU, self.onLaunchPlayer, menuLaunchPlayer)
        self.Bind(wx.EVT_MENU, self.onExitPlayer, menuExitPlayer)

## could be better with a for loop?
    def initRateMenu(self):
        self.rateMenu = wx.Menu()
        menuRatePos10 = self.rateMenu.Append(
            -1, "Rate as 10", " Set the score of the selected track to 10")
        menuRatePos9 = self.rateMenu.Append(
            -1, "Rate as 9", " Set the score of the selected track to 9")
        menuRatePos8 = self.rateMenu.Append(
            -1, "Rate as 8", " Set the score of the selected track to 8")
        menuRatePos7 = self.rateMenu.Append(
            -1, "Rate as 7", " Set the score of the selected track to 7")
        menuRatePos6 = self.rateMenu.Append(
            -1, "Rate as 6", " Set the score of the selected track to 6")
        menuRatePos5 = self.rateMenu.Append(
            -1, "Rate as 5", " Set the score of the selected track to 5")
        menuRatePos4 = self.rateMenu.Append(
            -1, "Rate as 4", " Set the score of the selected track to 4")
        menuRatePos3 = self.rateMenu.Append(
            -1, "Rate as 3", " Set the score of the selected track to 3")
        menuRatePos2 = self.rateMenu.Append(
            -1, "Rate as 2", " Set the score of the selected track to 2")
        menuRatePos1 = self.rateMenu.Append(
            -1, "Rate as 1", " Set the score of the selected track to 1")
        menuRate0 = self.rateMenu.Append(
            -1, "Rate as 0", " Set the score of the selected track to 0")
        menuRateNeg1 = self.rateMenu.Append(
            -1, "Rate as -1", " Set the score of the selected track to -1")
        menuRateNeg2 = self.rateMenu.Append(
            -1, "Rate as -2", " Set the score of the selected track to -2")
        menuRateNeg3 = self.rateMenu.Append(
            -1, "Rate as -3", " Set the score of the selected track to -3")
        menuRateNeg4 = self.rateMenu.Append(
            -1, "Rate as -4", " Set the score of the selected track to -4")
        menuRateNeg5 = self.rateMenu.Append(
            -1, "Rate as -5", " Set the score of the selected track to -5")
        menuRateNeg6 = self.rateMenu.Append(
            -1, "Rate as -6", " Set the score of the selected track to -6")
        menuRateNeg7 = self.rateMenu.Append(
            -1, "Rate as -7", " Set the score of the selected track to -7")
        menuRateNeg8 = self.rateMenu.Append(
            -1, "Rate as -8", " Set the score of the selected track to -8")
        menuRateNeg9 = self.rateMenu.Append(
            -1, "Rate as -9", " Set the score of the selected track to -9")
        menuRateNeg10 = self.rateMenu.Append(
            -1, "Rate as -10", " Set the score of the selected track to -10")

        self.Bind(wx.EVT_MENU, lambda e, score=10: self.onRate(e, score),
                  menuRatePos10)
        self.Bind(wx.EVT_MENU, lambda e, score=9: self.onRate(e, score),
                  menuRatePos9)
        self.Bind(wx.EVT_MENU, lambda e, score=8: self.onRate(e, score),
                  menuRatePos8)
        self.Bind(wx.EVT_MENU, lambda e, score=7: self.onRate(e, score),
                  menuRatePos7)
        self.Bind(wx.EVT_MENU, lambda e, score=6: self.onRate(e, score),
                  menuRatePos6)
        self.Bind(wx.EVT_MENU, lambda e, score=5: self.onRate(e, score),
                  menuRatePos5)
        self.Bind(wx.EVT_MENU, lambda e, score=4: self.onRate(e, score),
                  menuRatePos4)
        self.Bind(wx.EVT_MENU, lambda e, score=3: self.onRate(e, score),
                  menuRatePos3)
        self.Bind(wx.EVT_MENU, lambda e, score=2: self.onRate(e, score),
                  menuRatePos2)
        self.Bind(wx.EVT_MENU, lambda e, score=1: self.onRate(e, score),
                  menuRatePos1)
        self.Bind(wx.EVT_MENU, lambda e, score=0: self.onRate(e, score),
                  menuRate0)
        self.Bind(wx.EVT_MENU, lambda e, score=-1: self.onRate(e, score),
                  menuRateNeg1)
        self.Bind(wx.EVT_MENU, lambda e, score=-2: self.onRate(e, score),
                  menuRateNeg2)
        self.Bind(wx.EVT_MENU, lambda e, score=-3: self.onRate(e, score),
                  menuRateNeg3)
        self.Bind(wx.EVT_MENU, lambda e, score=-4: self.onRate(e, score),
                  menuRateNeg4)
        self.Bind(wx.EVT_MENU, lambda e, score=-5: self.onRate(e, score),
                  menuRateNeg5)
        self.Bind(wx.EVT_MENU, lambda e, score=-6: self.onRate(e, score),
                  menuRateNeg6)
        self.Bind(wx.EVT_MENU, lambda e, score=-7: self.onRate(e, score),
                  menuRateNeg7)
        self.Bind(wx.EVT_MENU, lambda e, score=-8: self.onRate(e, score),
                  menuRateNeg8)
        self.Bind(wx.EVT_MENU, lambda e, score=-9: self.onRate(e, score),
                  menuRateNeg9)
        self.Bind(wx.EVT_MENU, lambda e, score=-10: self.onRate(e, score),
                  menuRateNeg10)

##        self.rateMenu.Check(self.ID_menuRate0, True)
##        try:
##            score = self.db.getScoreValueFromID(self.trackID)
##            if score == 10:
##                self.rateMenu.Check(menuRatePos10, True)
##            elif score == 9:
##                self.rateMenu.Check(menuRatePos9, True)
##            elif score == 8:
##                self.rateMenu.Check(menuRatePos8, True)
##            elif score == 7:
##                self.rateMenu.Check(menuRatePos7, True)
##            elif score == 6:
##                self.rateMenu.Check(menuRatePos6, True)
##            elif score == 5:
##                self.rateMenu.Check(menuRatePos5, True)
##            elif score == 4:
##                self.rateMenu.Check(menuRatePos4, True)
##            elif score == 3:
##                self.rateMenu.Check(menuRatePos3, True)
##            elif score == 2:
##                self.rateMenu.Check(menuRatePos2, True)
##            elif score == 1:
##                self.rateMenu.Check(menuRatePos1, True)
##            elif score == 0:
##                self.rateMenu.Check(menuRate0, True)
##            elif score == 1:
##                self.rateMenu.Check(menuRateNeg1, True)
##            elif score == 2:
##                self.rateMenu.Check(menuRateNeg2, True)
##            elif score == 3:
##                self.rateMenu.Check(menuRateNeg3, True)
##            elif score == 4:
##                self.rateMenu.Check(menuRateNeg4, True)
##            elif score == 5:
##                self.rateMenu.Check(menuRateNeg5, True)
##            elif score == 6:
##                self.rateMenu.Check(menuRateNeg6, True)
##            elif score == 7:
##                self.rateMenu.Check(menuRateNeg7, True)
##            elif score == 8:
##                self.rateMenu.Check(menuRateNeg8, True)
##            elif score == 9:
##                self.rateMenu.Check(menuRateNeg9, True)
##            elif score == 10:
##                self.rateMenu.Check(menuRateNeg10, True)
##        except AttributeError as err:
##            if str(err) != "'MainWindow' object has no attribute 'trackID'":
##                raise err
##            print "No track selected."
##            return

    def initOptionsMenu(self):
        self.optionsMenu = wx.Menu()
        menuPrefs = self.optionsMenu.Append(self.ID_PREFS, "&Preferences...",
                                            " Change NQr's settings")
        menuRescan = self.optionsMenu.Append(
            -1, "&Rescan Library", " Search previously added directories for new files")
        self.optionsMenu.AppendSeparator()
        self.menuToggleNQr = self.optionsMenu.AppendCheckItem(
            self.ID_TOGGLENQR, "En&queue with NQr",
            " Use NQr to enqueue tracks")

##        self.Bind(wx.EVT_MENU, self.onPrefs, menuPrefs)
        self.Bind(wx.EVT_MENU, self.onRescan, menuRescan)
        self.Bind(wx.EVT_MENU, self.onToggleNQr, self.menuToggleNQr)

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

    ## first column for displaying "Now Playing" or a "+"
    def initTrackList(self):
        self.trackList = wx.ListCtrl(self, self.ID_TRACKLIST,
                                     style=wx.LC_REPORT|wx.LC_VRULES,
                                     size=(476,-1))
        self.trackList.InsertColumn(self.ID_NOWPLAYING, "",
                                    format=wx.LIST_FORMAT_CENTER, width=20)
        self.trackList.InsertColumn(self.ID_ARTIST, "Artist",
                                    format=wx.LIST_FORMAT_CENTER, width=100)
        self.trackList.InsertColumn(self.ID_TRACK, "Title",
                                    format=wx.LIST_FORMAT_CENTER, width=170)
        self.trackList.InsertColumn(self.ID_SCORE, "Score",
                                    format=wx.LIST_FORMAT_CENTER, width=45)
        self.trackList.InsertColumn(self.ID_LASTPLAYED, "Last Played",
                                    format=wx.LIST_FORMAT_CENTER, width=120)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelectTrack, self.trackList)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.onDeselectTrack,
                  self.trackList)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.onTrackRightClick,
                  self.trackList)

    def initScoreSlider(self):
        if self.system == 'FreeBSD':
            self.scoreSlider = wx.Slider(self, self.ID_SCORESLIDER, 0, -10, 10,
                                         style=wx.SL_VERTICAL|wx.SL_LABELS|
                                         wx.SL_INVERSE)
        else:
            self.scoreSlider = wx.Slider(self, self.ID_SCORESLIDER, 0, -10, 10,
                                         style=wx.SL_RIGHT|wx.SL_LABELS|
                                         wx.SL_INVERSE)

        self.Bind(wx.EVT_SCROLL_CHANGED, self.onScoreSliderMove,
                  self.scoreSlider)
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self.onScoreSliderMove,
                  self.scoreSlider)

    def onClose(self, e):
        if self.trackChangeThread:
            self.trackChangeThread.abort()
        self.Destroy()

    def onAbout(self, e):
        dialog = wx.MessageDialog(self, "For all your NQing needs", "NQr",
                                  wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

## TODO: change buttons to say "import" rather than "open"/"choose"
    def onAddFile(self, e):
        defaultDirectory = ''
        dialog = wx.FileDialog(
            self, "Choose a file", defaultDirectory, "",
            "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
            wx.FD_OPEN|wx.FD_MULTIPLE|wx.FD_CHANGE_DIR
            )
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            for f in paths:
                self.db.addTrack(f)
        dialog.Destroy()

    def onAddDirectory(self, e):
        defaultDirectory = ''
        if self.system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                                  wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.addDirectory(path)
        dialog.Destroy()

    def onAddDirectoryOnce(self, e):
        defaultDirectory = ''
        if self.system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                                  wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.addDirectoryNoWatch(path)
        dialog.Destroy()

    def onRemoveDirectory(self, e):
        defaultDirectory = ''
        if self.system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory to remove",
                                  defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory to remove",
                                  defaultDirectory, wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.removeDirectory(path)
        dialog.Destroy()

    def onLinkTracks(self, e):
        defaultDirectory = ''
        firstDialog = wx.FileDialog(
            self, "Choose the first file", defaultDirectory, "",
            "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
            wx.FD_OPEN|wx.FD_CHANGE_DIR
            )
        if firstDialog.ShowModal() == wx.ID_OK:
            firstPath = firstDialog.GetPath()
            firstTrack = self.trackFactory.getTrackFromPath(self.db, firstPath)
            directory = os.path.dirname(firstPath)
            secondDialog = wx.FileDialog(
                self, "Choose the second file", directory, "",
                "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
                wx.FD_OPEN|wx.FD_CHANGE_DIR
                )
            if secondDialog.ShowModal() == wx.ID_OK:
                secondPath = secondDialog.GetPath()
                secondTrack = self.trackFactory.getTrackFromPath(self.db,
                                                                 secondPath)
                self.db.addLink(firstTrack, secondTrack)
            secondDialog.Destroy()
        firstDialog.Destroy()

    def onRemoveLink(self, e):
        defaultDirectory = ''
        firstDialog = wx.FileDialog(
            self, "Choose the first file", defaultDirectory, "",
            "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
            wx.FD_OPEN|wx.FD_CHANGE_DIR
            )
        if firstDialog.ShowModal() == wx.ID_OK:
            firstPath = firstDialog.GetPath()
            firstTrack = self.trackFactory.getTrackFromPath(self.db, firstPath)
            directory = os.path.dirname(firstPath)
            secondDialog = wx.FileDialog(
                self, "Choose the second file", directory, "",
                "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
                wx.FD_OPEN|wx.FD_CHANGE_DIR
                )
            if secondDialog.ShowModal() == wx.ID_OK:
                secondPath = secondDialog.GetPath()
                secondTrack = self.trackFactory.getTrackFromPath(self.db,
                                                                 secondPath)
                if self.db.getLinkID(firstTrack, secondTrack) != None:
                    self.db.removeLink(firstTrack, secondTrack)
                else:
                    self.db.removeLink(secondTrack, firstTrack)
            secondDialog.Destroy()
        firstDialog.Destroy()

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
            if str(err) != "'MainWindow' object has no attribute 'track'":
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
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onRate(self, e, score):
        try:
            oldScore = self.db.getScoreValue(self.track)
            if score != oldScore:
                self.db.setScore(self.track, score)
                self.refreshSelectedTrack()
                self.populateDetails(self.track) ## poss superfluous
            else:
                print "The track already has that score!"
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onRequeue(self, e):
        try:
            self.player.addTrack(self.track.getPath())
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onResetScore(self, e):
        try:
            self.db.setUnscored(self.track)
            self.refreshSelectedTrack()
            self.populateDetails(self.track) ## poss superfluous
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onLaunchPlayer(self, e):
        self.player.launch()

    def onExitPlayer(self, e):
        self.player.close()

## FIXME: toggle should be turned off when NQr is closed
    def onToggleNQr(self, e=None):
        if self.menuToggleNQr.IsChecked() == False:
            self.toggleNQr = False
            self.player.setShuffle(self.oldShuffleStatus)
            if self.oldPlaylist != None and self.restorePlaylist == True:
                self.player.loadPlaylist(self.oldPlaylist)
            print "Enqueueing turned off."
        elif self.menuToggleNQr.IsChecked() == True:
            self.toggleNQr = True
            self.oldShuffleStatus = self.player.getShuffle()
            self.player.setShuffle(False)
            ## poss shouldn't restore the playlist ever?
            if self.restorePlaylist == True:
                self.oldPlaylist = self.player.savePlaylist()
            self.maintainPlaylist()
            print "Enqueueing turned on."
##        if not self.trackChangeThread:
##            self.trackChangeThread = TrackChangeThread(self, self.player)
##            print "Enqueueing turned on."
##        else:
##            self.trackChangeThread.abort()
##            self.trackChangeThread = None
##            print "Enqueueing turned off."

##    def onPrefs(self, e):

    def onRescan(self, e=None):
        self.db.rescanDirectories()

    def onSelectTrack(self, e):
        self.trackID = e.GetData()
        self.index = e.GetIndex()
        self.track = self.trackFactory.getTrackFromID(self.db, self.trackID)
        self.populateDetails(self.track)
        self.setScoreSliderPosition(self.db.getScoreValue(self.track))

    def onDeselectTrack(self, e):
        self.clearDetails()
##        path = currentTrack()
##        self.populateDetails(path)

    def onTrackRightClick(self, e):
        point = e.GetPoint()
        self.initRateMenu()
        trackRightClickMenu = wx.Menu()
        menuTrackRightClickRateUp = trackRightClickMenu.Append(
            -1, "Rate &Up", " Increase the score of the current track by one")
        menuTrackRightClickRateDown = trackRightClickMenu.Append(
            -1, "Rate &Down", " Decrease the score of the current track by one")
        rateRightClickMenu = trackRightClickMenu.AppendMenu(
            -1, "&Rate", self.rateMenu)
        trackRightClickMenu.AppendSeparator()
        menuTrackRightClickRequeue = trackRightClickMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
##        menuTrackRightClickResetScore = trackRightClickMenu.Append(
##            -1, "Reset Sc&ore", " Reset the score of the current track")

        self.Bind(wx.EVT_MENU, self.onRateUp, menuTrackRightClickRateUp)
        self.Bind(wx.EVT_MENU, self.onRateDown, menuTrackRightClickRateDown)
        self.Bind(wx.EVT_MENU, self.onRequeue, menuTrackRightClickRequeue)
##        self.Bind(wx.EVT_MENU, self.onResetScore, menuTrackRightClickResetScore)

        self.PopupMenu(trackRightClickMenu, point)
        rateRightClickMenu.Destroy()
        trackRightClickMenu.Destroy()

    def onScoreSliderMove(self, e):
        try:
            score = self.scoreSlider.GetValue()
            self.db.setScore(self.track, score)
            self.refreshSelectedTrack()
            self.populateDetails(self.track) ## poss superfluous
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onTrackChange(self, e):
        track = e.getTrack()
        self.db.addPlay(track)
        self.addTrack(track)
        self.maintainPlaylist()

    def maintainPlaylist(self):
        if self.toggleNQr == True:
            trackPosition = self.player.getCurrentTrackPos()
            if trackPosition > self.defaultTrackPosition:
                self.player.cropPlaylist(
                    trackPosition - self.defaultTrackPosition)
            playlistLength = self.player.getPlaylistLength()
            if playlistLength < self.defaultPlaylistLength:
                self.enqueueRandomTracks(
                    self.defaultPlaylistLength - playlistLength)

#### should queue the correct number of tracks
##    def onEnqueueTracks(self, e=None):
##        track = self.randomizer.chooseTrack()
##        self.enqueueTrack(track)

    def addTrack(self, track):
##        if IsCurrentTrack()==False:
        if self.db.isScored(track) == False:
            isScored = "+"
        else:
            isScored = ""
        if self.db.getLastPlayedLocalTime(track) == None:
            lastPlayed = "-"
        else:
            lastPlayed = self.db.getLastPlayedLocalTime(track) ## should be time from last play
        index = self.trackList.InsertStringItem(0, isScored)
        self.trackList.SetStringItem(index, 1, self.db.getArtist(track))
        self.trackList.SetStringItem(index, 2, self.db.getTitle(track))
        self.trackList.SetStringItem(index, 3, str(self.db.getScore(track)))
        self.trackList.SetStringItem(index, 4, lastPlayed)
        self.trackList.SetItemData(index, self.db.getTrackID(track))
        if self.index:
            self.index += 1

    def addTrackAtPos(self, track, index):
##        if IsCurrentTrack()==False:
        if self.db.isScored(track) == False:
            isScored = "+"
        else:
            isScored = ""
        if self.db.getLastPlayedLocalTime(track) == None:
            lastPlayed = "-"
        else:
            lastPlayed = self.db.getLastPlayedLocalTime(track) ## should be time from last play
        self.trackList.InsertStringItem(index, isScored)
        self.trackList.SetStringItem(index, 1, self.db.getArtist(track))
        self.trackList.SetStringItem(index, 2, self.db.getTitle(track))
        self.trackList.SetStringItem(index, 3, str(self.db.getScore(track)))
        self.trackList.SetStringItem(index, 4, lastPlayed)
        self.trackList.SetItemData(index, self.db.getTrackID(track))
        if self.index > index:
            self.index += 1

    def enqueueTrack(self, track):
        self.player.addTrack(track.getPath())

## TODO: would be better for NQr to create a queue during idle time and pop from
##       it when enqueuing        
    def enqueueRandomTracks(self, number):
        for n in range(number):
            track = self.randomizer.chooseTrack()
##            self.enqueueTrack(track)
## FIXME: untested!! poss most of the legwork should be done in db.getLinkIDs
            linkIDs = self.db.getLinkIDs(track)
            if linkIDs == None:
                self.enqueueTrack(track)
            else:
                originalLinkID = linkIDs[0]
                (firstTrackID,
                 secondTrackID) = self.db.getLinkedTrackIDs(originalLinkID)
                firstTrack = self.trackFactory.getTrackFromID(self.db,
                                                              firstTrackID)
                secondTrack = self.trackFactory.getTrackFromID(self.db,
                                                               secondTrackID)
                trackQueue = deque([firstTrack, secondTrack])
##                self.enqueueTrack(firstTrack)
##                self.enqueueTrack(secondTrack)
                linkIDs = self.db.getLinkIDs(firstTrack)
                oldLinkIDs = originalLinkID
                ## finds earlier tracks
                while True:
                    for linkID in linkIDs:
                        if linkID not in oldLinkIDs:
                            (newTrackID,
                             trackID) = self.db.getLinkedTrackIDs(linkID)
                            track = self.trackFactory.getTrackFromID(self.db,
                                                                     newTrackID)
                            trackQueue.appendleft(track)
                            oldLinkIDs = linkIDs
                            linkIDs = self.db.getLinkIDs(track)
                    if oldLinkIDs == linkIDs:
                            break
                linkIDs = self.db.getLinkIDs(secondTrack)
                oldLinkIDs = originalLinkID
                ## finds later tracks
                while True:
                    for linkID in linkIDs:
                        if linkID not in oldLinkIDs:
                            (trackID,
                             newTrackID) = self.db.getLinkedTrackIDs(linkID)
                            track = self.trackFactory.getTrackFromID(self.db,
                                                                     newTrackID)
                            trackQueue.append(track)
                            oldLinkIDs = linkIDs
                            linkIDs = self.db.getLinkIDs(track)
                    if oldLinkIDs == linkIDs:
                            break
##                oldTrackID = firstTrackID
##                while linkIDs != None:
##                    for linkID in linkIDs:
##                        (trackID,
##                         newTrackID) = self.db.getLinkedTrackIDs(linkID)
##                        if trackID != oldTrackID:
##                            track = self.trackFactory.getTrackFromID(self.db,
##                                                                     newTrackID)
##                            trackQueue.append(track)
##                            oldTrackID = trackID
##                    linkIDs = self.db.getLinkIDs(track)
                for track in trackQueue:
                    self.enqueueTrack(track)
##                if secondLinkID != None:
##                    (secondTrackID,
##                     thirdTrackID) = self.db.getLinkedTrackIDs(secondLinkID)
##                    thirdTrack = self.trackFactory.getTrackFromID(self.db,
##                                                                  thirdTrackID)
##                    self.enqueueTrack(thirdTrack)

    def setScoreSliderPosition(self, score):
        self.scoreSlider.SetValue(score)

    def refreshSelectedTrack(self):
        self.trackList.DeleteItem(self.index)
        self.addTrackAtPos(self.track, self.index)
        self.selectTrack(self.index)

    def selectTrack(self, index):
        self.trackList.SetItemState(index, wx.LIST_STATE_SELECTED, -1)

## the first populateDetails seems to produce a larger font than subsequent
## calls in Mac OS
## TODO: should focus on the top of the details
    def populateDetails(self, track):
        if self.db.getLastPlayedLocalTime(track) == None:
            lastPlayed = "-"
        else:
            lastPlayed = self.db.getLastPlayedLocalTime(track) ## should be time from last play
        self.clearDetails()
        self.addDetail("Artist:   "+self.db.getArtist(track))
        self.addDetail("Title:   "+self.db.getTitle(track))
        self.addDetail("Track:   "+self.db.getTrackNumber(track)\
                       +"       Album:   "+self.db.getAlbum(track))
        self.addDetail("Score:   "+str(self.db.getScore(track))\
                       +"       Last Played:   "+lastPlayed)
        self.addDetail("Filetrack:   "+self.db.getPath(track))

    def addDetail(self, detail):
        self.details.AppendText(detail+"\n")

    def clearDetails(self):
        self.details.Clear()

##app = wx.App(False)
##frame = MainWindow()
##
##frame.Center()
##frame.addTrack(Track.getTrackFromPath(frame.db, "C:/Users/Felix/Documents/Projects/TestDir/01 - Arctic Monkeys - Brianstorm.mp3"))
##frame.addTrack(Track.getTrackFromPath(frame.db, "C:/Users/Felix/Documents/Projects/TestDir/02 - Arctic Monkeys - Teddy Picker.mp3"))
##frame.addTrack(Track.getTrackFromPath(frame.db, frame.player.getCurrentTrackPath()))
##
##app.MainLoop()
