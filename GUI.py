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
from Errors import *
import os
from threading import *
import time
from Time import RoughAge
from Util import plural

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

ID_EVT_TRACK_CHANGE = wx.NewId()
##ID_EVT_TRACK_QUEUE = wx.NewId()

def EVT_TRACK_CHANGE(window, func):
    window.Connect(-1, -1, ID_EVT_TRACK_CHANGE, func)

class TrackChangeEvent(wx.PyEvent):
    def __init__(self, db, trackFactory, path):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_TRACK_CHANGE)
        self._db = db
        self._trackFactory = trackFactory
        self._path = path

    def getTrack(self):
        return self._trackFactory.getTrackFromPath(self._db, self._path)

##def EVT_TRACK_QUEUE(window, func):
##    window.Connect(-1, -1, ID_EVT_TRACK_QUEUE, func)
##
##class TrackQueueEvent(wx.PyEvent):
##    def __init__(self):
##        wx.PyEvent.__init__(self)
##        self.SetEventType(ID_EVT_TRACK_QUEUE)

## must be aborted when closing!
class TrackMonitor(Thread):
    def __init__(self, window, db, player, trackFactory, loggerFactory):
        Thread.__init__(self)
        self.setDaemon(True)
        self._window = window
        self._db = db
        self._player = player
        self._trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.TrackMonitor", "debug")
        self._abortFlag = False
        self.start()

## poss should use position rather than filename?
## FIXME: sometimes gets the wrong track if skipped too fast: should return the
##        path with the event (poss fixed). Also happens if track changes while
##        scoring
    def run(self):
        logging = True
        try:
            currentTrack = self._player.getCurrentTrackPath(logging=logging)
        except NoTrackError:
            currentTrack = None
##        changeCount = 3
        while True:
            time.sleep(.5)
            try:
                newTrack = self._player.getCurrentTrackPath(logging=logging)
                logging = False
            except NoTrackError:
                newTrack = None
            if newTrack != currentTrack:
                self._logger.debug("Track has changed.")
                currentTrack = newTrack
                wx.PostEvent(self._window, TrackChangeEvent(self._db,
                                                            self._trackFactory,
                                                            currentTrack))
                logging = True
##                changeCount += 1
##            if changeCount == 3:
##                wx.PostEvent(self._window, TrackQueueEvent())
##                changeCount = 0
            if self._abortFlag == True:
                self._logger.info("Stopping track monitor.")
                return

    def abort(self):
        self._abortFlag = True


## doesn't yet unlock GUI
class DatabaseThread(Thread):
    def __init__(self, db):
        Thread.__init__(self)
        self._db = db
        self.start()

    def run(self):
        pass

    def rescanDirectories(self):
        self._db.rescanDirectories()

#### TODO: poss create popup dialog when complete
#### continues even if NQr is closed
##class DatabaseOperationThread(Thread):
##    def __init__(self, db, operation, path):
##        Thread.__init__(self)
##        self.setDaemon(True)
##        self._db = db
##        self._operation = operation
##        self.path = path
##        self.start()
##
##    def run(self):
##        if self._operation == 0 or self._operation == "addTrack":
##            self._db.addTrack(self.path)
##        if self._operation == 1 or self._operation == "addDirectory":
##            self._db.addDirectory(self.path)
##        if self._operation == 2 or self._operation == "addDirecoryOnce":
##            self._db.addDirectoryNoWatch(self.path)
##        if self._operation == 3 or self._operation == "removeDirectory":
##            self._db.removeDirectory(self.path)
##        if self._operation == 4 or self._operation == "rescanDirectories":
##            self._db.rescanDirectories()
##        else:
##            print "No such operation."

class MainWindow(wx.Frame):
    def __init__(self, parent, db, randomizer, player, trackFactory, system,
                 loggerFactory, title="NQr", restorePlaylist=False,
                 enqueueOnStartup=True, rescanOnStartup=False,
                 defaultPlaylistLength=11):
        self._ID_ARTIST = wx.NewId()
        self._ID_TRACK = wx.NewId()
        self._ID_SCORE = wx.NewId()
        self._ID_LASTPLAYED = wx.NewId()
        self._ID_PREVIOUSPLAY = wx.NewId()
        self._ID_WEIGHT = wx.NewId()
        self._ID_SCORESLIDER = wx.NewId()
        self._ID_TRACKLIST = wx.NewId()
        self._ID_DETAILS = wx.NewId()
        self._ID_NOWPLAYING = wx.NewId()
        self._ID_ADDDIRECTORY = wx.NewId()
        self._ID_ADDFILE = wx.NewId()
        self._ID_PREFS = wx.NewId()
        self._ID_TOGGLENQR = wx.NewId()
    
##        self._db = DatabaseThread(db).database
        self._db = db
        self._randomizer = randomizer
        self._player = player
        self._trackFactory = trackFactory
        self._system = system
        self._logger = loggerFactory.getLogger("NQr.GUI", "debug")
        self._restorePlaylist = restorePlaylist
        self._enqueueOnStartup = enqueueOnStartup
        self._rescanOnStartup = rescanOnStartup
        self._defaultPlaylistLength = defaultPlaylistLength
        self._defaultTrackPosition = int(round(self._defaultPlaylistLength/2))
##        self._trackMonitor = None
        self._index = None

        wx.Frame.__init__(self, parent, title=title)
        self._logger.debug("Creating status bar.")
        self.CreateStatusBar()
        self._initCreateMenuBar()
        self._initCreateTrackRightClickMenu()
        self._initCreateMainSizer()

        EVT_TRACK_CHANGE(self, self._onTrackChange)
