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
## TODO: add submenu to player menu and right click menu with e.g. "rate 10"
## TODO: add menu option to turn NQr queueing on/off. When off change trackList
##       behaviour to only show played tracks, not to represent unplayed tracks,
##       or show only 3 future tracks?
## TODO: set up rescan on startup?
## TODO: make add/rescan directory/files a background operation: poss create a
##       thread to check the directory and queue the database to add the file.
## TODO: poss create delay before counting a play (to ignore skips)
## TODO: deal with tracks played not in database (ignore them?)
## TODO: add keyboard shortcuts
## TODO: make NQr only queue tracks up to a limit (rather than 3 tracks every
##       time 3 are played)

##from Database import Database
##from iTunesMacOS import iTunesMacOS
##from Randomizer import Randomizer
from threading import *
import time
##import Track
##from WinampWindows import WinampWindows
import wx

ID_EVT_TRACK_CHANGE = wx.NewId()
ID_EVT_TRACK_QUEUE = wx.NewId()

def EVT_TRACK_CHANGE(window, func):
    window.Connect(-1, -1, ID_EVT_TRACK_CHANGE, func)

class TrackChangeEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_TRACK_CHANGE)
##        self.path = path

##    def getPath(self):
##        return self.path

def EVT_TRACK_QUEUE(window, func):
    window.Connect(-1, -1, ID_EVT_TRACK_QUEUE, func)

class TrackQueueEvent(wx.PyEvent):
    def __init__(self):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_TRACK_QUEUE)

## must be aborted before closing!
class TrackChangeThread(Thread):
    def __init__(self, window, player):
        Thread.__init__(self)
##        self.setDaemon(True)
        self.window = window
        self.player = player
        self.abortFlag = False
        self.start()

## poss should use position rather than filename?
## sometimes gets the wrong track if skipped too fast: should return the path
## with the event
    def run(self):
        currentTrack = self.player.getCurrentTrackPath()
        changeCount = 3
        while True:
            time.sleep(.5)
            newTrack = self.player.getCurrentTrackPath()
            if newTrack != currentTrack:
                currentTrack = newTrack
                wx.PostEvent(self.window, TrackChangeEvent())
                changeCount += 1
            if changeCount == 3:
                wx.PostEvent(self.window, TrackQueueEvent())
                changeCount = 0
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
    
    def __init__(self, parent, db, randomizer, player, trackFactory,
                 title="NQr", enqueueOnStartup=True, rescanOnStartup=True):
##        self.db = DatabaseThread(db).database
        self.db = db
        self.randomizer = randomizer
        self.player = player
        self.trackFactory = trackFactory
        self.enqueueOnStartup = enqueueOnStartup
        self.rescanOnStartup = rescanOnStartup
        self.trackChangeThread = None
        
        wx.Frame.__init__(self, parent, title=title)
        self.CreateStatusBar()
        self.initMenuBar()
        self.initMainSizer()

        EVT_TRACK_CHANGE(self, self.onTrackChange)
        EVT_TRACK_QUEUE(self, self.onEnqueueTracks)
        self.Bind(wx.EVT_CLOSE, self.onClose, self)
        
        if self.enqueueOnStartup == True:
            self.optionsMenu.Check(self.ID_TOGGLENQR, True)
            self.onToggleNQr()

##        if self.rescanOnStartup == True:
##            self.onRescan()

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
        menuAbout = self.fileMenu.Append(wx.ID_ABOUT, "&About NQr",
                                         " Information about NQr")
        self.fileMenu.AppendSeparator()
        menuAddFile = self.fileMenu.Append(self.ID_ADDFILE, "Add &File...",
                                           " Add a file to the library")
        menuAddDirectory = self.fileMenu.Append(self.ID_ADDDIRECTORY,
                                                "Add &Directory...",
                                                " Add a directory to the library and watch list")
        menuAddDirectoryOnce = self.fileMenu.Append(-1,
                                                    "Add Directory &Once...",
                                                    " Add a directory to the library but not the watch list")
        self.fileMenu.AppendSeparator()
        menuRemoveDirectory = self.fileMenu.Append(-1, "&Remove Directory...",
                                                   " Remove a directory from the watch list")
        self.fileMenu.AppendSeparator()
        menuExit = self.fileMenu.Append(wx.ID_EXIT, "E&xit", " Terminate NQr")
        
        self.Bind(wx.EVT_MENU, self.onAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.onAddFile, menuAddFile)
        self.Bind(wx.EVT_MENU, self.onAddDirectory, menuAddDirectory)
        self.Bind(wx.EVT_MENU, self.onAddDirectoryOnce, menuAddDirectoryOnce)
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
                                            " Increase the score of the selected track by one")
        menuRateDown = self.playerMenu.Append(-1, "Rate &Down",
                                               " Decrease the score of the selected track by one")
        self.playerMenu.AppendSeparator()
        menuRequeue = self.playerMenu.Append(-1, "Re&queue Track",
                                             " Add the selected track to the playlist")
        menuResetScore = self.playerMenu.Append(-1, "Reset Sc&ore",
                                                " Reset the score of the selected track")
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
        self.Bind(wx.EVT_MENU, self.onRequeue, menuRequeue)
        self.Bind(wx.EVT_MENU, self.onResetScore, menuResetScore)
        self.Bind(wx.EVT_MENU, self.onLaunchPlayer, menuLaunchPlayer)
        self.Bind(wx.EVT_MENU, self.onExitPlayer, menuExitPlayer)

    def initOptionsMenu(self):
        self.optionsMenu = wx.Menu()        
        menuPrefs = self.optionsMenu.Append(self.ID_PREFS, "&Preferences...",
                                            " Change NQr's settings")
        menuRescan = self.optionsMenu.Append(-1, "&Rescan Library",
                                             " Search previously added directories for new files")
        self.optionsMenu.AppendSeparator()
        menuToggleNQr = self.optionsMenu.AppendCheckItem(self.ID_TOGGLENQR,
                                                         "En&queue with NQr",
                                                         " Use NQr to enqueue tracks")



