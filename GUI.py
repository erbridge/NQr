# GUI
#
# TODO: Add library viewer with scoring, queueing and search funcionality using
#       splitter window: top left - artist, top right - album, centre - tracks,
#       bottom - details.
# TODO: Add delete file/directory menus, with confirmation?
# TODO: Add support for mulitple track selections?
# TODO: Display unplayed tracks with option to remove and rearrange playlist.
# TODO: When NQr queueing off, change trackList behaviour to only show played
#       tracks, not to represent unplayed tracks, or show only 3 future tracks?
# TODO: Implement ignoring of tracks played not in database
#       (option already created).
# TODO: Make keyboard shortcuts make sense for Macs
#       (possibly default behaviour).
# TODO: Make details resizable (splitter window?).
# TODO: Add tags to right click menu.
# TODO: Give scores a drop down menu in the track list.
# TODO: Add requeue next.
# TODO: Add keyboard commands for (user defined) common ratings: like, love,
#       neutral, dislike, hate?
# TODO: Swap some menu ids for stock items:
#       http://docs.wxwidgets.org/2.9/page_stockitems.html
#
# FIXME: Track refreshes should only refresh things that will change - no
#        longer necessary?
# FIXME: Reduce processing - e.g. check tracks less often (if doing this
#        change delay in _onNext() etc.).
# FIXME: Old track details should update if track is in track list twice.
# FIXME: Change indicies when possible to finditemdata calls?
# FIXME: Last played should consistently be the time since the previous play 
#        (if there is one) and poss shouldn't update.
# FIXME: Make clicking a position on the slider move it there (and holding the
#        click drag it).
# FIXME: Make all clicks/key presses reset inactivity timer (done,
#        needs testing).
# FIXME: ClearCache breaks references to tracks in cache.

#from collections import deque
import ConfigParser
import os
import socket
import sys
import threading
import time
#import wx.lib.agw.multidirdialog as wxMDD

import Errors
import Events
import Util

wx = Util.wx


class TrackMonitor(Util.BaseThread):
    
    def __init__(self, parent, lock, db, player, trackFactory, loggerFactory,
                 trackCheckDelay):
        Util.BaseThread.__init__(
            self, parent, "Track Monitor",
            loggerFactory.getLogger("NQr.TrackMonitor", "debug"), None, lock)
        self._db = db
        self._player = player
        self._trackFactory = trackFactory
        self._trackCheckDelay = trackCheckDelay
        self._enqueueing = False
        self._abortFlag = False
        self._logging = True
        self._currentTrackPath = None

    def _run(self):
        self._restartTimer()

    def _abort(self):
        self._abortFlag = True
        self._timer.cancel()
    
    def setEnqueueing(self, status):
        self._enqueueing = status

    def _restartTimer(self):
        self._timer = threading.Timer(self._trackCheckDelay, self._onTimerDing)
        self._timer.start()

    def _onTimerDing(self):
        self.queue(lambda thisCallback: self._checkPath(thisCallback),
                   self._trace)
        self.queue(lambda thisCallback: self._checkHasNextTrack(thisCallback),
                   self._trace)
        self._restartTimer()
        
    def _checkPath(self, thisCallback):
        if self._abortFlag:
            return
        try:
            newTrackPath = self._player.getCurrentTrackPath(
                thisCallback, logging=self._logging)
        except Errors.NoTrackError:
            newTrackPath = None
        except Errors.PlayerNotRunningError:
            return
        self._logging = False
        if newTrackPath != self._currentTrackPath:
            self.postDebugLog("Track has changed.")
            self._currentTrackPath = newTrackPath
            self.postEvent(Events.TrackChangeEvent(self._db, self._trackFactory,
                                                   self._currentTrackPath,
                                                   thisCallback))
            self._logging = True
            self._enqueueing = True
            
    def _checkHasNextTrack(self, thisCallback):
        try:
            if (self._abortFlag or self._enqueueing or
                self._player.hasNextTrack(thisCallback)):
                    return
        except Errors.PlayerNotRunningError:
            return
        self.postDebugLog("End of playlist reached.")
        self.postEvent(Events.NoNextTrackEvent(thisCallback))


class SocketMonitor(Util.BaseThread):
    
    def __init__(self, window, lock, socket, address, loggerFactory):
        self._logger = loggerFactory.getLogger("NQr.SocketMonitor", "debug")
        Util.BaseThread.__init__(self, window, "Socket Monitor", self._logger,
                                 None, lock)
        self._window = window
        self._lock = lock
        self._socket = socket
        self._address = address
        self._connections = []
        self._abortFlag = False

    def run(self):
        self._runningLock.acquire()
        self._socket.listen(5) # FIXME: How many can/should it listen to?
        while not self._abortFlag:
            # FIXME: Has windows firewall permission issues...
            (conn, address) = self._socket.accept()
            self.postDebugLog(
                "Starting connection (" + address[0] + ":" + str(address[1])
                + ") monitor.")
            connMonitor = ConnectionMonitor(self._window, self._lock, conn,
                                            address, self._logger)
            connMonitor.start_()
            self._connections.append(connMonitor)
        self._socket.close()
        self.postDebugLog("Socket monitor stopped.")
        self._runningLock.release()
                
    def abort(self):
        self._abortFlag = True
        sock = socket.socket()
        sock.connect(self._address)
        sock.shutdown(2)
        sock.close()
        
    def getRunningLocks(self):
        locks = [self.getRunningLock()]
        for conn in self._connections:
            locks.append(conn.getRunningLock())
        return locks


class ConnectionMonitor(Util.BaseThread):
    
    def __init__(self, window, lock, connection, address, logger):
        self._address = address[0] + ":" + str(address[1])
        Util.BaseThread.__init__(self, window, self._address + " Monitor",
                                 logger, None, lock)
        self._conn = connection
    
    def run(self):
        self._runningLock.acquire()
        while True:
            try:
                message = self._recieve()
            except RuntimeError as err:
                if str(err) != "socket connection broken":
                    raise err
                self.postDebugLog(
                    "Stopping connection (" + self._address + ") monitor.")
                self._conn.shutdown(2)
                self._conn.close()
                break
            if message == "ATTEND\n":
                self.postEvent(Events.RequestAttentionEvent())
            elif message == "PAUSE\n":
                self.postEvent(Events.PauseEvent())
            elif message == "PLAY\n":
                self.postEvent(Events.PlayEvent())
            elif message == "STOP\n":
                self.postEvent(Events.StopEvent())
            elif message == "NEXT\n":
                self.postEvent(Events.NextEvent())
            elif message == "PREV\n":
                self.postEvent(Events.PreviousEvent())
            elif message == "RATEUP\n":
                self.postEvent(Events.RateUpEvent())
            elif message == "RATEDOWN\n":
                self.postEvent(Events.RateDownEvent())
            else:
                raise Errors.BadMessageError(trace=Util.getTrace(self._trace))
        self.postDebugLog("Connection (" + self._address + ") monitor stopped.")
        self._runningLock.release()
                               
    def _recieve(self):
        byte = ""
        message = ""
        while byte != "\n":
            byte = self._conn.recv(1)
            if byte == "":
                raise RuntimeError("socket connection broken")
            message += byte
        return message
        
    def abort(self): # FIXME: Does this work?
        self._conn.close()