##        EVT_TRACK_QUEUE(self, self._onEnqueueTracks)
        self.Bind(wx.EVT_CLOSE, self._onClose, self)

        if self._restorePlaylist == True:
            self._oldPlaylist = None

        if self._enqueueOnStartup == True:
            self._optionsMenu.Check(self._ID_TOGGLENQR, True)
            self._onToggleNQr()

        if self._rescanOnStartup == True:
            self._onRescan()

        self._logger.debug("Drawing main window.")
        self.Show(True)
        
        self._logger.info("Starting track monitor.")
        self._trackMonitor = TrackMonitor(self, self._db, self._player,
                                          self._trackFactory, loggerFactory)

    def _initCreateMenuBar(self):
        self._logger.debug("Creating menu bar.")
        self._initCreateFileMenu()
        self._initCreateRateMenu()
        self._initCreatePlayerMenu()
        self._initCreateOptionsMenu()

        menuBar = wx.MenuBar()
        menuBar.Append(self._fileMenu, "&File")
        menuBar.Append(self._playerMenu, "&Player")
        menuBar.Append(self._optionsMenu, "&Options")

        self.SetMenuBar(menuBar)

    def _initCreateFileMenu(self):
        self._logger.debug("Creating file menu.")
        self._fileMenu = wx.Menu()
        menuAbout = self._fileMenu.Append(
            wx.ID_ABOUT, "&About NQr", " Information about NQr")
        self._fileMenu.AppendSeparator()
        menuAddFile = self._fileMenu.Append(
            self._ID_ADDFILE, "Add &File...", " Add a file to the library")
        menuAddDirectory = self._fileMenu.Append(
            self._ID_ADDDIRECTORY, "Add &Directory...",
            " Add a directory to the library and watch list")
        menuAddDirectoryOnce = self._fileMenu.Append(
            -1, "Add Directory &Once...",
            " Add a directory to the library but not the watch list")
        self._fileMenu.AppendSeparator()
        menuRemoveDirectory = self._fileMenu.Append(
            -1, "&Remove Directory...",
            " Remove a directory from the watch list")
        self._fileMenu.AppendSeparator()
        menuLinkTracks = self._fileMenu.Append(
            -1, "&Link Tracks...",
            " Link two tracks so they always play together")
        menuRemoveLink = self._fileMenu.Append(
            -1, "Remo&ve Link...",
            " Remove the link between two tracks")
        self._fileMenu.AppendSeparator()
        menuExit = self._fileMenu.Append(wx.ID_EXIT, "E&xit", " Terminate NQr")

        self.Bind(wx.EVT_MENU, self._onAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self._onAddFile, menuAddFile)
        self.Bind(wx.EVT_MENU, self._onAddDirectory, menuAddDirectory)
        self.Bind(wx.EVT_MENU, self._onAddDirectoryOnce, menuAddDirectoryOnce)
        self.Bind(wx.EVT_MENU, self._onRemoveDirectory, menuRemoveDirectory)
        self.Bind(wx.EVT_MENU, self._onLinkTracks, menuLinkTracks)
        self.Bind(wx.EVT_MENU, self._onRemoveLink, menuRemoveLink)
        self.Bind(wx.EVT_MENU, self._onExit, menuExit)