##        self.Bind(wx.EVT_MENU, self.onPrefs, menuPrefs)
        self.Bind(wx.EVT_MENU, self.onRescan, menuRescan)
        self.Bind(wx.EVT_MENU, self.onToggleNQr, menuToggleNQr)
        
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
        dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                              wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.addDirectory(path)
        dialog.Destroy()

    def onAddDirectoryOnce(self, e):
        defaultDirectory = ''
        dialog = wx.DirDialog(self, "Choose a directory", defaultDirectory,
                              wx.DD_DIR_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            path = dialog.GetPath()
            self.db.addDirectoryNoWatch(path)
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

    def onRequeue(self, e):
        try:
            self.player.addTrack(self.track.getPath())
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

## should always be monitoring track changes, but toggle should turn on/off
## auto queueing
    def onToggleNQr(self, e=None):
        if not self.trackChangeThread:
            self.trackChangeThread = TrackChangeThread(self, self.player)
            print "Enqueueing turned on."
        else:
            self.trackChangeThread.abort()
            self.trackChangeThread = None
            print "Enqueueing turned off."

##    def onPrefs(self, e):

    def onRescan(self, e=None):
        self.db.rescanDirectories()

## should deal with limited cache size
    def onSelectTrack(self, e):
        self.trackID = e.GetData()
        self.index = e.GetIndex()
        self.track = self.trackFactory.getTrackFromCache(self.trackID)
        self.populateDetails(self.track)
        self.setScoreSliderPosition(self.db.getScoreValue(self.track))

##    def onDeselectTrack(self, e):
##        path = currentTrack()
##        self.populateDetails(path)

    def onTrackRightClick(self, e):
        point = e.GetPoint()
        trackRightClickMenu = wx.Menu()
        menuTrackRightClickRateUp = trackRightClickMenu.Append(
            -1, "Rate &Up", " Increase the score of the current track by one")
        menuTrackRightClickRateDown = trackRightClickMenu.Append(
            -1, "Rate &Down", " Decrease the score of the current track by one")
        self.playerMenu.AppendSeparator()
        menuTrackRightClickRequeue = trackRightClickMenu.Append(
            -1, "Re&queue Track", " Add the selected track to the playlist")
##        menuTrackRightClickResetScore = trackRightClickMenu.Append(
##            -1, "Reset Sc&ore", " Reset the score of the current track")
        
        self.Bind(wx.EVT_MENU, self.onRateUp, menuTrackRightClickRateUp)
        self.Bind(wx.EVT_MENU, self.onRateDown, menuTrackRightClickRateDown)
        self.Bind(wx.EVT_MENU, self.onRequeue, menuTrackRightClickRequeue)
##        self.Bind(wx.EVT_MENU, self.onResetScore, menuTrackRightClickResetScore)

        self.PopupMenu(trackRightClickMenu, point)
        trackRightClickMenu.Destroy()

    def onScoreSliderMove(self, e):
        try:
            score = self.scoreSlider.GetValue()
            self.db.setScore(self.track, score)
            self.refreshSelectedTrack()
            self.populateDetails(self.track) ## poss superfluous
        except AttributeError as err:
            if str(err) != "'mainWindow' object has no attribute 'track'":
                raise err
            print "No track selected."
            return

    def onTrackChange(self, e):
        path = self.player.getCurrentTrackPath()
##        path = e.getPath()
        track = self.trackFactory.getTrackFromPath(self.db, path)
        self.db.addPlay(track)
        self.addTrack(track)

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

    def enqueueTrack(self, track):
        self.player.addTrack(track.getPath())

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
        self.addDetail("Artist: "+self.db.getArtist(track))
        self.addDetail("Title: "+self.db.getTitle(track))
        self.addDetail("Track: "+self.db.getTrackNumber(track)\
                       +"     Album: "+self.db.getAlbum(track))
        self.addDetail("Score: "+str(self.db.getScore(track))\
                       +"     Last Played: "+lastPlayed)
        self.addDetail("Filetrack: "+self.db.getPath(track))

    def addDetail(self, detail):
        self.details.AppendText(detail+"\n")

    def clearDetails(self):
        self.details.Clear()

## should queue the correct number of tracks
    def onEnqueueTracks(self, e=None):
        for n in range(3):
            track = self.randomizer.chooseTrack()
            self.enqueueTrack(track)

##app = wx.App(False)
##frame = MainWindow()
##
##frame.Center()
##frame.addTrack(Track.getTrackFromPath(frame.db, "C:/Users/Felix/Documents/Projects/TestDir/01 - Arctic Monkeys - Brianstorm.mp3"))
##frame.addTrack(Track.getTrackFromPath(frame.db, "C:/Users/Felix/Documents/Projects/TestDir/02 - Arctic Monkeys - Teddy Picker.mp3"))
##frame.addTrack(Track.getTrackFromPath(frame.db, frame.player.getCurrentTrackPath()))
##
##app.MainLoop()
