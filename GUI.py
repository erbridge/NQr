## GUI
##
## TODO: add library viewer with scoring, queueing and search funcionality using
##       splitter window: top left - artist, top right - album, centre - tracks,
##       bottom - details
## TODO: debug message window with levels of messages (basic score up/down
##       etc for users and more complex for devs) using "logging" module?
## TODO: add delete file/directory menus, with confirmation?
## TODO: add support for mulitple track selections
## TODO: display unplayed tracks with option to remove and rearrange playlist
## TODO: when NQr queueing off, change trackList behaviour to only show played
##       tracks, not to represent unplayed tracks, or show only 3 future tracks?
## TODO: implement ignoring of tracks played not in database
##       (option already created)
## TODO: make keyboard shortcuts make sense for Macs
## TODO: add clear cache menu option (to force metadata change updates)?
## TODO: make details resizable (splitter window?)
## TODO: add tags to right click menu
## TODO: gives scores a drop down menu in the track list.
## TODO: add "select current track" keyboard shortcut and menu item
##
## FIXME: track refreshes should only refresh things that will change - poss no
##        longer necessary?
## FIXME: reduce processing - e.g. check tracks less often (if doing this
##        change delay in _onNext() etc.)

#from collections import deque
import ConfigParser
from Errors import NoTrackError, EmptyDatabaseError
import Events
import os
import sys
import threading
import time
from Time import roughAge
from Util import MultiCompletion, ErrorCompletion, doNothing, RedirectErr,\
    RedirectOut, plural, BasePrefsPage, validateDirectory, validateNumeric, wx

##import wx.lib.agw.multidirdialog as wxMDD

## must be aborted when closing!
class TrackMonitor(threading.Thread):
    def __init__(self, window, db, player, trackFactory, loggerFactory):
        threading.Thread.__init__(self, name="Track Monitor")
#        self.setDaemon(True)
        self._window = window
        self._db = db
        self._player = player
        self._trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.TrackMonitor", "debug")
        self._abortFlag = False
        self._enqueueing = False
        self.start()

## poss should use position rather than filename?
## FIXME: sometimes gets the wrong track if skipped too fast: should return the
##        path with the event (poss fixed). Also happens if track changes while
##        scoring
    def run(self):
        logging = True
        try:
            currentTrackPath = self._player.getCurrentTrackPath(logging=logging)
        except NoTrackError:
            currentTrackPath = None
        while True:
            time.sleep(.5)
            if self._abortFlag == True:
                self._logger.info("Stopping track monitor.")
                return
            try:
                newTrackPath = self._player.getCurrentTrackPath(logging=logging)
                logging = False
            except NoTrackError:
                newTrackPath = None
            if newTrackPath != currentTrackPath:
                self._logger.debug("Track has changed.")
                currentTrackPath = newTrackPath
                wx.PostEvent(self._window,
                             Events.TrackChangeEvent(self._db,
                                                     self._trackFactory,
                                                     currentTrackPath))
                logging = True
                self._enqueueing = True
            if self._enqueueing == False\
                    and self._player.hasNextTrack() == False:
                self._logger.info("End of playlist reached.")
                wx.PostEvent(self._window, Events.NoNextTrackEvent())
            if self._abortFlag == True:
                self._logger.info("Stopping track monitor.")
                return

    def abort(self):
        self._abortFlag = True
    
    def setEnqueueing(self, status):
        self._enqueueing = status

class SocketMonitor(threading.Thread): # FIXME: poss doesn't exit
    def __init__(self, window, socket, loggerFactory):
        threading.Thread.__init__(self, name="Socket Monitor")
#        self.setDaemon(True)
        self._window = window
        self._socket = socket
        self._logger = loggerFactory.getLogger("NQr.SocketMonitor", "debug")
        self._connections = []
        self.start()

    def run(self):
        self._socket.listen(5) # FIXME: how many can it listen to?
        while True:
            # FIXME: has windows permission issues...
            (conn, address) = self._socket.accept()
            self._logger.debug("Starting connection ("+address[0]+":"\
                               +str(address[1])+") monitor.")
            self._connections.append(ConnectionMonitor(self._window, conn,
                                                       address, self._logger))
                
    def abort(self):
        self._logger.debug("Stopping socket monitor.")
        for connection in self._connections: # FIXME: is this necessary?
            connection.abort()
        self._socket.close()
        
class ConnectionMonitor(threading.Thread): # FIXME: poss doesn't exit
    def __init__(self, window, connection, address, logger):
        self._address = address[0]+":"+str(address[1])
        threading.Thread.__init__(self, name=self._address+" Monitor")
#        self.setDaemon(True)
        self._window = window
        self._conn = connection
        self._logger = logger
        self.start()
    
    def run(self):
        while True:
            try:
                message = self._recieve()
            except RuntimeError as err:
                if str(err) != "socket connection broken":
                    raise err
                self._logger.debug("Stopping connection ("+self._address\
                                   +") monitor.")
                self._conn.close()
                break
            if message == "ATTEND\n":
                wx.PostEvent(self._window, Events.RequestAttentionEvent())
            elif message == "PAUSE\n":
                wx.PostEvent(self._window, Events.PauseEvent())
            elif message == "PLAY\n":
                wx.PostEvent(self._window, Events.PlayEvent())
            elif message == "STOP\n":
                wx.PostEvent(self._window, Events.StopEvent())
            elif message == "NEXT\n":
                wx.PostEvent(self._window, Events.NextEvent())
            elif message == "PREV\n":
                wx.PostEvent(self._window, Events.PreviousEvent())
            elif message == "RATEUP\n":
                wx.PostEvent(self._window, Events.RateUpEvent())
            elif message == "RATEDOWN\n":
                wx.PostEvent(self._window, Events.RateDownEvent())
                               
    def _recieve(self):
        byte = ""
        message = ""
        while byte != "\n":
            byte = self._conn.recv(1)
            if byte == "":
                raise RuntimeError("socket connection broken")
            message += byte
        return message
        
    def abort(self): # FIXME: does this work?
        self._logger.debug("Stopping connection ("+self._address+") monitor.")
        self._conn.close()
        