## could be better with a for loop?
    def _initCreateRateMenu(self):
        self._logger.debug("Creating rate menu.")
        self._rateMenu = wx.Menu()
        menuRatePos10 = self._rateMenu.Append(
            -1, "Rate as 10", " Set the score of the selected track to 10")
        menuRatePos9 = self._rateMenu.Append(
            -1, "Rate as 9", " Set the score of the selected track to 9")
        menuRatePos8 = self._rateMenu.Append(
            -1, "Rate as 8", " Set the score of the selected track to 8")
        menuRatePos7 = self._rateMenu.Append(
            -1, "Rate as 7", " Set the score of the selected track to 7")
        menuRatePos6 = self._rateMenu.Append(
            -1, "Rate as 6", " Set the score of the selected track to 6")
        menuRatePos5 = self._rateMenu.Append(
            -1, "Rate as 5", " Set the score of the selected track to 5")
        menuRatePos4 = self._rateMenu.Append(
            -1, "Rate as 4", " Set the score of the selected track to 4")
        menuRatePos3 = self._rateMenu.Append(
            -1, "Rate as 3", " Set the score of the selected track to 3")
        menuRatePos2 = self._rateMenu.Append(
            -1, "Rate as 2", " Set the score of the selected track to 2")
        menuRatePos1 = self._rateMenu.Append(
            -1, "Rate as 1", " Set the score of the selected track to 1")
        menuRate0 = self._rateMenu.Append(
            -1, "Rate as 0", " Set the score of the selected track to 0")
        menuRateNeg1 = self._rateMenu.Append(
            -1, "Rate as -1", " Set the score of the selected track to -1")
        menuRateNeg2 = self._rateMenu.Append(
            -1, "Rate as -2", " Set the score of the selected track to -2")
        menuRateNeg3 = self._rateMenu.Append(
            -1, "Rate as -3", " Set the score of the selected track to -3")
        menuRateNeg4 = self._rateMenu.Append(
            -1, "Rate as -4", " Set the score of the selected track to -4")
        menuRateNeg5 = self._rateMenu.Append(
            -1, "Rate as -5", " Set the score of the selected track to -5")
        menuRateNeg6 = self._rateMenu.Append(
            -1, "Rate as -6", " Set the score of the selected track to -6")
        menuRateNeg7 = self._rateMenu.Append(
            -1, "Rate as -7", " Set the score of the selected track to -7")
        menuRateNeg8 = self._rateMenu.Append(
            -1, "Rate as -8", " Set the score of the selected track to -8")
        menuRateNeg9 = self._rateMenu.Append(
            -1, "Rate as -9", " Set the score of the selected track to -9")
        menuRateNeg10 = self._rateMenu.Append(
            -1, "Rate as -10", " Set the score of the selected track to -10")

        self.Bind(wx.EVT_MENU, lambda e, score=10: self._onRate(e, score),
                  menuRatePos10)
        self.Bind(wx.EVT_MENU, lambda e, score=9: self._onRate(e, score),
                  menuRatePos9)
        self.Bind(wx.EVT_MENU, lambda e, score=8: self._onRate(e, score),
                  menuRatePos8)
        self.Bind(wx.EVT_MENU, lambda e, score=7: self._onRate(e, score),
                  menuRatePos7)
        self.Bind(wx.EVT_MENU, lambda e, score=6: self._onRate(e, score),
                  menuRatePos6)
        self.Bind(wx.EVT_MENU, lambda e, score=5: self._onRate(e, score),
                  menuRatePos5)
        self.Bind(wx.EVT_MENU, lambda e, score=4: self._onRate(e, score),
                  menuRatePos4)
        self.Bind(wx.EVT_MENU, lambda e, score=3: self._onRate(e, score),
                  menuRatePos3)
        self.Bind(wx.EVT_MENU, lambda e, score=2: self._onRate(e, score),
                  menuRatePos2)
        self.Bind(wx.EVT_MENU, lambda e, score=1: self._onRate(e, score),
                  menuRatePos1)
        self.Bind(wx.EVT_MENU, lambda e, score=0: self._onRate(e, score),
                  menuRate0)
        self.Bind(wx.EVT_MENU, lambda e, score=-1: self._onRate(e, score),
                  menuRateNeg1)
        self.Bind(wx.EVT_MENU, lambda e, score=-2: self._onRate(e, score),
                  menuRateNeg2)
        self.Bind(wx.EVT_MENU, lambda e, score=-3: self._onRate(e, score),
                  menuRateNeg3)
        self.Bind(wx.EVT_MENU, lambda e, score=-4: self._onRate(e, score),
                  menuRateNeg4)
        self.Bind(wx.EVT_MENU, lambda e, score=-5: self._onRate(e, score),
                  menuRateNeg5)
        self.Bind(wx.EVT_MENU, lambda e, score=-6: self._onRate(e, score),
                  menuRateNeg6)
        self.Bind(wx.EVT_MENU, lambda e, score=-7: self._onRate(e, score),
                  menuRateNeg7)
        self.Bind(wx.EVT_MENU, lambda e, score=-8: self._onRate(e, score),
                  menuRateNeg8)
        self.Bind(wx.EVT_MENU, lambda e, score=-9: self._onRate(e, score),
                  menuRateNeg9)
        self.Bind(wx.EVT_MENU, lambda e, score=-10: self._onRate(e, score),
                  menuRateNeg10)