class MainWindow(wx.Frame, Util.EventPoster):
    
    def __init__(self, parent, db, randomizer, player, trackFactory,
                 loggerFactory, prefsFactory, configParser, socket, address,
                 title, threadLock, defaultRestorePlaylist,
                 defaultEnqueueOnStartup, defaultRescanOnStartup,
                 defaultPlaylistLength, defaultPlayDelay, defaultIgnore,
                 defaultTrackCheckDelay, defaultDumpPath, eventLogger,
                 defaultInactivityTime=30000,
                 wildcards="Music files (*.mp3;*.mp4)|*.mp3;*.mp4|All files|"
                     + "*.*", defaultDefaultDirectory="",
                 defaultHaveLogPanel=True):
        self._ID_TOGGLENQR = wx.NewId()

        self._db = db
        self._randomizer = randomizer
        self._player = player
        self._player.makeEventPoster(self, threadLock)
        self._trackFactory = trackFactory
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
        self._defaultTrackCheckDelay = defaultTrackCheckDelay
        self._dumpPath = defaultDumpPath
        self._eventLogger = eventLogger
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
        Util.EventPoster.__init__(self, self, self._logger, threadLock)
        
        self._logger.debug("Creating status bar.")
        self.CreateStatusBar()
        self._initCreateMenuBar()
        self._initCreateTrackRightClickMenu()
        self._initCreateMainPanel()

        self._logger.debug("Creating play delay timer.")
        self._playTimer = wx.Timer(self, wx.NewId())

        self._logger.debug("Creating and starting inactivity timer.")
        self._inactivityTimer = wx.Timer(self, wx.NewId())
        self._inactivityTimer.Start(self._inactivityTime, oneShot=False)

        self._logger.debug("Creating and starting track list refresh timer.")
        self._refreshTimer = wx.Timer(self, wx.NewId())
        self._refreshTimer.Start(1000, oneShot=False)
        
        self._logger.debug("Starting track monitor.")
        self._trackMonitor = TrackMonitor(self, threadLock, self._db,
                                          self._player, self._trackFactory,
                                          loggerFactory, self._trackCheckDelay)
        
        self._logger.debug("Starting socket monitor.")
        self._socketMonitor = SocketMonitor(self, threadLock, socket, address,
                                            loggerFactory)
        
        self.Bind(wx.EVT_TIMER, self._onPlayTimerDing, self._playTimer)
        self.Bind(wx.EVT_TIMER, self._onInactivityTimerDing,
                  self._inactivityTimer)
        self.Bind(wx.EVT_TIMER, self._onRefreshTimerDing, self._refreshTimer)
        
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
        Events.EVT_LOG(self, self._onLog)
        Events.EVT_ENQUEUE_RANDOM(self, self._onEnqueueRandomTracks)
        Events.EVT_CHOOSE_TRACKS(self, self._onChooseTracks)
        
        self.Bind(wx.EVT_CLOSE, self._onClose, self)
        self._bindMouseAndKeyEvents(self)

        if self._restorePlaylist:
            self._oldPlaylist = None

        if self._enqueueOnStartup:
            self._optionsMenu.Check(self._ID_TOGGLENQR, True)
            self._onToggleNQr(startup=True)

        self._initCreateHotKeyTable()
        self._logger.debug("Drawing main window.")
        self._setPositionAndSize()
        self.Show(True)
        
        wx.CallAfter(self._onStart)
            
    def _onStart(self):
        if Util.getUpdate() != None:
            Util.doUpdate()
        self._trackMonitor.start_()
        self._socketMonitor.start_()
        self.resetInactivityTimer(2000*self._trackCheckDelay)
        
        if self._rescanOnStartup:
            self._onRescan()
        
        self.maintainPlaylist()
        
    # FIXME: Needs testing to make sure all clicks are registered correctly
    #        (and mouse holds on score slider).
    def _bindMouseAndKeyEvents(self, window):
        window.Bind(wx.EVT_MOUSE_EVENTS, self._onMouseOrKeyPress)
        window.Bind(wx.EVT_KEY_DOWN, self._onMouseOrKeyPress)

    def _trackMonitorQueue(self, completion, traceCallbackOrList=None):
        self._trackMonitor.queue(completion, traceCallbackOrList)

    def _initCreateMenuBar(self):
        self._logger.debug("Creating menu bar.")
        self._initCreateFileMenu()
        self._initCreateRateMenu()
        self._initCreatePlayerMenu()
        self._initCreateTagMenu()
        self._initCreateOptionsMenu()
        self._initCreateAdvancedMenu()

        menuBar = wx.MenuBar()
        menuBar.Append(self._fileMenu, "&File")
        menuBar.Append(self._playerMenu, "&Player")
        menuBar.Append(self._tagMenu, "&Tags")
        menuBar.Append(self._optionsMenu, "&Options")
        menuBar.Append(self._advMenu, "&Advanced")

        self.SetMenuBar(menuBar)
        self._bindMouseAndKeyEvents(menuBar)
        
    def _addMenuItem(self, menu, label, caption, onClick, id=None, hotkey=None,
                     checkItem=False):
        if id == None:
            id = wx.NewId()
        if checkItem == True:
            menuItem = menu.AppendCheckItem(id, label, caption)
        else:
            menuItem = menu.Append(id, label, caption)
        # FIXME: Labels are sufficient?
        # http://docs.wxwidgets.org/2.9/classwx_menu_item.html#8b0517fb35e3eada66b51568aa87f261
        if hotkey != None:
            (modifier, key) = hotkey
            self._addHotKey(modifier, key, id)
        self.Bind(wx.EVT_MENU, onClick, menuItem)

    def _initCreateFileMenu(self):
        self._logger.debug("Creating file menu.")
        self._fileMenu = wx.Menu()
        self._addMenuItem(self._fileMenu, "&About NQr\tF1",
                          " Information about NQr", self._onAbout,
                          id=wx.ID_ABOUT, hotkey=(None, wx.WXK_F1))
        self._fileMenu.AppendSeparator()
        self._addMenuItem(self._fileMenu, "Add &File...\tCtrl+F",
                          " Add a file to the library", self._onAddFile,
                          hotkey=("ctrl", "F"))
        self._addMenuItem(self._fileMenu, "Add &Directory...\tCtrl+D",
                          " Add a directory to the library and watch list",
                          self._onAddDirectory, hotkey=("ctrl", "D"))
        self._addMenuItem(
            self._fileMenu, "Add Directory &Once...",
            " Add a directory to the library but not the watch list",
            self._onAddDirectoryOnce)
        self._fileMenu.AppendSeparator()
        self._addMenuItem(self._fileMenu, "&Remove Directory...",
                          " Remove a directory from the watch list",
                          self._onRemoveDirectory)
        self._fileMenu.AppendSeparator()
        self._addMenuItem(self._fileMenu, "&Link Tracks...",
                          " Link two tracks so they always play together",
                          self._onLinkTracks)
        self._addMenuItem(self._fileMenu, "Remo&ve Link...",
                          " Remove the link between two tracks",
                          self._onRemoveLink)
        self._fileMenu.AppendSeparator()
        self._addMenuItem(self._fileMenu, "&Rescan Library",
                          " Search previously added directories for new files",
                          self._onRescan)
        self._fileMenu.AppendSeparator()
        self._addMenuItem(self._fileMenu, "E&xit\tCtrl+Q", " Terminate NQr",
                          self._onExit, id=wx.ID_EXIT, hotkey=("ctrl", "Q"))
        self._bindMouseAndKeyEvents(self._fileMenu)

    def _initCreateRateMenu(self):
        self._logger.debug("Creating rate menu.")
        self._rateMenu = wx.Menu()
        self._populateRateMenu(self._rateMenu)
        self._bindMouseAndKeyEvents(self._rateMenu)

    # TODO: Change up in "Rate Up" to an arrow?
    def _initCreatePlayerMenu(self):
        self._logger.debug("Creating player menu.")
        self._playerMenu = wx.Menu()
        self._addMenuItem(self._playerMenu, "Pre&vious Track\tZ",
                          " Play the previous track", self._onPrevious,
                          hotkey=(None, "Z"))
        self._addMenuItem(self._playerMenu, "&Play\tX",
                          " Play or restart the current track", self._onPlay,
                          hotkey=(None, "X"))
        self._addMenuItem(self._playerMenu, "P&ause\tC",
                          " Pause or resume the current track", self._onPause,
                          hotkey=(None, "C"))
        self._addMenuItem(self._playerMenu, "&Stop\tV",
                          " Stop the current track", self._onStop,
                          hotkey=(None, "V"))
        self._addMenuItem(self._playerMenu, "&Next Track\tB",
                          " Play the next track", self._onNext,
                          hotkey=(None, "B"))
        self._playerMenu.AppendSeparator()
        self._addMenuItem(self._playerMenu, "Rate &Up\tCtrl+PgUp",
                          " Increase the score of the selected track by one",
                          self._onRateUp, hotkey=("ctrl", wx.WXK_PAGEUP))
        self._addMenuItem(self._playerMenu, "Rate &Down\tCtrl+PgDn",
                          " Decrease the score of the selected track by one",
                          self._onRateDown, hotkey=("ctrl", wx.WXK_PAGEDOWN))
        self._playerMenu.AppendMenu(wx.NewId(), "&Rate", self._rateMenu)
        self._playerMenu.AppendSeparator()
        self._addMenuItem(self._playerMenu, "&Select Current Track\tCtrl+\\",
                          " Selects the currently playing track",
                          self._onSelectCurrent, hotkey=("ctrl", "\\"))
        self._playerMenu.AppendSeparator()
        self._addMenuItem(self._playerMenu, "Re&queue Track",
                          " Add the selected track to the playlist",
                          self._onRequeue)
        self._addMenuItem(self._playerMenu, "Requeue and &Play Track",
                          " Add the selected track to the playlist and play it",
                          self._onRequeueAndPlay)
        self._addMenuItem(self._playerMenu, "Reset Sc&ore",
                          " Reset the score of the selected track",
                          self._onResetScore)
        self._playerMenu.AppendSeparator()
        self._addMenuItem(self._playerMenu, "&Launch Player",
                          " Launch the media player",
                          self._onLaunchPlayer)
        self._addMenuItem(self._playerMenu, "E&xit Player",
                          " Terminate the media player", self._onExitPlayer)
        self._bindMouseAndKeyEvents(self._playerMenu)

    def _getAllTagsCompletion(self, menu, tags):
        self._allTags = {}
        for tag in tags:
            tagID = wx.NewId()
            self._allTags[tagID] = tag
            self._addMenuItem(menu, tag, " Tag track with \'" + tag + "\'",
                              self._onTag, id=tagID, checkItem=True)
            
    def _initCreateTagMenu(self):
        self._logger.debug("Creating tag menu.")
        self._tagMenu = wx.Menu()
        self._addMenuItem(self._tagMenu, "&New...",
                          " Create new tag and tag track with it",
                          self._onNewTag)
        self._tagMenu.AppendSeparator()
        
        self._db.getAllTagNames(
            lambda thisCallback, tags, menu=self._tagMenu:
                self._getAllTagsCompletion(menu, tags),
            priority=1)
        
        self._bindMouseAndKeyEvents(self._tagMenu)

    def _initCreateOptionsMenu(self):
        self._logger.debug("Creating options menu.")
        self._optionsMenu = wx.Menu()
        self._addMenuItem(self._optionsMenu, "&Preferences...\tCtrl+P",
                          " Change NQr's settings", self._onPrefs,
                          hotkey=("ctrl", "P"))
        self._addMenuItem(self._optionsMenu, "Restore &Defaults...",
                          " Restores settings to defaults",
                          self._onRestoreSettings)
        self._optionsMenu.AppendSeparator()
        self._addMenuItem(self._optionsMenu, "En&queue with NQr\tCtrl+E",
                          " Use NQr to enqueue tracks", self._onToggleNQr,
                          id=self._ID_TOGGLENQR, hotkey=("ctrl", "E"),
                          checkItem=True)
        self._bindMouseAndKeyEvents(self._optionsMenu)
        
    def _initCreateAdvancedMenu(self):
        self._logger.debug("Creating advanced menu.")
        self._advMenu = wx.Menu()
        self._addMenuItem(self._advMenu, "&Clear Cache",
                          " Clears the track cache", self._onClearCache)
        self._addMenuItem(self._advMenu, "&Dump Queues",
                          " Dump thread queues to file", self._onDump)
        self._bindMouseAndKeyEvents(self._advMenu)

    def _initCreateRightClickRateMenu(self):
        self._logger.debug("Creating rate menu.")
        self._rightClickRateMenu = wx.Menu()
        self._populateRateMenu(self._rightClickRateMenu)
        self._bindMouseAndKeyEvents(self._rightClickRateMenu)

    def _initCreateTrackRightClickMenu(self):
        self._logger.debug("Creating track right click menu.")
        self._initCreateRightClickRateMenu()
        
        self._trackRightClickMenu = wx.Menu()
        self._addMenuItem(self._trackRightClickMenu, "Rate &Up",
                          " Increase the score of the current track by one",
                          self._onRateUp)
        self._addMenuItem(self._trackRightClickMenu, "Rate &Down",
                          " Decrease the score of the current track by one",
                          self._onRateDown)
        self._trackRightClickMenu.AppendMenu(wx.NewId(), "&Rate",
                                             self._rightClickRateMenu)
        self._trackRightClickMenu.AppendSeparator()
        self._addMenuItem(self._trackRightClickMenu, "Re&queue Track",
                          " Add the selected track to the playlist",
                          self._onRequeue)
        self._addMenuItem(self._trackRightClickMenu, "Requeue and &Play Track",
                          " Add the selected track to the playlist and play it",
                          self._onRequeueAndPlay)
        self._trackRightClickMenu.AppendSeparator()
        self._addMenuItem(self._trackRightClickMenu, "Reset Sc&ore",
                          " Reset the score of the current track",
                          self._onResetScore)
        self._bindMouseAndKeyEvents(self._trackRightClickMenu)

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
        self.SetSizeHints(430, 481)
        self._bindMouseAndKeyEvents(self._panel)

    # TODO: Use svg or gd to create button images via wx.Bitmap and
    #       wx.BitmapButton?
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
        self._bindMouseAndKeyEvents(self._playerControls)

    def _initCreateDetails(self):
        self._logger.debug("Creating details panel.")
        self._details = wx.TextCtrl(
            self._panel, wx.NewId(),
            style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_DONTWRAP, size=(-1,140))
        self._bindMouseAndKeyEvents(self._details)

    def _initCreateTrackSizer(self):
        self._logger.debug("Creating track panel.")
        self._initCreateTrackList()
        self._initCreateScoreSlider()

        self._trackSizer = wx.BoxSizer(wx.HORIZONTAL)
        self._trackSizer.Add(self._trackList, 1, wx.EXPAND|wx.RIGHT, 5)
        self._trackSizer.Add(self._scoreSlider, 0, wx.EXPAND)

    def _initCreateTrackList(self):
        self._logger.debug("Creating track playlist.")
        self._trackList = wx.ListCtrl(
            self._panel, wx.NewId(),
            style=wx.LC_REPORT|wx.LC_VRULES|wx.LC_SINGLE_SEL, size=(656,-1))
        # For some reason setting column 0 forces left justification.
        self._trackList.InsertColumn(1, "Artist", format=wx.LIST_FORMAT_CENTER,
                                     width=self._artistWidth)
        self._trackList.InsertColumn(2, "Title", format=wx.LIST_FORMAT_CENTER,
                                     width=self._titleWidth)
        self._trackList.InsertColumn(3, "Score", format=wx.LIST_FORMAT_CENTER,
                                     width=self._scoreWidth)
        self._trackList.InsertColumn(4, "Played At",
                                     format=wx.LIST_FORMAT_CENTER,
                                     width=self._playedAtWidth)
        self._trackList.InsertColumn(5, "Last Played",
                                     format=wx.LIST_FORMAT_CENTER,
                                     width=self._lastPlayedWidth)
        self._trackList.InsertColumn(6, "Weight", format=wx.LIST_FORMAT_CENTER,
                                     width=self._weightWidth)