class MainWindow(wx.Frame):
    def __init__(self, parent, db, randomizer, player, trackFactory, system,
                 loggerFactory, prefsFactory, configParser, socket, title,
                 defaultRestorePlaylist, defaultEnqueueOnStartup,
                 defaultRescanOnStartup, defaultPlaylistLength,
                 defaultPlayDelay, defaultIgnore, defaultInactivityTime=30000,
                 wildcards="Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|"\
                    +"*.*", defaultDefaultDirectory="",
                defaultHaveLogPanel=True):
        self._ID_ARTIST = wx.NewId()
        self._ID_TRACK = wx.NewId()
        self._ID_SCORE = wx.NewId()
        self._ID_LASTPLAYED = wx.NewId()
        self._ID_PREVIOUSPLAY = wx.NewId()
        self._ID_WEIGHT = wx.NewId()
        self._ID_SCORESLIDER = wx.NewId()
        self._ID_TRACKLIST = wx.NewId()
        self._ID_DETAILS = wx.NewId()
        self._ID_TAGS = wx.NewId()
        self._ID_NOWPLAYING = wx.NewId()
        self._ID_ADDDIRECTORY = wx.NewId()
        self._ID_ADDFILE = wx.NewId()
        self._ID_PREFS = wx.NewId()
        self._ID_TOGGLENQR = wx.NewId()
        self._ID_PLAYTIMER = wx.NewId()
        self._ID_INACTIVITYTIMER = wx.NewId()
        self._ID_REFRESHTIMER = wx.NewId()
        self._ID_PLAY = wx.NewId()
        self._ID_STOP = wx.NewId()
        self._ID_PAUSE = wx.NewId()
        self._ID_PREV = wx.NewId()
        self._ID_NEXT = wx.NewId()
        self._ID_SELECTCURRENT = wx.NewId()
        self._ID_RATEUP = wx.NewId()
        self._ID_RATEDOWN = wx.NewId()

        self._db = db
        self._randomizer = randomizer
        self._player = player
        self._trackFactory = trackFactory
        self._system = system
        self._loggerFactory = loggerFactory
        self._logger = loggerFactory.getLogger("NQr.GUI", "debug")
        self._prefsFactory = prefsFactory
        self._configParser = configParser
        self._restorePlaylist = defaultRestorePlaylist
        self._enqueueOnStartup = defaultEnqueueOnStartup
        self._defaultRescanOnStartup = defaultRescanOnStartup
        self._defaultPlaylistLength = defaultPlaylistLength
        self._defaultTrackPosition = int(round(self._defaultPlaylistLength/2))
        self._defaultPlayDelay = defaultPlayDelay
        self._defaultInactivityTime = defaultInactivityTime
        self._wildcards = wildcards
        self._defaultDefaultDirectory = defaultDefaultDirectory
        self._defaultIgnore = defaultIgnore
        self._defaultHaveLogPanel = defaultHaveLogPanel
        self.loadSettings()

        self._index = None
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._hotKeys = []
        self._enqueueing = False

        wx.Frame.__init__(self, parent, title=title)

        self._logger.debug("Creating status bar.")
        self.CreateStatusBar()
        self._initCreateMenuBar()
        self._initCreateTrackRightClickMenu()
        self._initCreateMainPanel()

        self._logger.debug("Creating play delay timer.")
        self._playTimer = wx.Timer(self, self._ID_PLAYTIMER)

        self._logger.debug("Creating and starting inactivity timer.")
        self._inactivityTimer = wx.Timer(self, self._ID_INACTIVITYTIMER)
        self._inactivityTimer.Start(self._inactivityTime, oneShot=False)
        self._addHotKey(None, "T", self._ID_INACTIVITYTIMER)

        self._logger.debug("Creating and starting track list refresh timer.")
        self._refreshTimer = wx.Timer(self, self._ID_REFRESHTIMER)
        self._refreshTimer.Start(1000, oneShot=False)
        
        self._logger.info("Starting track monitor.")
        self._trackMonitor = TrackMonitor(self, self._db, self._player,
                                          self._trackFactory, loggerFactory)
        
        self._logger.debug("Starting socket monitor.")
        self._socketMonitor = SocketMonitor(self, socket, loggerFactory)

        wx.EVT_TIMER(self, self._ID_PLAYTIMER, self._onPlayTimerDing)
        wx.EVT_TIMER(self, self._ID_INACTIVITYTIMER,
                     self._onInactivityTimerDing)
        wx.EVT_TIMER(self, self._ID_REFRESHTIMER, self._onRefreshTimerDing)
        
        Events.EVT_TRACK_CHANGE(self, self._onTrackChange)
        Events.EVT_NO_NEXT_TRACK(self, self._onNoNextTrack)
        Events.EVT_REQUEST_ATTENTION(self, self._onRequestAttention)
        Events.EVT_PAUSE(self, self._onPause)
        Events.EVT_PLAY(self, self._onPlay)
        Events.EVT_STOP(self, self._onStop)
        Events.EVT_NEXT(self, self._onNext)
        Events.EVT_PREV(self, self._onPrevious)
        Events.EVT_RATE_UP(self, self._onRateUp)
        Events.EVT_RATE_DOWN(self, self._onRateDown)
        
        self.Bind(wx.EVT_CLOSE, self._onClose, self)

        if self._restorePlaylist == True:
            self._oldPlaylist = None

        if self._enqueueOnStartup == True:
            self._optionsMenu.Check(self._ID_TOGGLENQR, True)
            self._onToggleNQr()

        self._initCreateHotKeyTable()
        self._logger.debug("Drawing main window.")
        self.Show(True) ## FIXME: make window draw fully before queueing?
        
        self.maintainPlaylist()

        if self._rescanOnStartup == True:
            self._onRescan()

    def _initCreateMenuBar(self):
        self._logger.debug("Creating menu bar.")
        self._initCreateFileMenu()
        self._initCreateRateMenu()
        self._initCreatePlayerMenu()
        self._initCreateTagMenu()
        self._initCreateOptionsMenu()

        menuBar = wx.MenuBar()
        menuBar.Append(self._fileMenu, "&File")
        menuBar.Append(self._playerMenu, "&Player")
        menuBar.Append(self._tagMenu, "&Tags")
        menuBar.Append(self._optionsMenu, "&Options")

        self.SetMenuBar(menuBar)

    def _initCreateFileMenu(self):
        self._logger.debug("Creating file menu.")
        self._fileMenu = wx.Menu()
        menuAbout = self._fileMenu.Append(
            wx.ID_ABOUT, "&About NQr\tF1", " Information about NQr")
        
        self._addHotKey(None, wx.WXK_F1, wx.ID_ABOUT)
        
        self._fileMenu.AppendSeparator()
        menuAddFile = self._fileMenu.Append(
            self._ID_ADDFILE, "Add &File...\tCtrl+F",
            " Add a file to the library")
        
        self._addHotKey("ctrl", "F", self._ID_ADDFILE)
        
        menuAddDirectory = self._fileMenu.Append(
            self._ID_ADDDIRECTORY, "Add &Directory...\tCtrl+D",
            " Add a directory to the library and watch list")
        
        self._addHotKey("ctrl", "D", self._ID_ADDDIRECTORY)
        
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
            -1, "Remo&ve Link...", " Remove the link between two tracks")
        self._fileMenu.AppendSeparator()
        menuExit = self._fileMenu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q",
                                         " Terminate NQr")
        
        self._addHotKey("ctrl", "Q", wx.ID_EXIT)

        self.Bind(wx.EVT_MENU, self._onAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self._onAddFile, menuAddFile)
        self.Bind(wx.EVT_MENU, self._onAddDirectory, menuAddDirectory)
        self.Bind(wx.EVT_MENU, self._onAddDirectoryOnce, menuAddDirectoryOnce)
        self.Bind(wx.EVT_MENU, self._onRemoveDirectory, menuRemoveDirectory)
        self.Bind(wx.EVT_MENU, self._onLinkTracks, menuLinkTracks)
        self.Bind(wx.EVT_MENU, self._onRemoveLink, menuRemoveLink)
        self.Bind(wx.EVT_MENU, self._onExit, menuExit)

    def _initCreateRateMenu(self):
        self._logger.debug("Creating rate menu.")
        self._rateMenu = wx.Menu()
        self._populateRateMenu(self._rateMenu)

    ## TODO: change up in "Rate Up" to an arrow
    def _initCreatePlayerMenu(self):
        self._logger.debug("Creating player menu.")
        self._playerMenu = wx.Menu()
        menuPlay = self._playerMenu.Append(self._ID_PLAY, "&Play\tX",
                                           " Play or restart the current track")
        
        self._addHotKey(None, "X", self._ID_PLAY)
        
        menuPause = self._playerMenu.Append(
            self._ID_PAUSE, "P&ause\tC", " Pause or resume the current track")
        
        self._addHotKey(None, "C", self._ID_PAUSE)
        
        menuNext = self._playerMenu.Append(self._ID_NEXT, "&Next Track\tB",
                                           " Play the next track")
        
        self._addHotKey(None, "B", self._ID_NEXT)
        
        menuPrevious = self._playerMenu.Append(self._ID_PREV,
                                               "Pre&vious Track\tZ",
                                               " Play the previous track")
        
        self._addHotKey(None, "Z", self._ID_PREV)
        
        menuStop = self._playerMenu.Append(self._ID_STOP, "&Stop\tV",
                                           " Stop the current track")
        
        self._addHotKey(None, "V", self._ID_STOP)
        
        self._playerMenu.AppendSeparator()
        menuRateUp = self._playerMenu.Append(
            self._ID_RATEUP, "Rate &Up\tCtrl+PgUp",
            " Increase the score of the selected track by one")
        
        self._addHotKey("ctrl", wx.WXK_PAGEUP, self._ID_PLAY)
        
        menuRateDown = self._playerMenu.Append(
            self._ID_RATEDOWN, "Rate &Down\tCtrl+PgDn",
            " Decrease the score of the selected track by one")
        
        self._addHotKey("ctrl", wx.WXK_PAGEDOWN, self._ID_PLAY)
        
        self._playerMenu.AppendMenu(-1, "&Rate", self._rateMenu)
        self._playerMenu.AppendSeparator()
        menuRequeue = self._playerMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
        menuRequeueAndPlay = self._playerMenu.Append(
            -1, "Requeue and &Play Track",
            " Add the selected track to the playlist and play it")
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
        self.Bind(wx.EVT_MENU, self._onRequeueAndPlay, menuRequeueAndPlay)
        self.Bind(wx.EVT_MENU, self._onResetScore, menuResetScore)
        self.Bind(wx.EVT_MENU, self._onLaunchPlayer, menuLaunchPlayer)
        self.Bind(wx.EVT_MENU, self._onExitPlayer, menuExitPlayer)

    def _getAllTagsCompletion(self, tags):
        self._allTags = {}
        for tag in tags:
            tagID = wx.NewId()
            self._allTags[tagID] = tag
            tagMenu = self._tagMenu.AppendCheckItem(tagID, tag,
                                                    " Tag track with "+tag)

            self.Bind(wx.EVT_MENU, self._onTag, tagMenu)
            
    def _initCreateTagMenu(self):
        self._logger.debug("Creating tag menu.")
        self._tagMenu = wx.Menu()
        newTagMenu = self._tagMenu.Append(
            -1, "&New...", " Create new tag and tag track with it")
        self._tagMenu.AppendSeparator()
        
        self._db.getAllTagNames(
            lambda tags: self._getAllTagsCompletion(tags), priority=1)

        self.Bind(wx.EVT_MENU, self._onNewTag, newTagMenu)

    def _initCreateOptionsMenu(self):
        self._logger.debug("Creating options menu.")
        self._optionsMenu = wx.Menu()
        menuPrefs = self._optionsMenu.Append(self._ID_PREFS,
                                             "&Preferences...\tCtrl+P",
                                             " Change NQr's settings")

        self._addHotKey("ctrl", "P", self._ID_PREFS)
        
        menuRescan = self._optionsMenu.Append(
            -1, "&Rescan Library",
            " Search previously added directories for new files")
        self._optionsMenu.AppendSeparator()
        self.menuToggleNQr = self._optionsMenu.AppendCheckItem(
            self._ID_TOGGLENQR, "En&queue with NQr\tCtrl+E",
            " Use NQr to enqueue tracks")
        
        self._addHotKey("ctrl", "E", self._ID_TOGGLENQR)

        self.Bind(wx.EVT_MENU, self._onPrefs, menuPrefs)
        self.Bind(wx.EVT_MENU, self._onRescan, menuRescan)
        self.Bind(wx.EVT_MENU, self._onToggleNQr, self.menuToggleNQr)

    def _initCreateRightClickRateMenu(self):
        self._logger.debug("Creating rate menu.")
        self._rightClickRateMenu = wx.Menu()
        self._populateRateMenu(self._rightClickRateMenu)

    def _initCreateTrackRightClickMenu(self):
        self._logger.debug("Creating track right click menu.")
        self._initCreateRightClickRateMenu()

        self._trackRightClickMenu = wx.Menu()
        menuTrackRightClickRateUp = self._trackRightClickMenu.Append(
            -1, "Rate &Up", " Increase the score of the current track by one")
        menuTrackRightClickRateDown = self._trackRightClickMenu.Append(
            -1, "Rate &Down", " Decrease the score of the current track by one")
        self._trackRightClickMenu.AppendMenu(-1, "&Rate",
                                             self._rightClickRateMenu)
        self._trackRightClickMenu.AppendSeparator()
        menuTrackRightClickRequeue = self._trackRightClickMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
        menuTrackRightClickRequeueAndPlay = self._trackRightClickMenu.Append(
            -1, "Requeue and &Play Track",
            " Add the selected track to the playlist and play it")
        self._trackRightClickMenu.AppendSeparator()
        menuTrackRightClickResetScore = self._trackRightClickMenu.Append(
            -1, "Reset Sc&ore", " Reset the score of the current track")

        self.Bind(wx.EVT_MENU, self._onRateUp, menuTrackRightClickRateUp)
        self.Bind(wx.EVT_MENU, self._onRateDown, menuTrackRightClickRateDown)
        self.Bind(wx.EVT_MENU, self._onRequeue, menuTrackRightClickRequeue)
        self.Bind(wx.EVT_MENU, self._onRequeueAndPlay,
                  menuTrackRightClickRequeueAndPlay)
        self.Bind(wx.EVT_MENU, self._onResetScore,
                  menuTrackRightClickResetScore)

    def _initCreateMainPanel(self):
        self._panel = wx.Panel(self)
        self._initCreatePlayerControls()
        self._initCreateDetails()
        self._initCreateTrackSizer()

        self._mainSizer = wx.BoxSizer(wx.VERTICAL)
        self._mainSizer.Add(self._playerControls, 0, wx.EXPAND)
        self._mainSizer.Add(self._trackSizer, 1,
                            wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, 4)
        self._mainSizer.Add(self._details, 0, wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT,
                            3)
        if self._haveLogPanel == True:
            self._initCreateLogPanel()
            self._mainSizer.Add(self._logPanel, 0,
                                wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, 3)

        self._panel.SetSizerAndFit(self._mainSizer)
        self._panel.SetAutoLayout(True)
        self._mainSizer.Fit(self)
        self.SetSizeHints(430, self.GetSize().y);

