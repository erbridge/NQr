# NQr
#
# TODO: Allow use of bpm for music queueing (from ID3)?
# TODO: Allow import of directories with a score.
# TODO: ORGANIZE CODE
# TODO: Add track with tag retrieval?
# TODO: Populate prefs window including customizable score range (with
#	     database converter)?
# TODO: Make refocussing on window reselect current track?
# TODO: Build HTTP server/Android app for remote control.
# TODO: Add undo function.
#
# FIXME: Queues wrong track if track changes at time of start up.
# FIXME: Has problems if library is small, poss due to problems with multiple
#        track addition - possibly fixed?
# FIXME: iTunes only sees tracks in "NQr" playlist.

import ConfigParser
import getopt
import socket
import sys
import threading
import traceback

import GUI
import Logger
import Prefs
import Randomizer
import Database
import Track
import Util

wx = Util.wx


class Main(wx.App):
    
    def __init__(self):
        wx.App.__init__(self, False)
        self._setDefaults()

        self._configParser = ConfigParser.SafeConfigParser()
        self._configParser.read(self._prefsFile)
        
        self.loadSettings()
        
        self._loggerFactory = Logger.LoggerFactory(self._logAge,
                                                   self._debugMode)
        self._logger = self._loggerFactory.getLogger("NQr", "debug")

        sys.excepthook = self._exceptHook

        opts, args = getopt.getopt(sys.argv[1:], "nh", ["no-queue", "help"])
        for opt, arg in opts:
            if opt in ("-n", "--no-queue"):
                self._noQueue = True
            else:
                self._usage()
                sys.exit()
        
    def _usage(self):
        print sys.argv[0], "[-h|--help] [-n|--no-queue]"
        print
        print "-n      Don't queue tracks"

    def _exceptHook(self, type, value, traceBack):
        try:
            trace = value.getTrace()
            if trace != None:
                self._logger.critical(
                    "Uncaught exception:\n\nTraceback (most recent call last):"
                    + "\n" + "".join([
                        line for line in traceback.format_list(trace)
                        + traceback.format_exception_only(type, value)]))
            else:
                self._logger.critical("Uncaught exception:\n\n" + "".join([
                    line for line in traceback.format_exception(type, value,
                                                                traceBack)]))
        except AttributeError as err:
            if "object has no attribute \'getTrace\'" not in str(err):
                raise err
            self._logger.critical("Uncaught exception:\n\n" + "".join([
                line for line in traceback.format_exception(type, value,
                                                            traceBack)]))
        sys.exit(1) # FIXME: Possibly remove for non-dev versions?

    def run(self, socket, address):
        self._logger.debug("Running on " + Util.systemName + ".")
        
        self._logger.debug("Initializing track factory.")
        trackFactory = Track.TrackFactory(self._loggerFactory,
                                          self._configParser, self._debugMode)
        
        player = None
        if self._player == "Winamp":
            self._logger.debug("Loading Winamp module.")
            import WinampWindows
            player = WinampWindows.WinampWindows(self._loggerFactory,
                                                 self._noQueue,
                                                 self._configParser,
                                                 self._defaultPlayer,
                                                 self._safePlayers,
                                                 trackFactory)
            
        elif self._player == "XMMS":
            self._logger.debug("Loading XMMS module.")
            import XMMS
            player = XMMS.XMMS(self._loggerFactory, self._noQueue,
                               self._configParser, self._defaultPlayer,
                               self._safePlayers, trackFactory)
            
        elif self._player == "iTunes" and Util.systemName in Util.macNames:
            self._logger.debug("Loading iTunes module.")
            import iTunesMacOS
            player = iTunesMacOS.iTunesMacOS(self._loggerFactory, self._noQueue,
                                             self._configParser,
                                             self._defaultPlayer,
                                             self._safePlayers, trackFactory)
        
        elif self._player == "iTunes" and Util.systemName in Util.windowsNames:
            self._logger.debug("Loading iTunes module.")
            import iTunesWindows
            player = iTunesWindows.iTunesWindows(self._loggerFactory,
                                                 self._noQueue,
                                                 self._configParser,
                                                 self._defaultPlayer,
                                                 self._safePlayers,
                                                 trackFactory)
            
        eventLogger = Util.EventLogger()

        self._logger.debug("Initializing database.")
        threadLock = threading.Lock()
        db = Database.Database(threadLock, trackFactory, self._loggerFactory,
                               self._configParser, self._debugMode,
                               self._databaseFile, self._defaultDefaultScore,
                               eventLogger)

        self._logger.debug("Initializing randomizer.")
        randomizer = Randomizer.Randomizer(db, trackFactory,
                                           self._loggerFactory,
                                           self._configParser,
                                           self._defaultDefaultScore)

        modules = [player, trackFactory, db, randomizer, self]
        prefsFactory = Prefs.PrefsFactory(self._prefsFile, self._loggerFactory,
                                          modules, self._configParser)
        
        self._logger.debug("Initializing GUI.")
        if self._noQueue:
            self._title += " (no queue)"
            self._defaultEnqueueOnStartup = False
        gui = GUI.MainWindow(None, db, randomizer, player, trackFactory,
                             self._loggerFactory, prefsFactory,
                             self._configParser, socket, address, self._title,
                             threadLock, self._defaultRestorePlaylist,
                             self._defaultEnqueueOnStartup,
                             self._defaultRescanOnStartup,
                             self._defaultPlaylistLength,
                             self._defaultPlayDelay,
                             self._defaultIgnoreNewTracks,
                             self._defaultTrackCheckDelay,
                             self._defaultDumpPath, eventLogger)
        self._logger.info("Initialization complete.")
        self._logger.info("Starting main loop.")
        # TODO: Remove command window at this point and stop logging to stream
        #       if we are not in dev mode (poss just rename to .pyw)?
        self._loggerFactory.refreshStreamHandler()
        self.MainLoop()
        self._logger.info("Main loop stopped.")
        eventLogger.done()
        
    def criticalLog(self, message):
        self._logger.critical(message)
        
    def getPort(self):
        return self._port
        
    def _setDefaults(self):
        self._port = 35636 # FIXME: Ensure this port is not used on this system.
        self._prefsFile = "settings"
        self._databaseFile = "database"
        self._defaultDumpPath = "dumps/"
        self._title = "NQr"
        self._defaultNoQueue = False
        self._defaultDebugMode = False
        if Util.systemName in Util.windowsNames:
            self._safePlayers = ["Winamp", "iTunes"]
            self._defaultPlayer = "Winamp"
        elif Util.systemName in Util.freebsdNames:
            self._safePlayers = ["XMMS"]
            self._defaultPlayer = "XMMS"
        elif Util.systemName in Util.macNames:
            self._safePlayers = ["iTunes"]
            self._defaultPlayer = "iTunes"
        self._defaultDefaultScore = 10
        self._defaultRestorePlaylist = False
        self._defaultEnqueueOnStartup = True
        self._defaultRescanOnStartup = False
        self._defaultPlaylistLength = 11
        self._defaultPlayDelay = 4000
        self._defaultIgnoreNewTracks = False
        self._defaultTrackCheckDelay = 0.5
        self._defaultLogAge = 30
        
    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger,
                         self._defaultDebugMode, self._defaultNoQueue,
                         self._defaultLogAge), "Dev"

    def loadSettings(self):
        try:
            self._configParser.add_section("Main")
        except ConfigParser.DuplicateSectionError:
            pass
        try:
            self._debugMode = self._configParser.getboolean("Main", "debugMode")
        except ConfigParser.NoOptionError:
            self._debugMode = self._defaultDebugMode
        try:
            self._noQueue = self._configParser.getboolean("Main", "noQueue")
        except ConfigParser.NoOptionError:
            self._noQueue = self._defaultNoQueue
        try:
            self._logAge = self._configParser.getint("Main", "logAge")
        except ConfigParser.NoOptionError:
            self._logAge = self._defaultLogAge
        try:
            self._configParser.add_section("Player")
        except ConfigParser.DuplicateSectionError:
            pass
        try:
            self._player = self._configParser.get("Player", "player")
            if self._player not in self._safePlayers:
                self._logger.warning(
                    "Chosen player is not supported. Picking the default.")
                self._player = self._defaultPlayer
        except ConfigParser.NoOptionError:
            self._player = self._defaultPlayer