#        try:
#            self._logger.debug("Adding current track to track playlist.")
#            currentTrackPath = self._player.getCurrentTrackPath()
#            currentTrack = self._trackFactory.getTrackFromPath(self._db,
#                                                               currentTrackPath)
#            multicompletion = MultiCompletion(
#                2, lambda currentTrackID, oldTrackID,\
#                    currentTrack=currentTrack: self._compareTracksCompletion(
#                        currentTrack, currentTrackID, oldTrackID))
#            currentTrack.getID(lambda trackID, multicompletion=multicompletion:\
#                                    multicompletion.put(0, trackID),
#                               priority=1)
#            errcompletion = ErrorCompletion(EmptyDatabaseError,
#                                            lambda: doNothing())
#            self._db.getLastPlayedTrackID(
#                lambda trackID, multicompletion=multicompletion:\
#                    multicompletion(1, trackID), errcompletion, priority=1)
##            try:
##                if currentTrackID != self._db.getLastPlayedTrackID():
##                    self._logger.debug("Adding play for current track.")
##                    currentTrack.addPlay(priority=1)
##            except EmptyDatabaseError:
##                pass
#            self._db.getLastPlayedInSeconds(
#                currentTrack,
#                lambda previous, currentTrack=currentTrack:\
#                    currentTrack.setPreviousPlay(previous), priority=1)
#            self.addTrack(currentTrack, select=True)
#        except Errors.NoTrackError:
#            pass

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._onSelectTrack,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._onDeselectTrack,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._onTrackRightClick,
                  self._trackList)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._onTrackActivate,
                  self._trackList)
        self._bindMouseAndKeyEvents(self._trackList)
        
    def _compareTracksCompletion(self, firstTrack, firstTrackID, secondTrackID):
        if firstTrackID != secondTrackID:
            self._logger.debug("Adding play for current track.")
            firstTrack.addPlay(priority=1)

    def _initCreateScoreSlider(self):
        self._logger.debug("Creating score slider.")
        options = wx.SL_LABELS|wx.SL_INVERSE
        if Util.systemName in Util.freebsdNames:
            options = wx.SL_VERTICAL|options
        else:
            options=wx.SL_RIGHT|options
        self._scoreSlider = wx.Slider(self._panel, wx.NewId(), 0, -10, 10,
                                      style=options)

        self.Bind(wx.EVT_SCROLL_CHANGED, self._onScoreSliderMove,
                  self._scoreSlider)
        self.Bind(wx.EVT_SCROLL_THUMBRELEASE, self._onScoreSliderMove,
                  self._scoreSlider)
        self._bindMouseAndKeyEvents(self._scoreSlider)

    def _initCreateLogPanel(self):
        self._logger.debug("Creating log panel.")
        self._logPanel = wx.TextCtrl(
            self._panel, wx.NewId(),
            style=wx.TE_READONLY|wx.TE_MULTILINE|wx.TE_DONTWRAP, size=(-1,100))

        font = wx.Font(9, wx.MODERN, wx.NORMAL, wx.NORMAL)
        self._logPanel.SetFont(font)

        self._redirectOut = Util.RedirectOut(self._logPanel, sys.stdout)
        self._redirectErr = Util.RedirectErr(self._logPanel, sys.stderr)
        sys.stdout = self._redirectOut
        sys.stderr = self._redirectErr
        
        self._bindMouseAndKeyEvents(self._logPanel)
        
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
            menuItem = menu.Append(
                wx.NewId(), "Rate as " + str(score),
                " Set the score of the selected track to " + str(score))

            self.Bind(wx.EVT_MENU, lambda e, score=score:
                      self._onRate(e, score), menuItem)
            
    def _onTrackRightClick(self, e):
        self._eventLogger("GUI Track Right Click", e)
        self.resetInactivityTimer()
        self._logger.debug("Popping up track right click menu.")
        point = e.GetPoint()

        self.PopupMenu(self._trackRightClickMenu, point)
        
    def _onTrackActivate(self, e):
        self._eventLogger("GUI Track Activate", e)
        self._onRequeueAndPlay()
        
    def _onAboutCompletion(self, number, numberUnplayed, totals, oldest):
        self._logger.debug("Opening about dialog.")
        text = "\t  For all your NQing needs!\n"
        text += "\thttp://nqr.googlecode.com/\n\n"
        text += "\t              Version - " + Util.versionNumber + "\n\n\n"
        text += str(number) + " tracks in library:\n\n"
        
        scoreTableTitle = "\t     score\t|       number\n\t\t|\n"
        scoreTable = ""
        numberScored = 0
        for total in totals:
            numberScored += total[1]
            score = str(total[0])
            if score[0] != "-":
                score = " " + score
            scoreTable = ("\t       " + score + "\t|            "
                          + str(total[1]) + "\n" + scoreTable)
            
        text += "- " + str(number - numberScored) + " unscored\n"
        text += "- " + str(numberUnplayed) + " unplayed\n"
        text += ("- oldest unplayed track is roughly "
                 + str(Util.roughAge(oldest)) + "\n          ("+str(oldest)
                 + " seconds) old\n\n\n")
        text += scoreTableTitle + scoreTable

        dialog = wx.MessageDialog(self, text, "NQr", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def _onAbout(self, e):
        self._eventLogger("GUI About Dialog", e)
        multicompletion = Util.MultiCompletion(4, self._onAboutCompletion)
        self._db.getNumberOfTracks(
            lambda thisCallback, number, multicompletion=multicompletion:
                multicompletion(0, number),
            priority=1)
        self._db.getNumberOfUnplayedTracks(
            lambda thisCallback, numberUnplayed,
            multicompletion=multicompletion:
                multicompletion(1, numberUnplayed),
            priority=1)
        self._db.getScoreTotals(
            lambda thisCallback, totals, multicompletion=multicompletion:
                multicompletion(2, totals),
            priority=1)
        self._db.getOldestLastPlayed(
            lambda thisCallback, oldest, multicompletion=multicompletion:
                multicompletion(3, oldest),
            priority=1)
        
    def _onPrefs(self, e):
        self._eventLogger("GUI Prefs Dialog", e)
        self._logger.debug("Opening preferences window.")
        self._prefsWindow = self._prefsFactory.getPrefsWindow(self)
        self._prefsWindow.Show()
        
    def _onRestoreSettings(self, e):
        self._eventLogger("GUI Restore Settings", e)
        dialog = wx.MessageDialog(
            self,
            "Are you sure you wish to restore default settings?\n"
            + "(Settings will be backed up, overwriting old backups)",
            "NQr", wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION)
        if dialog.ShowModal() == wx.ID_YES:
            self._prefsFactory.restoreDefaults()
        dialog.Destroy()

    # TODO: Change buttons to say "import" rather than "open"/"choose"?
    def _onAddFile(self, e):
        self._eventLogger("GUI Add File Dialog", e)
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
        self._eventLogger("GUI Add Directory Dialog", e)
        self._logger.debug("Opening add directory dialog.")
        if Util.systemName in Util.freebsdNames:
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
        self._eventLogger("GUI Add Directory Once Dialog", e)
        self._logger.debug("Opening add directory once dialog.")
        if Util.systemName in Util.freebsdNames:
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
        self._eventLogger("GUI Remove Directory Dialog", e)
        self._logger.debug("Opening remove directory dialog.")
        if Util.systemName in Util.freebsdNames:
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
        if e:
            self._eventLogger("GUI Rescan", e)
        self._logger.debug("Rescanning watch list for new files.")
        self._db.rescanDirectories()

    # TODO: Make linking files simpler, possibly side by side selection or order
    #       sensitive multiple selection?
    def _onLinkTracks(self, e):
        self._eventLogger("GUI Add Link Dialog", e)
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
        
    def _onRemoveLinkCompletion(self, linkID, firstTrack, secondTrack,
                                traceCallback=None):
        if linkID != None:
            self._db.removeLink(firstTrack, secondTrack,
                                traceCallback=traceCallback)
        else:
            self._db.removeLink(secondTrack, firstTrack,
                                traceCallback=traceCallback)
            
    # TODO: Make removing links select from a list of current links.
    def _onRemoveLink(self, e):
        self._eventLogger("GUI Remove Link Dialog", e)
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
                    lambda thisCallback, linkID, firstTrack=firstTrack,
                    secondTrack=secondTrack:
                        self._onRemoveLinkCompletion(linkID, firstTrack,
                                                     secondTrack, thisCallback))
            secondDialog.Destroy()
        firstDialog.Destroy()
        
    def _onScoreChangeCompletion(self, track, oldScore, newScore,
                                 warnings=False, traceCallback=None):
        if oldScore != newScore:
            self._logger.debug(
                "Setting the track's score to " + str(newScore) + ".")
            track.setScore(newScore, traceCallback=traceCallback)
            self.refreshSelectedTrackScore(traceCallback=traceCallback)
        elif warnings == True:
            self._logger.warning("Track already has that score!")

    def _onScoreSliderMove(self, e):
        self._eventLogger("GUI Score Slider Move", e)
        self.resetInactivityTimer()
        try:
            self._logger.debug(
                "Score slider has been moved. Retrieving new score.")
            score = self._scoreSlider.GetValue()
            self._track.getScore(
                lambda thisCallback, oldScore, track=self._track, score=score:
                    self._onScoreChangeCompletion(track, oldScore, score,
                                                  thisCallback),
                priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def setScoreSliderPosition(self, score):
        self._logger.debug("Setting score slider to " + str(score) + ".")
        self._scoreSlider.SetValue(score)
        
    def _onRateUpCompletion(self, track, score, traceCallback=None):
        if score != 10:
            self._logger.debug("Increasing track's score by 1.")
            track.setScore(score + 1, traceCallback=traceCallback)
            self.refreshSelectedTrackScore(traceCallback=traceCallback)
        else:
            self._logger.warning("Track already has maximum score.")

    def _onRateUp(self, e):
        self._eventLogger("GUI Rate Up", e)
        self.resetInactivityTimer()
        try:
            self._track.getScoreValue(
                lambda thisCallback, score, track=self._track:
                    self._onRateUpCompletion(track, score, thisCallback),
                priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return
        
    def _onRateDownCompletion(self, track, score, traceCallback=None):
        if score != -10:
            self._logger.debug("Decreasing track's score by 1.")
            track.setScore(score-1, traceCallback=traceCallback)
            self.refreshSelectedTrackScore(traceCallback=traceCallback)
        else:
            self._logger.warning("Track already has minimum score.")

    def _onRateDown(self, e):
        self._eventLogger("GUI Rate Down", e)
        self.resetInactivityTimer()
        try:
            self._track.getScoreValue(
                lambda thisCallback, score, track=self._track:
                    self._onRateDownCompletion(track, score, thisCallback),
                priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onRate(self, e, score):
        self._eventLogger("GUI Rate", e)
        self.resetInactivityTimer()
        try:
            self._track.getScore(
                lambda thisCallback, oldScore, track=self._track, score=score:
                    self._onScoreChangeCompletion(track, oldScore, score,
                                                  warnings=True,
                                                  traceCallback=thisCallback),
                priority=1)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onResetScore(self, e):
        self._eventLogger("GUI Reset Score", e)
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
        self._eventLogger("GUI Tag", e)
        self.resetInactivityTimer()
        try:
            tagID = e.GetId()
            if self._tagMenu.IsChecked(tagID) == True: # Since clicking checks.
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
        self._eventLogger("GUI New Tag", e)
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
                    tagID, tag, " Tag track with " + tag)
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
        self._eventLogger("GUI Exit", e)
        self._logger.debug("Exiting NQr.")
        self.Close(True)

    def _onClose(self, e):
        self._eventLogger("GUI Close", e)
        interrupt = None
        locks = ([self._trackMonitor.getRunningLock()]
                 + self._socketMonitor.getRunningLocks())
        if self._db.getDirectoryWalking():
            options = wx.YES_NO|wx.NO_DEFAULT|wx.ICON_QUESTION
            if e.CanVeto():
                options = options|wx.CANCEL
            dialog = wx.MessageDialog(
                self,
                "NQr may be performing non-essential database operations such"
                + " as adding files or rescanning the database. Do you want"
                + " to stop these operations from completing?\n\n"
                + "(Pressing \'No\' will close NQr, but allow the database"
                + " operations to complete in the background)", "NQr", options)
            userChoice = dialog.ShowModal()
            if userChoice == wx.ID_NO:
                interrupt = False
            elif userChoice == wx.ID_YES:
                interrupt = True
            elif userChoice == wx.ID_CANCEL:
                dialog.Destroy()
                e.Veto()
                return
            dialog.Destroy()
        self._optionsMenu.Check(self._ID_TOGGLENQR, False)
        if self._trackMonitor:
            self._trackMonitor.abort()
        self._inactivityTimer.Stop()
        self._refreshTimer.Stop()
        if interrupt == None:
            locks += self._db.getThreadRunningLocks()
            self._db.abort()
        elif interrupt:
            locks += self._db.getThreadRunningLocks()
            self._db.abort(True)
        else:
            self._db.abort(False)
        if self._haveLogPanel == True:
            sys.stdout = self._stdout
            sys.stderr = self._stderr
            self._loggerFactory.refreshStreamHandler()
        self._socketMonitor.abort()
        self._saveWindowAndColumnSizes()
        
        for lock in locks:
            lock.acquire()
        self.Destroy()
        # FIXME: self.ScheduleForDestruction() added in wxPython 2.9.

    def _onMouseOrKeyPress(self, e):
        try:
            if e.Moving() or e.Leaving() or e.Entering():
                e.Skip()
                return
        except AttributeError as err:
            if "\'KeyEvent\' object has no attribute" not in str(err):
                raise err
        self._eventLogger("GUI Mouse or Key Press", e)
        self.resetInactivityTimer()
        e.Skip()
        
    def _onLaunchPlayer(self, e):
        self._eventLogger("GUI Launch Player", e)
        self._trackMonitorQueue(lambda thisCallback: self._player.launch())

    def _onExitPlayer(self, e):
        self._eventLogger("GUI Exit Player", e)
        self._trackMonitorQueue(lambda thisCallback: self._player.close())

    def _onNext(self, e):
        self._eventLogger("GUI Next Track", e)
        self._trackMonitorQueue(lambda thisCallback: self._player.nextTrack())
        self.resetInactivityTimer(2000*self._trackCheckDelay)

    def _onPause(self, e):
        self._eventLogger("GUI Pause", e)
        self._trackMonitorQueue(lambda thisCallback: self._player.pause())
        self.resetInactivityTimer(1)

    def _onPlay(self, e):
        self._eventLogger("GUI Play", e)
        self._trackMonitorQueue(lambda thisCallback: self._player.play())
        self.resetInactivityTimer(1)

    def _onPrevious(self, e):
        self._eventLogger("GUI Previous Track", e)
        self._trackMonitorQueue(
            lambda thisCallback: self._player.previousTrack())
        self.resetInactivityTimer(2000*self._trackCheckDelay)

    def _onStop(self, e):
        self._eventLogger("GUI Stop", e)
        self._trackMonitorQueue(lambda thisCallback: self._player.stop())
        self.resetInactivityTimer(1)
        
    def _onSelectCurrent(self, e):
        self._eventLogger("GUI Select Current", e)
        self.selectTrack(0)

    def _onRequeue(self, e):
        self._eventLogger("GUI Requeue", e)
        self.resetInactivityTimer()
        try:
            self._logger.info("Requeueing track.")
            self._trackMonitorQueue(
                lambda thisCallback, track=self._track: self._player.addTrack(
                    track.getPath()))
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _onRequeueAndPlayCompletion(self, path):
        position = self._player.getCurrentTrackPos() + 1
        self._player.insertTrack(path, position)
        self._player.playAtPosition(position)
        
    def _onRequeueAndPlay(self, e=None):
        if e:
            self._eventLogger("GUI Requeue and Play", e)
        self.resetInactivityTimer()
        try:
            self._logger.info("Requeueing track and playing it.")
            path = self._track.getPath()
            self._trackMonitorQueue(
                lambda thisCallback, path=path:
                    self._onRequeueAndPlayCompletion(path))
            self.resetInactivityTimer(2000*self._trackCheckDelay)
        except AttributeError as err:
            if str(err) != "'MainWindow' object has no attribute '_track'":
                raise err
            self._logger.error("No track selected.")
            return

    def _getShuffleCompletion(self):
        self._oldShuffleStatus = self._player.getShuffle()

    def _savePlaylistCompletion(self, traceCallback):
        self._oldPlaylist = self._player.savePlaylist(
            traceCallback=traceCallback)

    def _onToggleNQr(self, e=None, startup=False):
        if e:
            self._eventLogger("GUI Toggle NQr", e)
        self._logger.debug("Toggling NQr.")
        if self._optionsMenu.IsChecked(self._ID_TOGGLENQR) == False:
            self._toggleNQr = False
            self._logger.info("Restoring shuffle status.")
            self._trackMonitorQueue(
                lambda thisCallback, status=self._oldShuffleStatus:
                    self._player.setShuffle(status))
            if self._restorePlaylist == True and self._oldPlaylist != None:
                self._trackMonitorQueue(
                    lambda thisCallback, playlist=self._oldPlaylist:
                        self._player.loadPlaylist(playlist,
                                                  traceCallback=thisCallback))
            self._logger.info("Enqueueing turned off.")
        elif self._optionsMenu.IsChecked(self._ID_TOGGLENQR) == True:
            self._toggleNQr = True
            self._logger.info("Storing shuffle status.")
            self._trackMonitorQueue(
                lambda thisCallback: self._getShuffleCompletion())
            self._trackMonitorQueue(
                lambda thisCallback: self._player.setShuffle(False))
            # FIXME: Possibly shouldn't restore the playlist ever?
            if self._restorePlaylist == True:
                self._trackMonitorQueue(
                    lambda thisCallback: self._savePlaylistCompletion(
                        thisCallback))
            self._logger.info("Enqueueing turned on.")
            if startup == False:
                self.maintainPlaylist()
                
    def _onDump(self, e):
        self._eventLogger("GUI Dump", e)
        self._eventLogger.dump(self._dumpPath + "GUIEvents.dump")
        self._trackMonitor.dumpQueue(self._dumpPath + "TrackMonitorQueue.dump")
        self._db.dumpQueues(self._dumpPath)
        
    def _onClearCache(self, e): # TODO: Should also refresh tracks?
        self._eventLogger("GUI Clear Track Cache", e)
        self._trackFactory.clearCache()
                
    def _onTrackChangeCompletion(self, track, previousPlay, traceCallback):
        track.setPreviousPlay(previousPlay)
        # FIXME: Needs to ignore first track if it was last play before closing.
        self._playTimer.Stop()
        if self._playTimer.Start(self._playDelay, oneShot=True) == False:
            # Ensures play is added for track.
            track.addPlay(priority=1)
        self.addTrack(track)
        self.maintainPlaylist(traceCallback=traceCallback)

    def _onTrackChange(self, e):
        self._eventLogger("GUI Track Change", e)
        self._playingTrack = e.getTrack()
        self._db.getLastPlayedInSeconds(
            self._playingTrack,
            lambda thisCallback, previousPlay, track=self._playingTrack:
                self._onTrackChangeCompletion(track, previousPlay,
                                              thisCallback),
            traceCallback=e.getCallback(), priority=1)
    
    def _onNoNextTrack(self, e):
        self._eventLogger("GUI No Next Track", e)
        self.maintainPlaylist(traceCallback=e.getCallback())
        
    def _onRequestAttention(self, e):
        self._eventLogger("GUI Request Attention", e)
        self._logger.debug("Requesting user attention.")
        # FIXME: Possibly use wx.USER_ATTENTION_ERROR as arg?
        self.RequestUserAttention()
        
    def _onLog(self, e):
        self._eventLogger("GUI Log", e)
        e.doLog()
        
    def _onPlayTimerDingCompletion(self, track, traceCallback):
        if track == self._playingTrack:
            self.refreshLastPlayed(0, track, traceCallback=traceCallback)
            if track == self._playingTrack:
                self.refreshPreviousPlay(0, track)
            else:
                self.refreshPreviousPlay(1, track)
        else:
            self.refreshLastPlayed(1, track, traceCallback=traceCallback)
            self.refreshPreviousPlay(1, track)
        if self._track == track:
            self.populateDetails(track, traceCallback)

    def _onPlayTimerDing(self, e):
        self._eventLogger("GUI Play Timer Ding", e)
        track = self._playingTrack
        track.addPlay(
            self._playDelay,
            lambda thisCallback, playCount, track=track:
                self._onPlayTimerDingCompletion(track, thisCallback),
            priority=1)

    def _onInactivityTimerDing(self, e):
        self._eventLogger("GUI Inactivity Timer Ding", e)
        if self._index != 0:
            self.selectTrack(0)
            
    def _onRefreshTimerDing(self, e):
        self._eventLogger("GUI Refresh Timer Ding", e) # FIXME: Possibly remove?
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
                lambda thisCallback, track, index=index:
                    self.refreshPreviousPlay(index, track),
                priority=1)

    def resetInactivityTimer(self, time=None):
        self._logger.debug("Restarting inactivity timer.")
        if time == None:
            time = self._inactivityTime
        self._inactivityTimer.Start(time, oneShot=False)

    def _cropCompletion(self, traceCallback):
        trackPosition = self._player.getCurrentTrackPos(traceCallback)
        if trackPosition > self._defaultTrackPosition:
            self._player.cropPlaylist(
                trackPosition - self._defaultTrackPosition)

    def _enqueueRandomCompletion(self, traceCallback):
        playlistLength = self._player.getPlaylistLength()
        if playlistLength < self._defaultPlaylistLength:
            self.postEvent(
                Events.EnqueueRandomEvent(
                    self._defaultPlaylistLength - playlistLength,
                    traceCallback))

    def maintainPlaylist(self, traceCallback=None):
        if self._toggleNQr == True:
            self._logger.debug("Maintaining playlist.")
            self._trackMonitorQueue(
                lambda thisCallback: self._cropCompletion(thisCallback),
                traceCallback)
            self._trackMonitorQueue(
                lambda thisCallback: self._enqueueRandomCompletion(
                    thisCallback),
                traceCallback)
                
    def _onSelectTrackCompletion(self, track, traceCallback):
        self._track = track
        self.populateDetails(self._track, traceCallback)
        self._track.getScoreValue(
            lambda thisCallback, score: self.setScoreSliderPosition(score),
            priority=1, traceCallback=traceCallback)

    def _onSelectTrack(self, e):
        self._eventLogger("GUI Track Selected", e)
        self.resetInactivityTimer()
        self._logger.debug("Track has been selected.")
        self._logger.debug("Retrieving selected track's information.")
        self._trackID = e.GetData()
        self._index = e.GetIndex()
        self._trackFactory.getTrackFromID(
            self._db, self._trackID,
            lambda thisCallback, track: self._onSelectTrackCompletion(
                track, thisCallback), priority=1)
        

    def _onDeselectTrack(self, e):
        self._eventLogger("GUI Track Deselected", e)
        self.resetInactivityTimer()
        self._logger.debug("Track has been deselected.")
        self.clearDetails()

    def addTrack(self, track, select=False, traceCallback=None):
        self.addTrackAtPos(track, 0, select=select, traceCallback=traceCallback)
        
    def _addTrackAtPosCompletion(self, index, track, isScored, lastPlayed,
                                 score, scoreValue, trackID, select=False):
        self._logger.debug("Adding track to track playlist.")
        if isScored == False:
            score = "(" + str(scoreValue) + ")"
        else:
            score = str(score)
        if lastPlayed == None:
            lastPlayed = "-"
        self._trackList.InsertStringItem(index, track.getArtist())
        self._trackList.SetStringItem(index, 1, track.getTitle())
        self._trackList.SetStringItem(index, 2, score)
        self._trackList.SetStringItem(index, 3, lastPlayed)
        previous = track.getPreviousPlay()
        if previous != None:
            self._trackList.SetStringItem(index, 4,
                                          Util.roughAge(time.time() - previous))
        weight = track.getWeight()
        if weight != None:
            self._trackList.SetStringItem(index, 5, str(weight))
        self._trackList.SetItemData(index, trackID)
        if select == True:
            self.selectTrack(index)
        elif self._index >= index:
            self._index += 1
            
    def addTrackAtPos(self, track, index, select=False, traceCallback=None):
        multicompletion = Util.MultiCompletion(
            5,
            lambda isScored, lastPlayed, score, scoreValue, trackID,
            index=index, track=track, select=select:
                self._addTrackAtPosCompletion(index, track, isScored,
                                              lastPlayed, score, scoreValue,
                                              trackID, select=select),
            traceCallback)
        
        track.getIsScored(
            lambda thiscallback, isScored, multicompletion=multicompletion:
                multicompletion(0, isScored),
            priority=1, traceCallback=traceCallback)
        track.getLastPlay(
            lambda thisCallback, lastPlayed, multicompletion=multicompletion:
                multicompletion(1, lastPlayed),
            priority=1, traceCallback=traceCallback)
        track.getScore(
            lambda thisCallback, score, multicompletion=multicompletion:
                multicompletion(2, score),
            priority=1, traceCallback=traceCallback)
        track.getScoreValue(
            lambda thisCallback, scoreValue, multicompletion=multicompletion:
                multicompletion(3, scoreValue),
            priority=1, traceCallback=traceCallback)
        track.getID(
            lambda thisCallback, trackID, multicompletion=multicompletion:
                multicompletion(4, trackID),
            priority=1, traceCallback=traceCallback)
        

    def enqueueTrack(self, track, traceCallback=None):
        path = track.getPath()
        self._logger.debug("Enqueueing \'" + path + "\'.")
        self._trackMonitorQueue(
            lambda thisCallback: self._player.addTrack(path), traceCallback)

    def _onEnqueueRandomTracks(self, e):
        self._eventLogger("GUI Enqueue Random", e)
        self.enqueueRandomTracks(e.getNumber(), e.getCallback(), e.getTags())

    def _onChooseTracks(self, e):
        self._eventLogger("GUI Choose Random", e)
        self._randomizer.chooseTracks(e.getNumber(), e.getExclude(),
                                      e.getCompletion(), e.getCallback(),
                                      e.getTags())

    def enqueueRandomTracks(self, number, traceCallback=None, tags=None):
        if self._enqueueing:
            self._logger.debug("Already enqueuing")
            return
        self._enqueueing = True
        self._trackMonitor.setEnqueueing(True)
        self._logger.debug(
            "Enqueueing " + str(number) + " random track" + Util.plural(number)
            + ".")
        self._trackMonitorQueue(
            lambda thisCallback: self._player.getUnplayedTrackIDs(
                self._db,
                lambda callback, exclude, number=number, tags=tags:
                    self.postEvent(
                        Events.ChooseTracksEvent(
                            number, exclude,
                            lambda anotherCallback, tracks:
                                self._enqueueRandomTracksCompletion(
                                    tracks, traceCallback=anotherCallback),
                            callback, tags)),
                thisCallback),
            traceCallback)

    def _enqueueRandomTracksCompletion(self, tracks, traceCallback=None):
        self._logger.debug("Checking tracks for links.")
        self._enqueueing = False # FIXME: Perhaps set at the end?
        self._trackMonitor.setEnqueueing(False)
        for track in tracks:
            self.enqueueTrack(track, traceCallback=traceCallback)
            # FIXME: Needs links to be made async - started in Database.
            # FIXME: Untested!! Possibly most of the legwork should be done in
            #        db.getLinkIDs().
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

    def refreshSelectedTrack(self, traceCallback=None):
        self._logger.debug("Refreshing selected track.")
        self.refreshTrack(self._index, self._track, traceCallback=traceCallback)
        self._track.getScore(
            lambda thisCallback, score: self.setScoreSliderPosition(score),
            priority=1, traceCallback=traceCallback)
        self.populateDetails(self._track, traceCallback=traceCallback)

    def refreshSelectedTrackScore(self, traceCallback=None):
        self.refreshScore(self._index, self._track, traceCallback=traceCallback)
        self._track.getScoreValue(
            lambda thisCallback, score: self.setScoreSliderPosition(score),
            priority=1, traceCallback=traceCallback)
        self.populateDetails(self._track, traceCallback=traceCallback)

    def refreshTrack(self, index, track, traceCallback=None):
        self.refreshArtist(index, track)
        self.refreshTitle(index, track)
        self.refreshScore(index, track, traceCallback=traceCallback)
        self.refreshLastPlayed(index, track, traceCallback=traceCallback)
        self.refreshPreviousPlay(index, track)

    def refreshArtist(self, index, track):
        self._trackList.SetStringItem(index, 0, track.getArtist())
        self._trackList.RefreshItem(index)

    def refreshTitle(self, index, track):
        self._trackList.SetStringItem(index, 1, track.getTitle())
        self._trackList.RefreshItem(index)
        
    def _refreshScoreCompletion(self, index, isScored, scoreValue, score):
        if isScored == False:
            score = "(" + str(scoreValue) + ")"
        else:
            score = str(score)
        self._trackList.SetStringItem(index, 2, score)
        self._trackList.RefreshItem(index)

    def refreshScore(self, index, track, traceCallback=None):
        multicompletion = Util.MultiCompletion(
            3,
            lambda isScored, scoreValue, score, index=index:
                self._refreshScoreCompletion(index, isScored, scoreValue,
                                             score),
            traceCallback=traceCallback)
        track.getIsScored(
            lambda thisCallback, isScored, multicompletion=multicompletion:
                multicompletion(0, isScored),
            priority=1, traceCallback=traceCallback)
        track.getScoreValue(
            lambda thisCallback, scoreValue, multicompletion=multicompletion:
                multicompletion(1, scoreValue),
            priority=1, traceCallback=traceCallback)
        track.getScore(
            lambda thisCallback, score, multicompletion=multicompletion:
                multicompletion(2, score),
            priority=1, traceCallback=traceCallback)
        
    def _refreshLastPlayedCompletion(self, index, lastPlayed):
        if lastPlayed == None:
            lastPlayed = "-"
        self._trackList.SetStringItem(index, 3, lastPlayed)
        self._trackList.RefreshItem(index)

    def refreshLastPlayed(self, index, track, traceCallback=None):
        track.getLastPlay(
            lambda thisCallback, lastPlayed, index=index:
                self._refreshLastPlayedCompletion(index, lastPlayed),
            priority=1, traceCallback=traceCallback)

    def refreshPreviousPlay(self, index, track):
        previous = track.getPreviousPlay()
        if previous != None:
            self._trackList.SetStringItem(index, 4,
                                          Util.roughAge(time.time() - previous))
        self._trackList.RefreshItem(index)

    def selectTrack(self, index):
        self._logger.debug("Selecting track in position " + str(index) + ".")
        try:
            self._trackList.SetItemState(
                index, wx.LIST_STATE_SELECTED|wx.LIST_STATE_FOCUSED, -1)
            self._trackList.EnsureVisible(index)
        except wx.PyAssertionError as err:
            if "invalid list ctrl item index in SetItem" not in str(err):
                raise err
        
    def _populateDetailsCompletion(self, track, score, playCount, lastPlayed,
                                   tags):
        detailString = ("Artist:  \t" + track.getArtist()
                        + "\nTitle:  \t"+track.getTitle()
                        + "\nAlbum:  \t"+track.getAlbum()
                        + "\nTrack:  \t"+track.getTrackNumber()
                        + "    \tLength:  \t" + track.getLengthString())
            
        bpm = track.getBPM()
        if bpm != "-":
            detailString += "\nBPM:  \t" + bpm
            
        detailString += ("\nScore:  \t" + str(score)
                         + "\nPlay Count:    " + str(playCount))
            
        if lastPlayed != None:
            detailString += "    \tPlayed at:  \t" + lastPlayed
            
        tagString = self.updateTagMenu(tags)
        if tagString != "":
            detailString += "\nTags:  \t" + tagString
            
        detailString += "\nFilepath:      " + track.getPath()
        
        self.clearDetails()
        
        self._logger.debug("Populating details panel.")
        self.addToDetails(detailString)
        self._details.SetInsertionPoint(0)
        
    # FIXME: The first populateDetails seems to produce a larger font than
    #        subsequent calls in Mac OS.
    def populateDetails(self, track, traceCallback=None):
        self._logger.debug("Collecting details for details panel.")
        multicompletion = Util.MultiCompletion(
            4,
            lambda score, playCount, lastPlayed, tags, track=track:\
                self._populateDetailsCompletion(track, score, playCount,
                                                lastPlayed, tags),
            traceCallback)
        
        track.getScore(
            lambda thisCallback, score, multicompletion=multicompletion:
                multicompletion(0, score),
            priority=1, traceCallback=traceCallback)
        track.getPlayCount(
            lambda thisCallback, playCount, multicompletion=multicompletion:
                multicompletion(1, playCount),
            priority=1, traceCallback=traceCallback)
        track.getLastPlay(
            lambda thisCallback, lastPlayed, multicompletion=multicompletion:
                multicompletion(2, lastPlayed),
            priority=1, traceCallback=traceCallback)
        track.getTags(
            lambda thisCallback, tags, multicompletion=multicompletion:
                multicompletion(3, tags),
            priority=1, traceCallback=traceCallback)

    def addToDetails(self, detail):
        self._details.AppendText(detail)

    def clearDetails(self):
        self._logger.debug("Clearing details panel.")
        self._details.Clear()

    def setTag(self, track, tagID, traceCallback=None):
        self._logger.debug("Tagging track.")
        self._tagMenu.Check(tagID, True)
        track.setTag(self._allTags[tagID], traceCallback=traceCallback)

    def unsetTag(self, track, tagID, traceCallback=None):
        self._logger.info("Untagging track.")
        self._tagMenu.Check(tagID, False)
        track.unsetTag(self._allTags[tagID], traceCallback=traceCallback)

    def resetTagMenu(self):
        for tagID in self._allTags.keys():
            self._tagMenu.Check(tagID, False)
            
    def updateTagMenu(self, tags):
        self.resetTagMenu()
        tagString = ""
        for tag in tags:
            tagString += tag + ", "
            tagID = self._getTagID(tag)
            self._tagMenu.Check(tagID, True)
        if tagString != "":
            tagString = tagString[:-2]
        return tagString

    def _getTagID(self, tag):
        for (tagID, tagName) in self._allTags.iteritems():
            if tag == tagName:
                return tagID
            
    def _setPositionAndSize(self):
        self.SetDimensions(self._xCoord, self._yCoord, self._width,
                           self._height, wx.SIZE_USE_EXISTING)
            
    def _saveWindowAndColumnSizes(self):
        settings = {}
        windowRect = self.GetScreenRect()
        settings["height"] = windowRect.GetHeight()
        settings["width"] = windowRect.GetWidth()
        settings["xCoord"] = windowRect.GetX()
        settings["yCoord"] = windowRect.GetY()
        settings["artistWidth"] = self._trackList.GetColumnWidth(0)
        settings["titleWidth"] = self._trackList.GetColumnWidth(1)
        settings["scoreWidth"] = self._trackList.GetColumnWidth(2)
        settings["playedAtWidth"] = self._trackList.GetColumnWidth(3)
        settings["lastPlayedWidth"] = self._trackList.GetColumnWidth(4)
        settings["weightWidth"] = self._trackList.GetColumnWidth(5)
        try:
            self._configParser.add_section("GUI")
        except ConfigParser.DuplicateSectionError:
            pass
        for (name, value) in settings.items():
            self._configParser.set("GUI", name, str(value))
        self._prefsFactory.writePrefs()

    def getPrefsPage(self, parent, logger):
        return PrefsPage(
            parent, self._configParser, logger, self._defaultPlayDelay,
            self._defaultInactivityTime, self._defaultIgnore,
            self._defaultHaveLogPanel, self._defaultRescanOnStartup,
            self._defaultDefaultDirectory, self._defaultTrackCheckDelay), "GUI"

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
            self._db.setIgnoreNewTracks(self._ignoreNewTracks)
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
        try:
            self._trackCheckDelay = self._configParser.getfloat(
                "GUI", "trackCheckDelay")
        except ConfigParser.NoOptionError:
            self._trackCheckDelay = self._defaultTrackCheckDelay
        try:
            self._height = self._configParser.getint("GUI", "height")
        except ConfigParser.NoOptionError:
            self._height = 481
        try:
            self._width = self._configParser.getint("GUI", "width")
        except ConfigParser.NoOptionError:
            self._width = 730
        try:
            self._xCoord = self._configParser.getint("GUI", "xCoord")
        except ConfigParser.NoOptionError:
            self._xCoord = 475
        try:
            self._yCoord = self._configParser.getint("GUI", "yCoord")
        except ConfigParser.NoOptionError:
            self._yCoord = 284
        try:
            self._artistWidth = self._configParser.getint("GUI", "artistWidth")
        except ConfigParser.NoOptionError:
            self._artistWidth = 100
        try:
            self._titleWidth = self._configParser.getint("GUI", "titleWidth")
        except ConfigParser.NoOptionError:
            self._titleWidth = 170
        try:
            self._scoreWidth = self._configParser.getint("GUI", "scoreWidth")
        except ConfigParser.NoOptionError:
            self._scoreWidth = 45
        try:
            self._playedAtWidth = self._configParser.getint("GUI",
                                                            "playedAtWidth")
        except ConfigParser.NoOptionError:
            self._playedAtWidth = 120
        try:
            self._lastPlayedWidth = self._configParser.getint("GUI",
                                                              "lastPlayedWidth")
        except ConfigParser.NoOptionError:
            self._lastPlayedWidth = 120
        try:
            self._weightWidth = self._configParser.getint("GUI", "weightWidth")
        except ConfigParser.NoOptionError:
            self._weightWidth = 80


class PrefsPage(Util.BasePrefsPage):
    
    def __init__(self, parent, configParser, logger, defaultPlayDelay,
                 defaultInactivityTime, defaultIgnore, defaultHaveLogPanel,
                 defaultRescanOnStartup, defaultDefaultDirectory,
                 defaultTrackCheckDelay):
        Util.BasePrefsPage.__init__(self, parent, configParser, logger, "GUI",
                                    defaultPlayDelay, defaultInactivityTime,
                                    defaultIgnore, defaultHaveLogPanel,
                                    defaultRescanOnStartup,
                                    defaultDefaultDirectory,
                                    defaultTrackCheckDelay)
        
        self._initCreateDirectorySizer()
        self._initCreatePlayDelaySizer()
        self._initCreateInactivityTimeSizer()
        self._initCreateTrackCheckDelaySizer()
        self._initCreateIgnoreCheckBox()
        self._initCreateRescanCheckBox()
        self._initCreateLogCheckBox()

        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._directorySizer, 0)
        mainSizer.Add(self._playDelaySizer, 0)
        mainSizer.Add(self._inactivityTimeSizer, 0)
        mainSizer.Add(self._trackCheckSizer, 0)
        mainSizer.Add(self._ignoreCheckBox, 0)
        mainSizer.Add(self._rescanCheckBox, 0)
        mainSizer.Add(self._logCheckBox, 0)

        self.SetSizer(mainSizer)
        
    def _initCreateDirectorySizer(self): # FIXME: Make a "choose" dialog.
        self._directorySizer = wx.BoxSizer(wx.HORIZONTAL)

        directoryLabel = wx.StaticText(self, wx.NewId(),
                                       "Default Dialog Directory: ")
        self._directorySizer.Add(directoryLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._directoryControl = wx.TextCtrl(
            self, wx.NewId(), str(self._settings["defaultDirectory"]))
        self._directorySizer.Add(self._directoryControl, 0)

        self._directoryControl.Bind(wx.EVT_KILL_FOCUS, self._onDirectoryChange)

    def _initCreatePlayDelaySizer(self):
        self._playDelaySizer = wx.BoxSizer(wx.HORIZONTAL)

        playDelayLabel = wx.StaticText(self, wx.NewId(), "Play Record Delay: ")
        self._playDelaySizer.Add(playDelayLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)
        
        self._playDelayControl = wx.TextCtrl(
            self, wx.NewId(), str(self._settings["playDelay"]), size=(40,-1))
        self._playDelaySizer.Add(self._playDelayControl, 0)

        playDelayUnits = wx.StaticText(self, wx.NewId(), " milliseconds")
        self._playDelaySizer.Add(playDelayUnits, 0,
                                 wx.RIGHT|wx.TOP|wx.BOTTOM, 3)

        self.Bind(wx.EVT_TEXT, self._onPlayDelayChange,
                  self._playDelayControl)

    def _initCreateInactivityTimeSizer(self):
        self._inactivityTimeSizer = wx.BoxSizer(wx.HORIZONTAL)

        inactivityTimeLabel = wx.StaticText(self, wx.NewId(), "Idle Time: ")
        self._inactivityTimeSizer.Add(inactivityTimeLabel, 0,
                                      wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._inactivityTimeControl = wx.TextCtrl(
            self, wx.NewId(), str(self._settings["inactivityTime"]),
            size=(50,-1))
        self._inactivityTimeSizer.Add(self._inactivityTimeControl, 0)

        inactivityTimeUnits = wx.StaticText(self, wx.NewId(), " milliseconds")
        self._inactivityTimeSizer.Add(inactivityTimeUnits, 0,
                                      wx.RIGHT|wx.TOP|wx.BOTTOM, 3)

        self.Bind(wx.EVT_TEXT, self._onInactivityTimeChange,
                  self._inactivityTimeControl)
        
    def _initCreateTrackCheckDelaySizer(self):
        self._trackCheckSizer = wx.BoxSizer(wx.HORIZONTAL)

        trackCheckLabel = wx.StaticText(self, wx.NewId(),
                                        "Check player for track change every ")
        self._trackCheckSizer.Add(trackCheckLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM,
                                  3)

        self._trackCheckControl = wx.TextCtrl(
            self, wx.NewId(), str(int(self._settings["trackCheckDelay"]*1000)),
            size=(40,-1))
        self._trackCheckSizer.Add(self._trackCheckControl, 0)

        trackCheckUnits = wx.StaticText(self, wx.NewId(), " milliseconds")
        self._trackCheckSizer.Add(trackCheckUnits, 0, wx.RIGHT|wx.TOP|wx.BOTTOM,
                                  3)

        self.Bind(wx.EVT_TEXT, self._onTrackCheckChange,
                  self._trackCheckControl)

    def _initCreateIgnoreCheckBox(self):
        self._ignoreCheckBox = wx.CheckBox(self, wx.NewId(),
                                           "Ignore Tracks not in Database")
        if self._settings["ignoreNewTracks"] == True:
            self._ignoreCheckBox.SetValue(True)
        else:
            self._ignoreCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onIgnoreChange, self._ignoreCheckBox)
        
    def _initCreateRescanCheckBox(self):
        self._rescanCheckBox = wx.CheckBox(self, wx.NewId(),
                                           "Rescan Library on Startup")
        if self._settings["rescanOnStartup"] == True:
            self._rescanCheckBox.SetValue(True)
        else:
            self._rescanCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onRescanChange, self._rescanCheckBox)
        
    def _initCreateLogCheckBox(self):
        self._logCheckBox = wx.CheckBox(self, wx.NewId(), "Show Log Panel")
        if self._settings["haveLogPanel"] == True:
            self._logCheckBox.SetValue(True)
        else:
            self._logCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onLogChange, self._logCheckBox)
        
    def _onDirectoryChange(self, e):
        rawDirectory = self._directoryControl.GetLineText(0)
        directory = os.path.realpath(rawDirectory)
        if Util.validateDirectory(self._directoryControl):
            self._settings["defaultDirectory"] = os.path.realpath(directory)
        else:
            self._directoryControl.ChangeValue(
                self._settings["defaultDirectory"])

    def _onPlayDelayChange(self, e):
        if Util.validateNumeric(self._playDelayControl):
            playDelay = self._playDelayControl.GetLineText(0)
            if playDelay != "":
                self._settings["playDelay"] = int(playDelay)

    def _onInactivityTimeChange(self, e):
        if Util.validateNumeric(self._inactivityTimeControl):
            inactivityTime = self._inactivityTimeControl.GetLineText(0)
            if inactivityTime != "":
                self._settings["inactivityTime"] = int(inactivityTime)
                
    def _onTrackCheckChange(self, e):
        if Util.validateNumeric(self._trackCheckControl):
            trackCheckDelay = self._trackCheckControl.GetLineText(0)
            if trackCheckDelay != "":
                self._settings["trackCheckDelay"] = float(trackCheckDelay/1000)

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
                     defaultDefaultDirectory, defaultTrackCheckDelay):
        self._defaultPlayDelay = defaultPlayDelay
        self._defaultInactivityTime = defaultInactivityTime
        self._defaultIgnore = defaultIgnore
        self._defaultHaveLogPanel = defaultHaveLogPanel
        self._defaultRescanOnStartup = defaultRescanOnStartup
        self._defaultDefaultDirectory = defaultDefaultDirectory
        self._defaultTrackCheckDelay = defaultTrackCheckDelay

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
        try:
            trackCheckDelay = self._configParser.getfloat("GUI",
                                                          "trackCheckDelay")
            self._settings["trackCheckDelay"] = trackCheckDelay
        except ConfigParser.NoOptionError:
            self._settings["trackCheckDelay"] = self._defaultTrackCheckDelay