##        self._rateMenu.Check(self._ID_menuRate0, True)
##        try:
##            score = self._db.getScoreValueFromID(self._trackID)
##            if score == 10:
##                self._rateMenu.Check(menuRatePos10, True)
##            elif score == 9:
##                self._rateMenu.Check(menuRatePos9, True)
##            elif score == 8:
##                self._rateMenu.Check(menuRatePos8, True)
##            elif score == 7:
##                self._rateMenu.Check(menuRatePos7, True)
##            elif score == 6:
##                self._rateMenu.Check(menuRatePos6, True)
##            elif score == 5:
##                self._rateMenu.Check(menuRatePos5, True)
##            elif score == 4:
##                self._rateMenu.Check(menuRatePos4, True)
##            elif score == 3:
##                self._rateMenu.Check(menuRatePos3, True)
##            elif score == 2:
##                self._rateMenu.Check(menuRatePos2, True)
##            elif score == 1:
##                self._rateMenu.Check(menuRatePos1, True)
##            elif score == 0:
##                self._rateMenu.Check(menuRate0, True)
##            elif score == 1:
##                self._rateMenu.Check(menuRateNeg1, True)
##            elif score == 2:
##                self._rateMenu.Check(menuRateNeg2, True)
##            elif score == 3:
##                self._rateMenu.Check(menuRateNeg3, True)
##            elif score == 4:
##                self._rateMenu.Check(menuRateNeg4, True)
##            elif score == 5:
##                self._rateMenu.Check(menuRateNeg5, True)
##            elif score == 6:
##                self._rateMenu.Check(menuRateNeg6, True)
##            elif score == 7:
##                self._rateMenu.Check(menuRateNeg7, True)
##            elif score == 8:
##                self._rateMenu.Check(menuRateNeg8, True)
##            elif score == 9:
##                self._rateMenu.Check(menuRateNeg9, True)
##            elif score == 10:
##                self._rateMenu.Check(menuRateNeg10, True)
##        except AttributeError as err:
##            if str(err) != "'MainWindow' object has no attribute 'trackID'":
##                raise err
##            print "No track selected."
##            return

    ## TODO: change up in "Rate Up" to an arrow
    def _initCreatePlayerMenu(self):
        self._logger.debug("Creating player menu.")
        self._playerMenu = wx.Menu()
        menuPlay = self._playerMenu.Append(-1, "&Play",
                                          " Play or restart the current track")
        menuPause = self._playerMenu.Append(-1, "P&ause",
                                           " Pause or resume the current track")
        menuNext = self._playerMenu.Append(-1, "&Next Track",
                                          " Play the next track")
        menuPrevious = self._playerMenu.Append(-1, "Pre&vious Track",
                                              " Play the previous track")
        menuStop = self._playerMenu.Append(-1, "&Stop",
                                          " Stop the current track")
        self._playerMenu.AppendSeparator()
        menuRateUp = self._playerMenu.Append(
            -1, "Rate &Up", " Increase the score of the selected track by one")
        menuRateDown = self._playerMenu.Append(
            -1, "Rate &Down",
            " Decrease the score of the selected track by one")
        self._playerMenu.AppendMenu(-1, "&Rate", self._rateMenu)
        self._playerMenu.AppendSeparator()
        menuRequeue = self._playerMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
        menuResetScore = self._playerMenu.Append(
            -1, "Reset Sc&ore", " Reset the score of the selected track")
        self._playerMenu.AppendSeparator()
        menuLaunchPlayer = self._playerMenu.Append(
            -1, "&Launch Player", " Launch the selected media player")
        menuExitPlayer = self._playerMenu.Append(
            -1, "E&xit Player", " Terminate the selected media player")

        self.Bind(wx.EVT_MENU, self._onPlay, menuPlay)
        self.Bind(wx.EVT_MENU, self._onPause, menuPause)
        self.Bind(wx.EVT_MENU, self._onStop, menuStop)
        self.Bind(wx.EVT_MENU, self._onPrevious, menuPrevious)
        self.Bind(wx.EVT_MENU, self._onNext, menuNext)
        self.Bind(wx.EVT_MENU, self._onRateUp, menuRateUp)
        self.Bind(wx.EVT_MENU, self._onRateDown, menuRateDown)
        self.Bind(wx.EVT_MENU, self._onRequeue, menuRequeue)
        self.Bind(wx.EVT_MENU, self._onResetScore, menuResetScore)
        self.Bind(wx.EVT_MENU, self._onLaunchPlayer, menuLaunchPlayer)
        self.Bind(wx.EVT_MENU, self._onExitPlayer, menuExitPlayer)

    def _initCreateOptionsMenu(self):
        self._logger.debug("Creating options menu.")
        self._optionsMenu = wx.Menu()
        menuPrefs = self._optionsMenu.Append(self._ID_PREFS, "&Preferences...",
                                            " Change NQr's settings")
        menuRescan = self._optionsMenu.Append(
            -1, "&Rescan Library", " Search previously added directories for new files")
        self._optionsMenu.AppendSeparator()
        self.menuToggleNQr = self._optionsMenu.AppendCheckItem(
            self._ID_TOGGLENQR, "En&queue with NQr",
            " Use NQr to enqueue tracks")

        self.Bind(wx.EVT_MENU, self._onPrefs, menuPrefs)
        self.Bind(wx.EVT_MENU, self._onRescan, menuRescan)
        self.Bind(wx.EVT_MENU, self._onToggleNQr, self.menuToggleNQr)

    def _initCreateTrackRightClickMenu(self):
        self._logger.debug("Creating track right click menu.")
        self._trackRightClickMenu = wx.Menu()
        menuTrackRightClickRateUp = self._trackRightClickMenu.Append(
            -1, "Rate &Up", " Increase the score of the current track by one")
        menuTrackRightClickRateDown = self._trackRightClickMenu.Append(
            -1, "Rate &Down", " Decrease the score of the current track by one")
        rateRightClickMenu = self._trackRightClickMenu.AppendMenu(
            -1, "&Rate", self._rateMenu)
        self._trackRightClickMenu.AppendSeparator()
        menuTrackRightClickRequeue = self._trackRightClickMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
        self._trackRightClickMenu.AppendSeparator()
        menuTrackRightClickResetScore = self._trackRightClickMenu.Append(
            -1, "Reset Sc&ore", " Reset the score of the current track")

        self.Bind(wx.EVT_MENU, self._onRateUp, menuTrackRightClickRateUp)
        self.Bind(wx.EVT_MENU, self._onRateDown, menuTrackRightClickRateDown)
        self.Bind(wx.EVT_MENU, self._onRequeue, menuTrackRightClickRequeue)
        self.Bind(wx.EVT_MENU, self._onResetScore, menuTrackRightClickResetScore)

    def _initCreateMainSizer(self):
        self._initCreatePlayerControls()
        self._initCreateDetails()
        self._initCreateTrackSizer()

        self._mainSizer = wx.BoxSizer(wx.VERTICAL)
        self._mainSizer.Add(self._playerControls, 0, wx.EXPAND)
        self._mainSizer.Add(self._trackSizer, 1,
                           wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, 4)
        self._mainSizer.Add(self._details, 0, wx.EXPAND|wx.ALL, 3)

        self.SetSizer(self._mainSizer)
        self.SetAutoLayout(True)
        self._mainSizer.Fit(self)

