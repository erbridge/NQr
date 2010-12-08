## NQr
##
## TODO: sort out ' and unicode in filenames (done?)
## TODO: allow use of bpm for music queueing (from ID3)
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score
## TODO: ORGANIZE CODE
## TODO: add track with tag retrieval?
## TODO: populate prefs window including customizable score range (with
##	     database converter)?
## TODO: read settings from settings file
## TODO: make refocussing on window reselect current track
##
## FIXME: queues wrong track if track changes at time of start up

import ConfigParser
import Database
import getopt
import GUI
import Logger
import platform
import Prefs
import Randomizer
import socket
import sys
import traceback
import Track

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

class Main(wx.App):
    def __init__(self):
        wx.App.__init__(self, False)
        self._prefsFile = "settings"

        self._configParser = ConfigParser.SafeConfigParser()
        self._configParser.read(self._prefsFile)

        self._defaultNoQueue = False
        self._defaultDebugMode = False
        
        self.loadSettings()
        
        self._loggerFactory = Logger.LoggerFactory(debugMode=self._debugMode)
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
            if value.trace != None:
                self._logger.critical(
                    "Uncaught exception:\n\nTraceback (most recent call last):"\
                    +"\n"+"".join([
                        line for line in traceback.format_list(value.trace)\
                        +traceback.format_exception_only(type, value)]))
            else:
                self._logger.critical("Uncaught exception:\n\n"+"".join([
                    line for line in traceback.format_exception(type, value,
                                                                traceBack)]))
        except AttributeError as err:
            if "object has no attribute \'trace\'" not in str(err):
                raise
            self._logger.critical("Uncaught exception:\n\n"+"".join([
                line for line in traceback.format_exception(type, value,
                                                            traceBack)]))
        sys.exit(1)## poss remove for non-dev versions?

    def run(self, socket):
        # Do platform-dependent imports, and choose a player type. For
        # now, we just choose it based on the platform...
        system = platform.system()
        self._logger.debug("Running on "+system+".")
        player = None
        if system == 'Windows':
            self._logger.debug("Loading Winamp module.")
            import WinampWindows
            player = WinampWindows.WinampWindows(self._loggerFactory,
                                                 self._noQueue,
                                                 self._configParser)
            ## should be called early
        elif system == 'FreeBSD':
            self._logger.debug("Loading XMMS module.")
            import XMMS
            player = XMMS.XMMS(self._loggerFactory, self._noQueue,
                               self._configParser)
        elif system == 'Mac OS X':
            self._logger.debug("Loading iTunes module.")
            import iTunesMacOS
            player = iTunesMacOS.iTunesMacOS(self._noQueue)

        self._logger.debug("Initializing track factory.")
        trackFactory = Track.TrackFactory(self._loggerFactory,
                                          self._configParser,
                                          debugMode=self._debugMode)

        self._logger.debug("Initializing database.")
        db = Database.Database(trackFactory, self._loggerFactory,
                               self._configParser, debugMode=self._debugMode)

        self._logger.debug("Initializing randomizer.")
        randomizer = Randomizer.Randomizer(db, trackFactory,
                                           self._loggerFactory,
                                           self._configParser)

        modules = [player, trackFactory, db, randomizer, self]
        prefsFactory = Prefs.PrefsFactory(self._prefsFile, self._loggerFactory,
                                          modules, self._configParser)
        
        self._logger.debug("Initializing GUI.")
        title = "NQr"
        if self._noQueue:
            title = title + " (no queue)"
        gui = GUI.MainWindow(None, db, randomizer, player, trackFactory, system,
                             self._loggerFactory, prefsFactory,
                             self._configParser, socket, title=title)
        gui.Center()
        self._logger.info("Initialization complete.")
        self._logger.info("Starting main loop.")
        ## TODO: remove command window at this point and stop logging to stream
        ##       if we are not in dev mode
        self._loggerFactory.refreshStreamHandler()
        self.MainLoop()
        
    def criticalLog(self, message):
        self._logger.critical(message)
        
    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger,
                         self._defaultDebugMode, self._defaultNoQueue), "Dev"

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
        
class PrefsPage(wx.Panel):
    def __init__(self, parent, configParser, logger, defaultDebugMode,
                 defaultNoQueue):
        wx.Panel.__init__(self, parent)
        self._logger = logger
        self._defaultDebugMode = defaultDebugMode
        self._defaultNoQueue = defaultNoQueue
        self._settings = {}
        self._configParser = configParser
        try:
            self._configParser.add_section("Main")
        except ConfigParser.DuplicateSectionError:
            pass
        self._loadSettings()
        self._initCreateDebugCheckBox()
        self._initCreateQueueCheckBox()
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._debugCheckBox, 0)
        mainSizer.Add(self._queueCheckBox, 0)
        
        self.SetSizer(mainSizer)
        
    def _initCreateDebugCheckBox(self):
        self._debugCheckBox = wx.CheckBox(self, -1, "Debug Mode")
        if self._settings["debugMode"] == True:
            self._debugCheckBox.SetValue(True)
        else:
            self._debugCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onDebugChange, self._debugCheckBox)
        
    def _initCreateQueueCheckBox(self):
        self._queueCheckBox = wx.CheckBox(self, -1, "No Queue Mode")
        if self._settings["noQueue"] == True:
            self._queueCheckBox.SetValue(True)
        else:
            self._queueCheckBox.SetValue(False)

        self.Bind(wx.EVT_CHECKBOX, self._onQueueChange, self._queueCheckBox)
        
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

    def savePrefs(self):
        self._logger.debug("Saving player preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set("Main", name, str(value))

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
        
if __name__ == '__main__':
    NQr = Main()
    # I'm not sure what this really does (Felix)
    sock = socket.socket()
    host = socket.gethostname()
    port = 35636 # FIXME: make sure this port is not used on this system
    try:
        sock.bind((host, port))
        NQr.run(sock)
    except socket.error as (errno, msg):
        if errno != 10048:
            raise
        NQr.criticalLog("NQr is already running.")
        # TODO: make running NQr focus
#        # FIXME: has windows permission issues...
#        sock.connect((host, port))
#        sock.send("raise")
        dialog = wx.MessageDialog(None, "NQr is already running", "NQr", wx.OK)
        dialog.ShowModal()
        dialog.Destroy()
    