## TODO: use svg or gd to create button images via wx.Bitmap and wx.BitmapButton
    def _initCreatePlayerControls(self):
        self._logger.debug("Creating player controls.")
        self._playerControls = wx.Panel(self._panel)
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
        self._details = wx.TextCtrl(self._panel, self._ID_DETAILS,
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
        self._trackList = wx.ListCtrl(self._panel, self._ID_TRACKLIST,
                                      style=wx.LC_REPORT|wx.LC_VRULES|
                                      wx.LC_SINGLE_SEL, size=(656,-1))
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
                                     format=wx.LIST_FORMAT_CENTER, width=80)


        try:
            self._logger.debug("Adding current track to track playlist.")
            currentTrackPath = self._player.getCurrentTrackPath()
            currentTrack = self._trackFactory.getTrackFromPath(self._db,
                                                               currentTrackPath)
            multicompletion = MultiCompletion(
                2, lambda currentTrackID, oldTrackID,\
                    currentTrack=currentTrack: self._compareTracksCompletion(
                        currentTrack, currentTrackID, oldTrackID))
            currentTrack.getID(lambda trackID, multicompletion=multicompletion:\
                                    multicompletion.put(0, trackID),
                               priority=1)
            errcompletion = ErrorCompletion(EmptyDatabaseError,
                                            lambda: doNothing())
            self._db.getLastPlayedTrackID(
                lambda trackID, multicompletion=multicompletion:\
                    multicompletion.put(1, trackID), errcompletion, priority=1)