## TODO: use svg or gd to create button images via wx.Bitmap and wx.BitmapButton
## TODO: add requeue button and "play this" button to play selected track
    def _initCreatePlayerControls(self):
        self._logger.debug("Creating player controls.")
        self._playerControls = wx.Panel(self)
        previousButton = wx.Button(self._playerControls, wx.ID_ANY, "Prev")
        playButton = wx.Button(self._playerControls, wx.ID_ANY, "Play")
        pauseButton = wx.Button(self._playerControls, wx.ID_ANY, "Pause")
        stopButton = wx.Button(self._playerControls, wx.ID_ANY, "Stop")
        nextButton = wx.Button(self._playerControls, wx.ID_ANY, "Next")

        buttonPanel = wx.BoxSizer(wx.HORIZONTAL)
        buttonPanel.Add(previousButton, 0, wx.ALL, 4)
        buttonPanel.Add(playButton, 0, wx.ALL, 4)
        buttonPanel.Add(pauseButton, 0, wx.ALL, 4)
        buttonPanel.Add(stopButton, 0, wx.ALL, 4)
        buttonPanel.Add(nextButton, 0, wx.ALL, 4)

        self._playerControls.SetSizer(buttonPanel)

        self.Bind(wx.EVT_BUTTON, self._onPrevious, previousButton)
        self.Bind(wx.EVT_BUTTON, self._onPlay, playButton)
        self.Bind(wx.EVT_BUTTON, self._onPause, pauseButton)
        self.Bind(wx.EVT_BUTTON, self._onStop, stopButton)
        self.Bind(wx.EVT_BUTTON, self._onNext, nextButton)

    def _initCreateDetails(self):
        self._logger.debug("Creating details panel.")
        self._details = wx.TextCtrl(self, self._ID_DETAILS,
                                   style=wx.TE_READONLY|wx.TE_MULTILINE|
                                   wx.TE_DONTWRAP, size=(-1,140))

    def _initCreateTrackSizer(self):
        self._logger.debug("Creating track panel.")
        self._initCreateTrackList()
        self._initCreateScoreSlider()

        self._trackSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._trackSizer.Add(self._trackList, 1, wx.EXPAND|wx.RIGHT, 5)
        self._trackSizer.Add(self._scoreSlider, 0, wx.EXPAND)

    ## first column for displaying "Now Playing" or a "+"
    def _initCreateTrackList(self):
        self._logger.debug("Creating track playlist.")
        self._trackList = wx.ListCtrl(self, self._ID_TRACKLIST,
                                     style=wx.LC_REPORT|wx.LC_VRULES,
                                     size=(476,-1))
        self._trackList.InsertColumn(self._ID_NOWPLAYING, "",
                                     format=wx.LIST_FORMAT_CENTER, width=20)
        self._trackList.InsertColumn(self._ID_ARTIST, "Artist",
                                     format=wx.LIST_FORMAT_CENTER, width=100)
        self._trackList.InsertColumn(self._ID_TRACK, "Title",
                                     format=wx.LIST_FORMAT_CENTER, width=170)
        self._trackList.InsertColumn(self._ID_SCORE, "Score",
                                     format=wx.LIST_FORMAT_CENTER, width=45)
        self._trackList.InsertColumn(self._ID_LASTPLAYED, "Played At",
                                     format=wx.LIST_FORMAT_CENTER, width=120)
        self._trackList.InsertColumn(self._ID_PREVIOUSPLAY, "Last Played",
                                     format=wx.LIST_FORMAT_CENTER, width=120)
        self._trackList.InsertColumn(self._ID_WEIGHT, "Weight",
                                     format=wx.LIST_FORMAT_CENTER, width=120)


        try:
            self._logger.debug("Adding current track to track playlist.")
            currentTrackPath = self._player.getCurrentTrackPath()
            currentTrack = self._trackFactory.getTrackFromPath(self._db,
                                                              currentTrackPath)
            currentTrackID = currentTrack.getID()
            if currentTrackID != self._db.getLastPlayedTrackID():
                self._logger.debug("Adding play for current track.")
                self._db.addPlay(currentTrack)
            currentTrack.setPreviousPlay(
                self._db.getLastPlayedInSeconds(currentTrack))
            self.addTrack(currentTrack)
        except NoTrackError:
            pass

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onSelectTrack,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._onDeselectTrack,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._onTrackRightClick,
                  self._trackList)

    def _initCreateScoreSlider(self):
        self._logger.debug("Creating score slider.")
        if self._system == 'FreeBSD':
            self._scoreSlider = wx.Slider(self, self._ID_SCORESLIDER, 0, -10,
                                          10, style=wx.SL_VERTICAL|wx.SL_LABELS|
                                          wx.SL_INVERSE)
        else:
            self._scoreSlider = wx.Slider(self, self._ID_SCORESLIDER, 0, -10,
                                          10, style=wx.SL_RIGHT|wx.SL_LABELS|
                                          wx.SL_INVERSE)

        self.Bind(wx.EVT_SCROLL_CHANGED, self._onScoreSliderMove,
                  self._scoreSlider)
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self._onScoreSliderMove,
                  self._scoreSlider)

    def _onTrackRightClick(self, e):
        self._logger.debug("Popping up track right click menu.")
        point = e.GetPoint()