class PrefsPage(Util.BasePrefsPage):
    
    def __init__(self, parent, configParser, logger, defaultDebugMode,
                 defaultNoQueue, defaultLogAge):
        Util.BasePrefsPage.__init__(self, parent, configParser, logger, "Main",
                                    defaultDebugMode, defaultNoQueue,
                                    defaultLogAge)
        
        self._initCreateLogAgeSizer()
        self._initCreateDebugCheckBox()
        self._initCreateQueueCheckBox()
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._logAgeSizer, 0)
        mainSizer.Add(self._debugCheckBox, 0)
        mainSizer.Add(self._queueCheckBox, 0)
        
        self.SetSizer(mainSizer)
        
    def _initCreateDebugCheckBox(self):
        self._debugCheckBox = wx.CheckBox(self, wx.NewId(), "Debug Mode")
        if self._settings["debugMode"] == True:
            self._debugCheckBox.SetValue(True)
        else:
            self._debugCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onDebugChange, self._debugCheckBox)
        
    def _initCreateQueueCheckBox(self):
        self._queueCheckBox = wx.CheckBox(self, wx.NewId(), "No Queue Mode")
        if self._settings["noQueue"] == True:
            self._queueCheckBox.SetValue(True)
        else:
            self._queueCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onQueueChange, self._queueCheckBox)
        
    def _initCreateLogAgeSizer(self):
        self._logAgeSizer = wx.BoxSizer(wx.HORIZONTAL)

        logAgeLabel = wx.StaticText(self, wx.NewId(), "Keep old logs for ")
        self._logAgeSizer.Add(logAgeLabel, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)
        
        self._logAgeControl = wx.TextCtrl(
            self, wx.NewId(), str(self._settings["logAge"]), size=(40,-1))
        self._logAgeSizer.Add(self._logAgeControl, 0)

        logAgeUnits = wx.StaticText(self, wx.NewId(), " days")
        self._logAgeSizer.Add(logAgeUnits, 0, wx.RIGHT|wx.TOP|wx.BOTTOM, 3)

        self.Bind(wx.EVT_TEXT, self._onLogAgeChange,
                  self._logAgeControl)
        
    def _onDebugChange(self, e):
        if self._debugCheckBox.IsChecked():
            self._settings["debugMode"] = True
        else:
            self._settings["debugMode"] = False
        
    def _onQueueChange(self, e):
        if self._queueCheckBox.IsChecked():
            self._settings["noQueue"] = True
        else:
            self._settings["noQueue"] = False
            
    def _onLogAgeChange(self, e):
        if Util.validateNumeric(self._logAgeControl):
            logAge = self._logAgeControl.GetLineText(0)
            if logAge != "":
                self._settings["logAge"] = int(logAge)

    def _setDefaults(self, defaultDebugMode, defaultNoQueue, defaultLogAge):
        self._defaultDebugMode = defaultDebugMode
        self._defaultNoQueue = defaultNoQueue
        self._defaultLogAge = defaultLogAge

    def _loadSettings(self):
        try:
            debugMode = self._configParser.getboolean("Main", "debugMode")
            self._settings["debugMode"] = debugMode
        except ConfigParser.NoOptionError:
            self._settings["debugMode"] = self._defaultDebugMode
        try:
            noQueue = self._configParser.getboolean("Main", "noQueue")
            self._settings["noQueue"] = noQueue
        except ConfigParser.NoOptionError:
            self._settings["noQueue"] = self._defaultNoQueue
        try:
            logAge = self._configParser.getint("Main", "logAge")
            self._settings["logAge"] = logAge
        except ConfigParser.NoOptionError:
            self._settings["logAge"] = self._defaultLogAge


if __name__ == '__main__':
    NQr = Main()
    sock = socket.socket()
    host = socket.gethostname()
    port = NQr.getPort()
    try:
        sock.bind((host, port))
        NQr.run(sock, (host, port))
    except socket.error as (errno, msg):
        if errno != 10048:
            raise
        NQr.criticalLog("NQr is already running.")
        # TODO: Maybe make running NQr focus - poss see winamp.focus for clues.
        # FIXME: Has windows firewall permission issues...
        sock.connect((host, port))
        message = "ATTEND\n"
        totalSent = 0
        while totalSent < len(message):
            sent = sock.send(message[totalSent:])
            if sent == 0:
                break
            totalSent += sent
        sock.shutdown(2)
        sock.close()
        dialog = wx.MessageDialog(None, "NQr is already running", "NQr", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()
    