#            try:
#                if currentTrackID != self._db.getLastPlayedTrackID():
#                    self._logger.debug("Adding play for current track.")
#                    currentTrack.addPlay()
#            except EmptyDatabaseError:
#                pass
            self._db.getLastPlayedInSeconds(
                currentTrack,
                lambda previous, currentTrack=currentTrack:\
                    currentTrack.setPreviousPlay(previous), priority=1)
            self.addTrack(currentTrack, select=True)
        except NoTrackError:
            pass

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onSelectTrack,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._onDeselectTrack,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._onTrackRightClick,
                  self._trackList)
        
    def _compareTracksCompletion(self, firstTrack, firstTrackID, secondTrackID):
        if firstTrackID != secondTrackID:
            self._logger.debug("Adding play for current track.")
            firstTrack.addPlay()

    def _initCreateScoreSlider(self):
        self._logger.debug("Creating score slider.")
        if self._system == 'FreeBSD':
            self._scoreSlider = wx.Slider(self._panel, self._ID_SCORESLIDER, 0,
                                          -10, 10, style=wx.SL_VERTICAL|
                                          wx.SL_LABELS|wx.SL_INVERSE)
        else:
            self._scoreSlider = wx.Slider(self._panel, self._ID_SCORESLIDER, 0,
                                          -10, 10, style=wx.SL_RIGHT|
                                          wx.SL_LABELS|wx.SL_INVERSE)

        self.Bind(wx.EVT_SCROLL_CHANGED, self._onScoreSliderMove,
                  self._scoreSlider)
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self._onScoreSliderMove,
                  self._scoreSlider)

    def _initCreateLogPanel(self):
        self._logger.debug("Creating log panel.")
        self._logPanel = wx.TextCtrl(self._panel, -1, style=wx.TE_READONLY|
                                     wx.TE_MULTILINE|wx.TE_DONTWRAP,
                                     size=(-1,100))

        font = wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL)
        self._logPanel.SetFont(font)

        # FIXME: sometimes raises exception when printing to out at the same
        #        time as printing to err
        self._redirectOut = RedirectOut(self._logPanel, sys.stdout)
        self._redirectErr = RedirectErr(self._logPanel, sys.stderr)
        sys.stdout = self._redirectOut
        sys.stderr = self._redirectErr
        
    def _initCreateHotKeyTable(self):
        self._hotKeyTable = wx.AcceleratorTable(self._hotKeys)
        self.SetAcceleratorTable(self._hotKeyTable)

    def _addHotKey(self, modifier, key, targetID):
        if modifier == "ctrl":
            flag = wx.ACCEL_CTRL
        elif modifier == "alt":
            flag = wx.ACCEL_ALT
        elif modifier == "shift":
            flag = wx.ACCEL_SHIFT
        else:
            flag = wx.ACCEL_NORMAL
        if isinstance(key, str):
            keyCode = ord(key)
        else:
            keyCode = key
        
        self._hotKeys.append((flag, keyCode, targetID))
        
    def _populateRateMenu(self, menu):
        scores = range(10, -11, -1)
        for score in scores:
            menuItem = menu.Append(-1, "Rate as "+str(score),
                                   " Set the score of the selected track to "\
                                   +str(score))

            self.Bind(wx.EVT_MENU, lambda e, score=score:
                      self._onRate(e, score), menuItem)
            
    def _onTrackRightClick(self, e):
        self.resetInactivityTimer()
        self._logger.debug("Popping up track right click menu.")
        point = e.GetPoint()

        self.PopupMenu(self._trackRightClickMenu, point)
        
    def _onAboutCompletion(self, number, numberUnplayed, totals):
        self._logger.debug("Opening about dialog.")
        text = "For all your NQing needs\n\n"
        text += str(number)+" tracks in library:\n"
        
        scoreTableTitle = "score\t|       number\n\t|\n"
        scoreTable = ""
        numberScored = 0
        for total in totals:
            numberScored += total[1]
            score = str(total[0])
            if score[0] != "-":
                score = " "+score
            scoreTable = "  "+score+"\t|            "+str(total[1])+"\n"\
                +scoreTable
            
        text += "- "+str(number - numberScored)+" unscored\n"
        text += "- "+str(numberUnplayed)+" unplayed\n\n"
        text += scoreTableTitle+scoreTable

        dialog = wx.MessageDialog(self, text, "NQr", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def _onAbout(self, e):
        multicompletion = MultiCompletion(
            3, lambda number, numberUnplayed, totals:\
                self._onAboutCompletion(number, numberUnplayed, totals))
        self._db.getNumberOfTracks(
            lambda number, multicompletion=multicompletion: multicompletion.put(
                0, number), priority=1)
        self._db.getNumberOfUnplayedTracks(
            lambda numberUnplayed, multicompletion=multicompletion:\
                multicompletion.put(1, numberUnplayed), priority=1)
        self._db.getScoreTotals(lambda totals, multicompletion=multicompletion:\
                                    multicompletion.put(2, totals), priority=1)
        
    def _onPrefs(self, e):
        self._logger.debug("Opening preferences window.")
        self._prefsWindow = self._prefsFactory.getPrefsWindow(self)
        self._prefsWindow.Show()

## TODO: change buttons to say "import" rather than "open"/"choose"
    def _onAddFile(self, e):
        self._logger.debug("Opening add file dialog.")
        dialog = wx.FileDialog(
            self, "Choose some files...", self._defaultDirectory, "",
            self._wildcards, wx.FD_OPEN|wx.FD_MULTIPLE|wx.FD_CHANGE_DIR)
        if dialog.ShowModal() == wx.ID_OK:
            paths = dialog.GetPaths()
            for path in paths:
                self._db.addTrack(path)
        dialog.Destroy()

    def _onAddDirectory(self, e):
        self._logger.debug("Opening add directory dialog.")
        if self._system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory...",
                                  self._defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory...",
                                  self._defaultDirectory, wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._db.addDirectory(path)
        dialog.Destroy()

    def _onAddDirectoryOnce(self, e):
        self._logger.debug("Opening add directory once dialog.")
        if self._system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory...",
                                  self._defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory...",
                                  self._defaultDirectory, wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._db.addDirectoryNoWatch(path)
##        dialog = wxMDD.MultiDirDialog(self, title="Choose some directories...",
##                                      defaultPath=self._defaultDirectory,
##                                      agwStyle=wxMDD.DD_DIR_MUST_EXIST|
##                                      wxMDD.DD_MULTIPLE)
##        if dialog.ShowModal() == wx.ID_OK:
##            paths = dialog.GetPaths()
##            for path in paths:
##                self._db.addDirectoryNoWatch(path)
        dialog.Destroy()

    def _onRemoveDirectory(self, e):
        self._logger.debug("Opening remove directory dialog.")
        if self._system == 'FreeBSD':
            dialog = wx.DirDialog(self, "Choose a directory to remove...",
                                  self._defaultDirectory)
        else:
            dialog = wx.DirDialog(self, "Choose a directory to remove...",
                                  self._defaultDirectory, wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self._db.removeDirectory(path)
        dialog.Destroy()

    def _onRescan(self, e=None):
        self._logger.debug("Rescanning watch list for new files.")
        self._db.rescanDirectories()

## TODO: make linking files simpler, poss side by side selection or order
##       sensitive multiple selection?
    def _onLinkTracks(self, e):
        self._logger.debug("Opening add link dialogs.")
        self._logger.debug("Opening first file dialog.")
        firstDialog = wx.FileDialog(
            self, "Choose the first file...", self._defaultDirectory, "",
            self._wildcards, wx.FD_OPEN|wx.FD_CHANGE_DIR)
        if firstDialog.ShowModal() == wx.ID_OK:
            firstPath = firstDialog.GetPath()
            firstTrack = self._trackFactory.getTrackFromPath(self._db,
                                                             firstPath)
            self._logger.debug("Opening second file dialog.")
            directory = os.path.dirname(firstPath)
            secondDialog = wx.FileDialog(
                self, "Choose the second file...", directory, "",
                self._wildcards, wx.FD_OPEN|wx.FD_CHANGE_DIR)
            if secondDialog.ShowModal() == wx.ID_OK:
                secondPath = secondDialog.GetPath()
                secondTrack = self._trackFactory.getTrackFromPath(self._db,
                                                                  secondPath)
                self._db.addLink(firstTrack, secondTrack)
            secondDialog.Destroy()
        firstDialog.Destroy()
        
    def _onRemoveLinkCompletion(self, linkID, firstTrack, secondTrack):
        if linkID != None:
            self._db.removeLink(firstTrack, secondTrack)
        else:
            self._db.removeLink(secondTrack, firstTrack)
            
## TODO: make removing links select from a list of current links
    def _onRemoveLink(self, e):
        self._logger.debug("Opening remove link dialog.")
        self._logger.debug("Opening first file dialog.")
        firstDialog = wx.FileDialog(
            self, "Choose the first file...", self._defaultDirectory, "",
            self._wildcards, wx.FD_OPEN|wx.FD_CHANGE_DIR)
        if firstDialog.ShowModal() == wx.ID_OK:
            firstPath = firstDialog.GetPath()
            firstTrack = self._trackFactory.getTrackFromPath(self._db,
                                                             firstPath)
            self._logger.debug("Opening second file dialog.")
            directory = os.path.dirname(firstPath)
            secondDialog = wx.FileDialog(
                self, "Choose the second file...", directory, "",
                self._wildcards, wx.FD_OPEN|wx.FD_CHANGE_DIR
                )
            if secondDialog.ShowModal() == wx.ID_OK:
                secondPath = secondDialog.GetPath()
                secondTrack = self._trackFactory.getTrackFromPath(self._db,
                                                                  secondPath)
                self._db.getLinkID(
                    firstTrack, secondTrack,
                    lambda linkID, firstTrack=firstTrack,\
                        secondTrack=secondTrack: self._onRemoveLinkCompletion(
                            linkID, firstTrack, secondTrack))
            secondDialog.Destroy()
        firstDialog.Destroy()
        
    def _onScoreChangeCompletion(self, track, oldScore, newScore,
                                 warnings=False):
        if oldScore != newScore:
            self._logger.debug("Setting the track's score to "+str(newScore)\
                               +".")
            track.setScore(newScore)
            self.refreshSelectedTrackScore()
        elif warnings == True:
            self._logger.warning("Track already has that score!")

    def _onScoreSliderMove(self, e):
        self.resetInactivityTimer()
        try:
            self._logger.debug("Score slider has been moved."\
                               +" Retrieving new score.")
            score = self._scoreSlider.GetValue()
            self._track.getScore(
                lambda oldScore, track=self._track, score=score:\
                    self._onScoreChangeCompletion(track, oldScore, score),
                priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def setScoreSliderPosition(self, score):
        self._logger.debug("Setting score slider to "+str(score)+".")
        self._scoreSlider.SetValue(score)
        
    def _onRateUpCompletion(self, track, score):
        if score != 10:
            self._logger.debug("Increasing track's score by 1.")
            track.setScore(score+1)
            self.refreshSelectedTrackScore()
        else:
            self._logger.warning("Track already has maximum score.")

    def _onRateUp(self, e):
        self.resetInactivityTimer()
        try:
            self._track.getScoreValue(
                lambda score, track=self._track: self._onRateUpCompletion(
                    track, score), priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return
        
    def _onRateDownCompletion(self, track, score):
        if score != -10:
            self._logger.debug("Decreasing track's score by 1.")
            track.setScore(score-1)
            self.refreshSelectedTrackScore()
        else:
            self._logger.warning("Track already has minimum score.")

    def _onRateDown(self, e):
        self.resetInactivityTimer()
        try:
            self._track.getScoreValue(
                lambda score, track=self._track: self._onRateDownCompletion(
                    track, score), priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onRate(self, e, score):
        self.resetInactivityTimer()
        try:
            self._track.getScore(
                lambda oldScore, track=self._track, score=score:\
                    self._onScoreChangeCompletion(track, oldScore, score,
                                                  warnings=True), priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onResetScore(self, e):
        self.resetInactivityTimer()
        try:
            self._logger.info("Resetting track's score.")
            self._track.setUnscored()
            self.refreshSelectedTrackScore()
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onTag(self, e):
        self.resetInactivityTimer()
        try:
            tagID = e.GetId()
            if self._tagMenu.IsChecked(tagID) == True: # since clicking checks
                self.setTag(self._track, tagID)
            else:
                self.unsetTag(self._track, tagID)
            self.populateDetails(self._track)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onNewTag(self, e):
        try:
            self._inactivityTimer.Stop()
            self._logger.info("Creating tag.")
            dialog = wx.TextEntryDialog(self, "Tag name:", "New Tag...")
            if dialog.ShowModal() == wx.ID_OK:
                tag = unicode(dialog.GetValue())
                self._db.addTagName(tag)
                tagID = wx.NewId()
                self._allTags[tagID] = tag
                tagMenu = self._tagMenu.AppendCheckItem(
                    tagID, tag, " Tag track with "+tag)
                self.setTag(self._track, tagID)
                self.populateDetails(self._track)

                self.Bind(wx.EVT_MENU, self._onTag, tagMenu)
            dialog.Destroy()
            self.resetInactivityTimer()
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            self.resetInactivityTimer()
            return

    def _onExit(self, e):
        self._logger.debug("Exiting NQr.")
        self.Close(True)

    def _onClose(self, e):
        self._optionsMenu.Check(self._ID_TOGGLENQR, False)
        if self._trackMonitor:
            self._trackMonitor.abort()
        self._inactivityTimer.Stop()
        self._refreshTimer.Stop()
        self._db.abort()
        if self._haveLogPanel == True:
            sys.stdout = self._stdout
            sys.stderr = self._stderr
            self._loggerFactory.refreshStreamHandler()
        self._socketMonitor.abort()
        
        self.Destroy()

    def _onLaunchPlayer(self, e):
        self._player.launch()

    def _onExitPlayer(self, e):
        self._player.close()

    def _onNext(self, e):
        self._player.nextTrack()
        self.resetInactivityTimer(1000)

    def _onPause(self, e):
        self._player.pause()
        self.resetInactivityTimer(1)

    def _onPlay(self, e):
        self._player.play()
        self.resetInactivityTimer(1)

    def _onPrevious(self, e):
        self._player.previousTrack()
        self.resetInactivityTimer(1000)

    def _onStop(self, e):
        self._player.stop()
        self.resetInactivityTimer(1)

    def _onRequeue(self, e):
        self.resetInactivityTimer()
        try:
            self._logger.info("Requeueing track.")
            self._player.addTrack(self._track.getPath())
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return
        
    def _onRequeueAndPlay(self, e):
        self.resetInactivityTimer()
        try:
            self._logger.info("Requeueing track and playing it.")
            position = self._player.getCurrentTrackPos() + 1
            self._player.insertTrack(self._track.getPath(), position)
            self._player.playAtPosition(position)
            self.resetInactivityTimer(1000)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onToggleNQr(self, e=None):
        self._logger.debug("Toggling NQr.")
        if self.menuToggleNQr.IsChecked() == False:
            self._toggleNQr = False
            self._logger.info("Restoring shuffle status.")
            self._player.setShuffle(self._oldShuffleStatus)
            if self._restorePlaylist == True and self._oldPlaylist != None:
                self._player.loadPlaylist(self._oldPlaylist)
            self._logger.info("Enqueueing turned off.")
        elif self.menuToggleNQr.IsChecked() == True:
            self._toggleNQr = True
            self._logger.info("Storing shuffle status.")
            self._oldShuffleStatus = self._player.getShuffle()
            self._player.setShuffle(False)
            ## poss shouldn't restore the playlist ever?
            if self._restorePlaylist == True:
                self._oldPlaylist = self._player.savePlaylist()
            self._logger.info("Enqueueing turned on.")
            self.maintainPlaylist()

    def _onTrackChange(self, e):
        self._playingTrack = e.getTrack()
        self._db.getLastPlayedInSeconds(
            self._playingTrack,
            lambda previous, track=self._playingTrack:\
                track.setPreviousPlay(previous), priority=1)
        self._playTimer.Stop()
        if self._playTimer.Start(self._playDelay, oneShot=True) == False:
            self._playingTrack.addPlay()
        self.addTrack(self._playingTrack)
        self.maintainPlaylist()
    
    def _onNoNextTrack(self, e):
        self.maintainPlaylist()
        
    def _onRequestAttention(self, e):
        self._logger.debug("Requesting user attention.")
        self.RequestUserAttention() # poss use wx.USER_ATTENTION_ERROR as arg?
        
    def _onPlayTimerDingCompletion(self, track):
        if track == self._playingTrack:
            self.refreshLastPlayed(0, track)
            if track == self._playingTrack:
                self.refreshPreviousPlay(0, track)
            else:
                self.refreshPreviousPlay(1, track)
        else:
            self.refreshLastPlayed(1, track)
            self.refreshPreviousPlay(1, track)

    def _onPlayTimerDing(self, e):
        track = self._playingTrack
        track.addPlay(self._playDelay,
                      lambda track=track: self._onPlayTimerDingCompletion(
                            track))

    def _onInactivityTimerDing(self, e):
        if self._index != 0:
            self.selectTrack(0)
            
    def _onRefreshTimerDing(self, e):
        top = self._trackList.GetTopItem()
        visibleCount = self._trackList.GetCountPerPage() + 1
        total = self._trackList.GetItemCount()
        if visibleCount > total:
            visibleCount = total
        elif total - visibleCount < top:
            visibleCount -= 1
        for index in range(top, top + visibleCount):
            trackID = self._trackList.GetItemData(index)
            self._trackFactory.getTrackFromID(
                self._db, trackID,
                lambda track, index=index: self.refreshPreviousPlay(index,
                                                                    track),
                priority=1)

    def resetInactivityTimer(self, time=None):
        self._logger.debug("Restarting inactivity timer.")
        if time == None:
            time = self._inactivityTime
        self._inactivityTimer.Start(time, oneShot=False)

    def maintainPlaylist(self):
        if self._toggleNQr == True:
            self._logger.debug("Maintaining playlist.")
            trackPosition = self._player.getCurrentTrackPos()
            if trackPosition > self._defaultTrackPosition:
                self._player.cropPlaylist(
                    trackPosition - self._defaultTrackPosition)
            playlistLength = self._player.getPlaylistLength()
            if playlistLength < self._defaultPlaylistLength:
                self.enqueueRandomTracks(
                    self._defaultPlaylistLength - playlistLength)
                
    def _onSelectTrackCompletion(self, track):
        self._track = track
        self.populateDetails(self._track)
        self._track.getScoreValue(
            lambda score: self.setScoreSliderPosition(score), priority=1)

    def _onSelectTrack(self, e):
        self.resetInactivityTimer()
        self._logger.debug("Track has been selected.")
        self._logger.debug("Retrieving selected track's information.")
        self._trackID = e.GetData()
        self._index = e.GetIndex()
        self._trackFactory.getTrackFromID(
            self._db, self._trackID,
            lambda track: self._onSelectTrackCompletion(track), priority=1)
        

    def _onDeselectTrack(self, e):
        self.resetInactivityTimer()
        self._logger.debug("Track has been deselected.")
        self.clearDetails()

    def addTrack(self, track, select=False):
        self.addTrackAtPos(track, 0, select=select)
        
    def _addTrackAtPosCompletion(self, index, track, isScored, lastPlayed,
                                 score, scoreValue, trackID, select=False):
        self._logger.debug("Adding track to track playlist.")
        if isScored == False:
            score = "("+str(scoreValue)+")"
        else:
            score = str(score)
        ## should be time from last play?
        if lastPlayed == None:
            lastPlayed = "-"
        self._trackList.InsertStringItem(index, track.getArtist())
        self._trackList.SetStringItem(index, 1, track.getTitle())
        self._trackList.SetStringItem(index, 2, score)
        self._trackList.SetStringItem(index, 3, lastPlayed)
        previous = track.getPreviousPlay()
        if previous != None:
            self._trackList.SetStringItem(index, 4,
                                          roughAge(time.time() - previous))
        weight = track.getWeight()
        if weight != None:
            self._trackList.SetStringItem(index, 5, str(weight))
        self._trackList.SetItemData(index, trackID)
        if select == True:
            self.selectTrack(index)
        elif self._index >= index:
            self._index += 1
        
    # TODO: give higher priority?
    def addTrackAtPos(self, track, index, select=False):
        multicompletion = MultiCompletion(
            5, lambda isScored, lastPlayed, score, scoreValue, trackID,\
                index=index, track=track, select=select:\
                    self._addTrackAtPosCompletion(index, track, isScored,
                                                  lastPlayed, score, scoreValue,
                                                  trackID, select=select))
        
        track.getIsScored(lambda isScored, multicompletion=multicompletion:\
                            multicompletion.put(0, isScored), priority=1)
        self._db.getLastPlayedLocalTime(
            track, lambda lastPlayed, multicompletion=multicompletion:\
                multicompletion.put(1, lastPlayed), priority=1)
        track.getScore(lambda score, multicompletion=multicompletion:\
                            multicompletion.put(2, score), priority=1)
        track.getScoreValue(lambda scoreValue, multicompletion=multicompletion:
                                multicompletion.put(3, scoreValue), priority=1)
        track.getID(lambda trackID, multicompletion=multicompletion:\
                        multicompletion.put(4, trackID), priority=1)
        

    def enqueueTrack(self, track):
        path = track.getPath()
        self._logger.debug("Enqueueing \'"+path+"\'.")
        self._player.addTrack(path)
#        self._db.addEnqueue(track)

## TODO: would be better for NQr to create a queue during idle time and pop from
##       it when enqueuing
    def enqueueRandomTracks(self, number, tags=None):
        if self._enqueueing:
            self._logger.info("Already enqueuing")
            return
        self._enqueueing = True
        self._trackMonitor.setEnqueueing(True)
        self._logger.debug("Enqueueing "+str(number)+" random track"\
                           +plural(number)+'.')
        completion = lambda tracks: \
                     self._enqueueRandomTracksCompletion(tracks)
        # FIXME: poss use a changing value for number to speed up queueing if it
        #        takes a long time
        self._player.getUnplayedTrackIDs(
            self._db, lambda exclude, number=number, completion=completion,\
                tags=tags: self._randomizer.chooseTracks(number, exclude,
                                                         completion, tags))

    def _enqueueRandomTracksCompletion(self, tracks):
## FIXME: untested!! poss most of the legwork should be done in db.getLinkIDs
        self._logger.debug("Checking tracks for links.")
        # Perhaps set at the end?
        self._enqueueing = False
        self._trackMonitor.setEnqueueing(False)
        for track in tracks:
            self.enqueueTrack(track)
            # FIXME: needs links to be made async - started in Database
#            linkIDs = self._db.getLinkIDs(track)
#            if linkIDs == None:
#                self.enqueueTrack(track)
#            else:
#                originalLinkID = linkIDs[0]
#                (firstTrackID,
#                 secondTrackID) = self._db.getLinkedTrackIDs(originalLinkID)
#                firstTrack = self._trackFactory.getTrackFromID(self._db,
#                                                               firstTrackID)
#                secondTrack = self._trackFactory.getTrackFromID(
#                    self._db, secondTrackID)
#                trackQueue = deque([firstTrack, secondTrack])
#                linkIDs = self._db.getLinkIDs(firstTrack)
#                oldLinkIDs = originalLinkID
#                ## finds earlier tracks
#                while True:
#                    for linkID in linkIDs:
#                        if linkID not in oldLinkIDs:
#                            (newTrackID,
#                             trackID) = self._db.getLinkedTrackIDs(linkID)
#                            track = self._trackFactory.getTrackFromID(
#                                self._db, newTrackID)
#                            trackQueue.appendleft(track)
#                            oldLinkIDs = linkIDs
#                            linkIDs = self._db.getLinkIDs(track)
#                    if oldLinkIDs == linkIDs:
#                        break
#                linkIDs = self._db.getLinkIDs(secondTrack)
#                oldLinkIDs = originalLinkID
#                ## finds later tracks
#                while True:
#                    for linkID in linkIDs:
#                        if linkID not in oldLinkIDs:
#                            (trackID,
#                             newTrackID) = self._db.getLinkedTrackIDs(
#                                linkID)
#                            track = self._trackFactory.getTrackFromID(
#                                self._db, newTrackID)
#                            trackQueue.append(track)
#                            oldLinkIDs = linkIDs
#                            linkIDs = self._db.getLinkIDs(track)
#                    if oldLinkIDs == linkIDs:
#                        break
#                for track in trackQueue:
#                    self.enqueueTrack(track)
##                    if secondLinkID != None:
##                        (secondTrackID,
##                         thirdTrackID) = self._db.getLinkedTrackIDs(secondLinkID)
##                        thirdTrack = self._trackFactory.getTrackFromID(self._db,
##                                                                      thirdTrackID)
##                        self.enqueueTrack(thirdTrack)

## FIXME: seems to give an outlined focus on track 2 (poss does nothing except
##        look confusing) - seems to have stopped...
    def refreshSelectedTrack(self):
        self._logger.debug("Refreshing selected track.")
        self.refreshTrack(self._index, self._track)
        self._track.getScore(lambda score: self.setScoreSliderPosition(score),
                             priority=1)
        self.populateDetails(self._track)

    def refreshSelectedTrackScore(self):
        self.refreshScore(self._index, self._track)
        self._track.getScore(lambda score: self.setScoreSliderPosition(score),
                             priority=1)
        self.populateDetails(self._track)

    def refreshTrack(self, index, track):
        self.refreshArtist(index, track)
        self.refreshTitle(index, track)
        self.refreshScore(index, track)
        self.refreshLastPlayed(index, track)
        self.refreshPreviousPlay(index, track)

    def refreshArtist(self, index, track):
        self._trackList.SetStringItem(index, 0, track.getArtist())
        self._trackList.RefreshItem(index)

    def refreshTitle(self, index, track):
        self._trackList.SetStringItem(index, 1, track.getTitle())
        self._trackList.RefreshItem(index)
        
    def _refreshScoreCompletion(self, index, isScored, scoreValue, score):
        if isScored == False:
            score = "("+str(scoreValue)+")"
        else:
            score = str(score)
        self._trackList.SetStringItem(index, 2, score)
        self._trackList.RefreshItem(index)

    def refreshScore(self, index, track):
        multicompletion = MultiCompletion(
            3, lambda isScored, scoreValue, score, index=index:\
                self._refreshScoreCompletion(index, isScored, scoreValue,
                                             score))
        track.getIsScored(lambda isScored, multicompletion=multicompletion:\
                            multicompletion.put(0, isScored), priority=1)
        track.getScoreValue(lambda scoreValue, multicompletion=multicompletion:\
                                multicompletion.put(1, scoreValue), priority=1)
        track.getScore(lambda score, multicompletion=multicompletion:\
                            multicompletion.put(2, score), priority=1)
        
    def _refreshLastPlayedCompletion(self, index, lastPlayed):
        if lastPlayed == None:
            lastPlayed = "-"
        self._trackList.SetStringItem(index, 3, lastPlayed)
        self._trackList.RefreshItem(index)

    def refreshLastPlayed(self, index, track):
        self._db.getLastPlayedLocalTime(
            track,
            lambda lastPlayed, index=index: self._refreshLastPlayedCompletion(
                index, lastPlayed), priority=1)

    def refreshPreviousPlay(self, index, track):
        previous = track.getPreviousPlay()
        if previous != None:
            self._trackList.SetStringItem(index, 4,
                                          roughAge(time.time() - previous))
        self._trackList.RefreshItem(index)

    def selectTrack(self, index):
        self._logger.debug("Selecting track in position "+str(index)+".")
        self._trackList.SetItemState(index, wx.LIST_STATE_SELECTED, -1)
        self._trackList.EnsureVisible(index)
        
    def _populateDetailsCompletion(self, track, score, playCount, lastPlayed,
                                   tags):
        self._logger.debug("Populating details panel.")

        detailString = "Artist:  \t"+track.getArtist()\
            +"\nTitle:  \t"+track.getTitle()\
            +"\nAlbum:  \t"+track.getAlbum()\
            +"\nTrack:  \t"+track.getTrackNumber()+"    \tLength:  \t"\
            +track.getLengthString()
            
        bpm = track.getBPM()
        if bpm != "-":
            detailString += "\nBPM:  \t"+bpm
            
        detailString += "\nScore:  \t"+str(score)\
            +"\nPlay Count:    "+str(playCount)
            
        if lastPlayed != None:
            detailString += "    \tPlayed at:  \t"+lastPlayed
            
        self.resetTagMenu()
        tagString = ""
        for tag in tags:
            tagString += tag + ", "
            tagID = self._getTagID(tag)
            self._tagMenu.Check(tagID, True)
        if tagString != "":
            detailString += "\nTags:  \t"+tagString[:-2]
            
        detailString += "\nFilepath:      "+track.getPath()
        
        self.clearDetails()
        self.addToDetails(detailString)
        self._details.SetInsertionPoint(0)
        
## the first populateDetails seems to produce a larger font than subsequent
## calls in Mac OS
    def populateDetails(self, track): # FIXME: make higher priority?
        multicompletion = MultiCompletion(
            4, lambda score, playCount, lastPlayed, tags, track=track:\
                self._populateDetailsCompletion(track, score, playCount,
                                                lastPlayed, tags))
        
        track.getScore(lambda score, multicompletion=multicompletion:\
                            multicompletion.put(0, score), priority=1)
        track.getPlayCount(lambda playCount, multicompletion=multicompletion:\
                                multicompletion.put(1, playCount), priority=1)
        self._db.getLastPlayedLocalTime(
            track, lambda lastPlayed, multicompletion=multicompletion:\
                multicompletion.put(2, lastPlayed), priority=1)
        track.getTags(lambda tags, multicompletion=multicompletion:\
                        multicompletion.put(3, tags), priority=1)

    def addToDetails(self, detail):
        self._details.AppendText(detail)

    def clearDetails(self):
        self._logger.debug("Clearing details panel.")
        self._details.Clear()

    def setTag(self, track, tagID):
        self._logger.info("Tagging track.")
        self._tagMenu.Check(tagID, True)
        track.setTag(self._allTags[tagID])

    def unsetTag(self, track, tagID):
        self._logger.info("Untagging track.")
        self._tagMenu.Check(tagID, False)
        track.unsetTag(self._allTags[tagID])
        
    def _resetTagMenuCompletion(self, tags):
        for tag in tags:
            tagID = self._getTagID(tag)
            self._tagMenu.Check(tagID, False)

    def resetTagMenu(self):
        self._db.getAllTagNames(
            lambda tags: self._resetTagMenuCompletion(tags), priority=1)

    def _getTagID(self, tag):
        for (tagID, tagName) in self._allTags.iteritems():
            if tag == tagName:
                return tagID

    def getPrefsPage(self, parent, logger, system):
        return PrefsPage(
            parent, system, self._configParser, logger, self._defaultPlayDelay,
            self._defaultInactivityTime, self._defaultIgnore,
            self._defaultHaveLogPanel, self._defaultRescanOnStartup,
            self._defaultDefaultDirectory), "GUI"

    def loadSettings(self):
        try:
            self._configParser.add_section("GUI")
        except ConfigParser.DuplicateSectionError:
            pass
        try:
            self._playDelay = self._configParser.getint("GUI", "playDelay")
        except ConfigParser.NoOptionError:
            self._playDelay = self._defaultPlayDelay
        try:
            self._inactivityTime = self._configParser.getint("GUI",
                                                             "inactivityTime")
        except ConfigParser.NoOptionError:
            self._inactivityTime = self._defaultInactivityTime
        try:
            self._ignoreNewTracks = self._configParser.getboolean(
                "GUI", "ignoreNewTracks")
        except ConfigParser.NoOptionError:
            self._ignoreNewTracks = self._defaultIgnore
        try:
            self._rescanOnStartup = self._configParser.getboolean(
                "GUI", "rescanOnStartup")
        except ConfigParser.NoOptionError:
            self._rescanOnStartup = self._defaultRescanOnStartup
        try:
            self._haveLogPanel = self._configParser.getboolean(
                "GUI", "haveLogPanel")
        except ConfigParser.NoOptionError:
            self._haveLogPanel = self._defaultHaveLogPanel
        try:
            self._defaultDirectory = os.path.realpath(
                self._configParser.get("GUI", "defaultDirectory"))
        except ConfigParser.NoOptionError:
            self._defaultDirectory = self._defaultDefaultDirectory

class PrefsPage(BasePrefsPage):
    def __init__(self, parent, system, configParser, logger, defaultPlayDelay,
                 defaultInactivityTime, defaultIgnore, defaultHaveLogPanel,
                 defaultRescanOnStartup, defaultDefaultDirectory):
        BasePrefsPage.__init__(self, parent, system, configParser, logger,
                               "GUI", defaultPlayDelay, defaultInactivityTime,
                               defaultIgnore, defaultHaveLogPanel,
                               defaultRescanOnStartup, defaultDefaultDirectory)
        
        self._initCreateDirectorySizer()
        self._initCreatePlayDelaySizer()
        self._initCreateInactivityTimeSizer()
        self._initCreateIgnoreCheckBox()
        self._initCreateRescanCheckBox()
        self._initCreateLogCheckBox()

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._directorySizer, 0)
        mainSizer.Add(self._playDelaySizer, 0)
        mainSizer.Add(self._inactivityTimeSizer, 0)
        mainSizer.Add(self._ignoreCheckBox, 0)
        mainSizer.Add(self._rescanCheckBox, 0)
        mainSizer.Add(self._logCheckBox, 0)

        self.SetSizer(mainSizer)
        
    def _initCreateDirectorySizer(self): # FIXME: make a "choose" dialog
        self._directorySizer = wx.BoxSizer(wx.HORIZONTAL)

        directoryLabel = wx.StaticText(self, -1, "Default Dialog Directory: ")
        self._directorySizer.Add(directoryLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._directoryControl = wx.TextCtrl(
            self, -1, str(self._settings["defaultDirectory"]))
        self._directorySizer.Add(self._directoryControl, 0)

        self._directoryControl.Bind(wx.EVT_KILL_FOCUS, self._onDirectoryChange)

    def _initCreatePlayDelaySizer(self):
        self._playDelaySizer = wx.BoxSizer(wx.HORIZONTAL)

        playDelayLabel = wx.StaticText(self, -1, "Play Record Delay: ")
        self._playDelaySizer.Add(playDelayLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)
        
        self._playDelayControl = wx.TextCtrl(
            self, -1, str(self._settings["playDelay"]), size=(40,-1))
        self._playDelaySizer.Add(self._playDelayControl, 0)

        playDelayUnits = wx.StaticText(self, -1, " milliseconds")
        self._playDelaySizer.Add(playDelayUnits, 0,
                                 wx.RIGHT|wx.TOP|wx.BOTTOM, 3)

        self.Bind(wx.EVT_TEXT, self._onPlayDelayChange,
                  self._playDelayControl)

    def _initCreateInactivityTimeSizer(self):
        self._inactivityTimeSizer = wx.BoxSizer(wx.HORIZONTAL)

        inactivityTimeLabel = wx.StaticText(self, -1, "Idle Time: ")
        self._inactivityTimeSizer.Add(inactivityTimeLabel, 0,
                                      wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._inactivityTimeControl = wx.TextCtrl(
            self, -1, str(self._settings["inactivityTime"]), size=(50,-1))
        self._inactivityTimeSizer.Add(self._inactivityTimeControl, 0)

        inactivityTimeUnits = wx.StaticText(self, -1, " milliseconds")
        self._inactivityTimeSizer.Add(inactivityTimeUnits, 0,
                                      wx.RIGHT|wx.TOP|wx.BOTTOM, 3)

        self.Bind(wx.EVT_TEXT, self._onInactivityTimeChange,
                  self._inactivityTimeControl)

    def _initCreateIgnoreCheckBox(self):
        self._ignoreCheckBox = wx.CheckBox(self, -1,
                                           "Ignore Tracks not in Database")
        if self._settings["ignoreNewTracks"] == True:
            self._ignoreCheckBox.SetValue(True)
        else:
            self._ignoreCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onIgnoreChange, self._ignoreCheckBox)
        
    def _initCreateRescanCheckBox(self):
        self._rescanCheckBox = wx.CheckBox(self, -1,
                                           "Rescan Library on Startup")
        if self._settings["rescanOnStartup"] == True:
            self._rescanCheckBox.SetValue(True)
        else:
            self._rescanCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onRescanChange, self._rescanCheckBox)
        
    def _initCreateLogCheckBox(self):
        self._logCheckBox = wx.CheckBox(self, -1, "Show Log Panel")
        if self._settings["haveLogPanel"] == True:
            self._logCheckBox.SetValue(True)
        else:
            self._logCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onLogChange, self._logCheckBox)
        
    def _onDirectoryChange(self, e):
        rawDirectory = self._directoryControl.GetLineText(0)
        directory = os.path.realpath(rawDirectory)
        if validateDirectory(self._directoryControl):
            self._settings["defaultDirectory"] = os.path.realpath(directory)
        else:
            self._directoryControl.ChangeValue(
                self._settings["defaultDirectory"])

    def _onPlayDelayChange(self, e):
        if validateNumeric(self._playDelayControl):
            playDelay = self._playDelayControl.GetLineText(0)
            if playDelay != "":
                self._settings["playDelay"] = int(playDelay)

    def _onInactivityTimeChange(self, e):
        if validateNumeric(self._inactivityTimeControl):
            inactivityTime = self._inactivityTimeControl.GetLineText(0)
            if inactivityTime != "":
                self._settings["inactivityTime"] = int(inactivityTime)

    def _onIgnoreChange(self, e):
        if self._ignoreCheckBox.IsChecked():
            self._settings["ignoreNewTracks"] = True
        else:
            self._settings["ignoreNewTracks"] = False
            
    def _onRescanChange(self, e):
        if self._rescanCheckBox.IsChecked():
            self._settings["rescanOnStartup"] = True
        else:
            self._settings["rescanOnStartup"] = False
            
    def _onLogChange(self, e):
        if self._logCheckBox.IsChecked():
            self._settings["haveLogPanel"] = True
        else:
            self._settings["haveLogPanel"] = False
        
    def _setDefaults(self, defaultPlayDelay, defaultInactivityTime,
                     defaultIgnore, defaultHaveLogPanel, defaultRescanOnStartup,
                     defaultDefaultDirectory):
        self._defaultPlayDelay = defaultPlayDelay
        self._defaultInactivityTime = defaultInactivityTime
        self._defaultIgnore = defaultIgnore
        self._defaultHaveLogPanel = defaultHaveLogPanel
        self._defaultRescanOnStartup = defaultRescanOnStartup
        self._defaultDefaultDirectory = defaultDefaultDirectory

    def _loadSettings(self):
        try:
            playDelay = self._configParser.getint("GUI", "playDelay")
            self._settings["playDelay"] = playDelay
        except ConfigParser.NoOptionError:
            self._settings["playDelay"] = self._defaultPlayDelay
        try:
            inactivityTime = self._configParser.getint("GUI", "inactivityTime")
            self._settings["inactivityTime"] = inactivityTime
        except ConfigParser.NoOptionError:
            self._settings["inactivityTime"] = self._defaultInactivityTime
        try:
            ignore = self._configParser.getboolean("GUI", "ignoreNewTracks")
            self._settings["ignoreNewTracks"] = ignore
        except ConfigParser.NoOptionError:
            self._settings["ignoreNewTracks"] = self._defaultIgnore
        try:
            rescan = self._configParser.getboolean("GUI", "rescanOnStartup")
            self._settings["rescanOnStartup"] = rescan
        except ConfigParser.NoOptionError:
            self._settings["rescanOnStartup"] = self._defaultRescanOnStartup
        try:
            log = self._configParser.getboolean("GUI", "haveLogPanel")
            self._settings["haveLogPanel"] = log
        except ConfigParser.NoOptionError:
            self._settings["haveLogPanel"] = self._defaultHaveLogPanel
        try:
            directory = os.path.realpath(
                self._configParser.get("GUI", "defaultDirectory"))
            self._settings["defaultDirectory"] = directory
        except ConfigParser.NoOptionError:
            self._settings["defaultDirectory"] = self._defaultDefaultDirectory