##        self._initCreateRateMenu()
##        trackRightClickMenu = wx.Menu()
##        menuTrackRightClickRateUp = trackRightClickMenu.Append(
##            -1, "Rate &Up", " Increase the score of the current track by one")
##        menuTrackRightClickRateDown = trackRightClickMenu.Append(
##            -1, "Rate &Down", " Decrease the score of the current track by one")
##        rateRightClickMenu = trackRightClickMenu.AppendMenu(
##            -1, "&Rate", self._rateMenu)
##        trackRightClickMenu.AppendSeparator()
##        menuTrackRightClickRequeue = trackRightClickMenu.Append(
##            -1, "Re&queue Track", " Add the selected track to the playlist")
####        menuTrackRightClickResetScore = trackRightClickMenu.Append(
####            -1, "Reset Sc&ore", " Reset the score of the current track")
##
##        self.Bind(wx.EVT_MENU, self._onRateUp, menuTrackRightClickRateUp)
##        self.Bind(wx.EVT_MENU, self._onRateDown, menuTrackRightClickRateDown)
##        self.Bind(wx.EVT_MENU, self._onRequeue, menuTrackRightClickRequeue)
####        self.Bind(wx.EVT_MENU, self._onResetScore, menuTrackRightClickResetScore)

        self.PopupMenu(self._trackRightClickMenu, point)
##        rateRightClickMenu.Destroy()
##        trackRightClickMenu.Destroy()

    def _onAbout(self, e):
        self._logger.debug("Opening about dialog.")
        text = "For all your NQing needs\n"
        text += str(self._db.getNumberOfTracks()) + " tracks in library"
        dialog = wx.MessageDialog(self, text, "NQr",
                                  wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def _onPrefs(self, e):
        self._logger.debug("Opening preferences window.")
        pass

## TODO: change buttons to say "import" rather than "open"/"choose"
    def _onAddFile(self, e):
        self._logger.debug("Opening add file dialog.")
        defaultDirectory = ''
        dialog = wx.FileDialog(
            self, "Choose a file", defaultDirectory, "",
            "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
            wx.FD_OPEN|wx.FD_MULTIPLE|wx.FD_CHANGE_DIR
            )
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            for path in paths:
                self._db.addTrack(os.path.abspath(path))
        dialog.Destroy()

    def _onAddDirectory(self, e):
        self._logger.debug("Opening add directory dialog.")
        defaultDirectory = ''
        if self._system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                                  wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._db.addDirectory(os.path.abspath(path))
        dialog.Destroy()

    def _onAddDirectoryOnce(self, e):
        self._logger.debug("Opening add directory once dialog.")
        defaultDirectory = ''
        if self._system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                                  wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._db.addDirectoryNoWatch(os.path.abspath(path))
        dialog.Destroy()

    def _onRemoveDirectory(self, e):
        self._logger.debug("Opening remove directory dialog.")
        defaultDirectory = ''
        if self._system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory to remove",
                                  defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory to remove",
                                  defaultDirectory, wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._db.removeDirectory(os.path.abspath(path))
        dialog.Destroy()

    def _onRescan(self, e=None):
        self._logger.debug("Rescanning watch list for new files.")
        self._db.rescanDirectories()

    def _onLinkTracks(self, e):
        self._logger.debug("Opening add link dialogs.")
        self._logger.debug("Opening first file dialog.")
        defaultDirectory = ''
        firstDialog = wx.FileDialog(
            self, "Choose the first file", defaultDirectory, "",
            "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
            wx.FD_OPEN|wx.FD_CHANGE_DIR
            )
        if firstDialog.ShowModal() == wx.ID_OK:
            firstPath = firstDialog.GetPath()
            firstTrack = self._trackFactory.getTrackFromPath(
                self._db, os.path.abspath(firstPath))
            self._logger.debug("Opening second file dialog.")
            directory = os.path.dirname(firstPath)
            secondDialog = wx.FileDialog(
                self, "Choose the second file", directory, "",
                "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
                wx.FD_OPEN|wx.FD_CHANGE_DIR
                )
            if secondDialog.ShowModal() == wx.ID_OK:
                secondPath = secondDialog.GetPath()
                secondTrack = self._trackFactory.getTrackFromPath(
                    self._db, os.path.abspath(secondPath))
                self._db.addLink(firstTrack, secondTrack)
            secondDialog.Destroy()
        firstDialog.Destroy()

    def _onRemoveLink(self, e):
        self._logger.debug("Opening remove link dialog.")
        self._logger.debug("Opening first file dialog.")
        defaultDirectory = ''
        firstDialog = wx.FileDialog(
            self, "Choose the first file", defaultDirectory, "",
            "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
            wx.FD_OPEN|wx.FD_CHANGE_DIR
            )
        if firstDialog.ShowModal() == wx.ID_OK:
            firstPath = firstDialog.GetPath()
            firstTrack = self._trackFactory.getTrackFromPath(
                self._db, os.path.abspath(firstPath))
            self._logger.debug("Opening second file dialog.")
            directory = os.path.dirname(firstPath)
            secondDialog = wx.FileDialog(
                self, "Choose the second file", directory, "",
                "Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|*.*",
                wx.FD_OPEN|wx.FD_CHANGE_DIR
                )
            if secondDialog.ShowModal() == wx.ID_OK:
                secondPath = secondDialog.GetPath()
                secondTrack = self._trackFactory.getTrackFromPath(
                    self._db, os.path.abspath(secondPath))
                if self._db.getLinkID(firstTrack, secondTrack) != None:
                    self._db.removeLink(firstTrack, secondTrack)
                else:
                    self._db.removeLink(secondTrack, firstTrack)
            secondDialog.Destroy()
        firstDialog.Destroy()

    def _onScoreSliderMove(self, e):
        try:
            self._logger.debug("Score slider has been moved."\
                               +" Retrieving new score.")
            score = self._scoreSlider.GetValue()
            self._db.setScore(self._track, score)
            self.refreshSelectedTrack()
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            self._logger.error("No track selected.")
            return

    def setScoreSliderPosition(self, score):
        self._logger.debug("Setting score slider to "+str(score)+".")
        self._scoreSlider.SetValue(score)

    def _onRateUp(self, e):
        try:
            self._logger.debug("Increasing track's score by 1.")
            score = self._db.getScoreValue(self._track)
            if score != 10:
                self._db.setScore(self._track, score+1)
                self.refreshSelectedTrack()
            else:
                self._logger.warning("Track already has maximum score.")
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onRateDown(self, e):
        try:
            self._logger.debug("Decreasing track's score by 1.")
            score = self._db.getScoreValue(self._track)
            if score != -10:
                self._db.setScore(self._track, score-1)
                self.refreshSelectedTrack()
            else:
                self._logger.warning("Track already has minimum score.")
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onRate(self, e, score):
        try:
            self._logger.debug("Setting the track's score to "+str(score)+".")
            oldScore = self._db.getScoreValue(self._track)
            if score != oldScore:
                self._db.setScore(self._track, score)
                self.refreshSelectedTrack()
            else:
                self._logger.warning("Track already has that score!")
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onResetScore(self, e):
        try:
            self._logger.info("Resetting track's score.")
            self._db.setUnscored(self._track)
            self.refreshSelectedTrack()
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onExit(self, e):
        self._logger.debug("Exiting NQr.")
        self.Close(True)

    def _onClose(self, e):
        if self._trackMonitor:
            self._trackMonitor.abort()
        self.Destroy()

    def _onLaunchPlayer(self, e):
        self._player.launch()

    def _onExitPlayer(self, e):
        self._player.close()

    def _onNext(self, e):
        self._player.nextTrack()

    def _onPause(self, e):
        self._player.pause()

    def _onPlay(self, e):
        self._player.play()

    def _onPrevious(self, e):
        self._player.previousTrack()

    def _onStop(self, e):
        self._player.stop()

    def _onRequeue(self, e):
        try:
            self._logger.info("Requeueing track.")
            self._player.addTrack(self._track.getPath())
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute 'track'":
                raise err
            self._logger.error("No track selected.")
            return

## FIXME: toggle should be turned off when NQr is closed
    def _onToggleNQr(self, e=None):
        self._logger.debug("Toggling NQr.")
        if self.menuToggleNQr.IsChecked() == False:
            self.toggleNQr = False
            self._logger.info("Restoring shuffle status.")
            self._player.setShuffle(self._oldShuffleStatus)
            if self._oldPlaylist != None and self._restorePlaylist == True:
                self._player.loadPlaylist(self._oldPlaylist)
            self._logger.info("Enqueueing turned off.")
        elif self.menuToggleNQr.IsChecked() == True:
            self.toggleNQr = True
            self._logger.info("Storing shuffle status.")
            self._oldShuffleStatus = self._player.getShuffle()
            self._player.setShuffle(False)
            ## poss shouldn't restore the playlist ever?
            if self._restorePlaylist == True:
                self._oldPlaylist = self._player.savePlaylist()
            self._logger.info("Enqueueing turned on.")
            self.maintainPlaylist()

    def _onTrackChange(self, e):
        track = e.getTrack()
        self._db.addPlay(track)
        self.addTrack(track)
        self.maintainPlaylist()

    def maintainPlaylist(self):
        if self.toggleNQr == True:
            self._logger.debug("Maintaining playlist.")
            trackPosition = self._player.getCurrentTrackPos()
            if trackPosition > self._defaultTrackPosition:
                self._player.cropPlaylist(
                    trackPosition - self._defaultTrackPosition)
            playlistLength = self._player.getPlaylistLength()
            if playlistLength < self._defaultPlaylistLength:
                self.enqueueRandomTracks(
                    self._defaultPlaylistLength - playlistLength)

    def _onSelectTrack(self, e):
        self._logger.debug("Track has been selected.")
        self._logger.debug("Retrieving selected track's information.")
        self._trackID = e.GetData()
        self._index = e.GetIndex()
        self._track = self._trackFactory.getTrackFromID(self._db, self._trackID)
        self.populateDetails(self._track)
        self.setScoreSliderPosition(self._db.getScoreValue(self._track))

    def _onDeselectTrack(self, e):
        self._logger.debug("Track has been deselected.")
        self.clearDetails()
##        path = currentTrack()
##        self.populateDetails(path)

#### should queue the correct number of tracks
##    def _onEnqueueTracks(self, e=None):
##        track = self._randomizer.chooseTrack()
##        self.enqueueTrack(track)

    def addTrack(self, track):
        self.addTrackAtPos(track, 0)

    def addTrackAtPos(self, track, index):
        self._logger.debug("Adding track to track playlist.")
##        if IsCurrentTrack()==False:
        isScored = self._db.getIsScored(track)
        if isScored == False:
            score = "("+str(self._db.getScoreValue(track))+")"
            isScored = "+"
        else:
            score = str(self._db.getScore(track))
            isScored = ""
        lastPlayed = self._db.getLastPlayedLocalTime(track)
        ## should be time from last play?
        if lastPlayed == None:
            lastPlayed = "-"
        previous = track.getPreviousPlay()
        weight = track.getWeight()
        self._trackList.InsertStringItem(index, isScored)
        self._trackList.SetStringItem(index, 1, self._db.getArtist(track))
        self._trackList.SetStringItem(index, 2, self._db.getTitle(track))
        self._trackList.SetStringItem(index, 3, score)
        self._trackList.SetStringItem(index, 4, lastPlayed)
        if previous != None:
            self._trackList.SetStringItem(index, 5,
                                          RoughAge(time.time() - previous))
        if weight != None:
            self._trackList.SetStringItem(index, 6, str(weight))
        self._trackList.SetItemData(index, self._db.getTrackID(track))
        if self._index >= index:
            self._index += 1

    def enqueueTrack(self, track):
        path = track.getPath()
        self._logger.debug("Enqueueing \'"+path+"\'.")
        self._player.addTrack(path)
        self._db.addEnqueue(track)

## TODO: would be better for NQr to create a queue during idle time and pop from
##       it when enqueuing        
    def enqueueRandomTracks(self, number):
        try:
            self._logger.debug("Enqueueing "+str(number)+" random track"
                               + plural(number) + '.')
            exclude = self._player.getUnplayedTrackIDs(self._db)
            tracks = self._randomizer.chooseTracks(number, exclude)
## FIXME: untested!! poss most of the legwork should be done in db.getLinkIDs
            self._logger.debug("Checking tracks for links.")
            for track in tracks:
##                self.enqueueTrack(track)
                linkIDs = self._db.getLinkIDs(track)
                if linkIDs == None:
                    self.enqueueTrack(track)
                else:
                    originalLinkID = linkIDs[0]
                    (firstTrackID,
                     secondTrackID) = self._db.getLinkedTrackIDs(originalLinkID)
                    firstTrack = self._trackFactory.getTrackFromID(self._db,
                                                                  firstTrackID)
                    secondTrack = self._trackFactory.getTrackFromID(
                        self._db, secondTrackID)
                    trackQueue = deque([firstTrack, secondTrack])
##                    self.enqueueTrack(firstTrack)
##                    self.enqueueTrack(secondTrack)
                    linkIDs = self._db.getLinkIDs(firstTrack)
                    oldLinkIDs = originalLinkID
                    ## finds earlier tracks
                    while True:
                        for linkID in linkIDs:
                            if linkID not in oldLinkIDs:
                                (newTrackID,
                                 trackID) = self._db.getLinkedTrackIDs(linkID)
                                track = self._trackFactory.getTrackFromID(
                                    self._db, newTrackID)
                                trackQueue.appendleft(track)
                                oldLinkIDs = linkIDs
                                linkIDs = self._db.getLinkIDs(track)
                        if oldLinkIDs == linkIDs:
                                break
                    linkIDs = self._db.getLinkIDs(secondTrack)
                    oldLinkIDs = originalLinkID
                    ## finds later tracks
                    while True:
                        for linkID in linkIDs:
                            if linkID not in oldLinkIDs:
                                (trackID,
                                 newTrackID) = self._db.getLinkedTrackIDs(
                                     linkID)
                                track = self._trackFactory.getTrackFromID(
                                    self._db, newTrackID)
                                trackQueue.append(track)
                                oldLinkIDs = linkIDs
                                linkIDs = self._db.getLinkIDs(track)
                        if oldLinkIDs == linkIDs:
                                break
##                    oldTrackID = firstTrackID
##                    while linkIDs != None:
##                        for linkID in linkIDs:
##                            (trackID,
##                             newTrackID) = self._db.getLinkedTrackIDs(linkID)
##                            if trackID != oldTrackID:
##                                track = self._trackFactory.getTrackFromID(self._db,
##                                                                         newTrackID)
##                                trackQueue.append(track)
##                                oldTrackID = trackID
##                        linkIDs = self._db.getLinkIDs(track)
                    for track in trackQueue:
                        self.enqueueTrack(track)
##                    if secondLinkID != None:
##                        (secondTrackID,
##                         thirdTrackID) = self._db.getLinkedTrackIDs(secondLinkID)
##                        thirdTrack = self._trackFactory.getTrackFromID(self._db,
##                                                                      thirdTrackID)
##                        self.enqueueTrack(thirdTrack)
        except EmptyDatabaseError:
            self._logging.error("The database is empty.")
            return

    def refreshSelectedTrack(self):
        self._logger.debug("Refreshing selected track.")
        index = self._index
        self._trackList.DeleteItem(index)
        self.addTrackAtPos(self._track, index)
        self.selectTrack(index)

    def selectTrack(self, index):
        self._logger.debug("Selecting track in position "+str(index)+".")
        self._trackList.SetItemState(index, wx.LIST_STATE_SELECTED, -1)

## the first populateDetails seems to produce a larger font than subsequent
## calls in Mac OS
## TODO: should focus on the top of the details
    def populateDetails(self, track):
        self._logger.debug("Populating details panel.")
        lastPlayed = self._db.getLastPlayedLocalTime(track)
        ## should be time from last play?
        if lastPlayed == None:
            lastPlayed = "-"
        self.clearDetails()
        self.addDetail("Artist:   "+self._db.getArtist(track))
        self.addDetail("Title:   "+self._db.getTitle(track))
        self.addDetail("Track:   "+self._db.getTrackNumber(track)\
                       +"       Album:   "+self._db.getAlbum(track))
        self.addDetail("Score:   "+str(self._db.getScore(track)))
        self.addDetail("Play Count:   "+str(self._db.getPlayCount(track))\
                       +"       Last Played:   "+lastPlayed)
        self.addDetail("Filetrack:   "+self._db.getPath(track))

    def addDetail(self, detail):
        self._details.AppendText(detail+"\n")

    def clearDetails(self):
        self._logger.debug("Clearing details panel.")
        self._details.Clear()
