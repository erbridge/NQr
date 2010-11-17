## NQr
##
## TODO: sort out ' and unicode in filenames (done?)
## TODO: allow use of bpm for music queueing (from ID3)
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score
## TODO: ORGANIZE CODE
## TODO: add track with tag retrieval?
## TODO: prevent multiple instances of NQr
## TODO: populate prefs window including customizable score range (with
##       database converter)?
## TODO: read settings from settings file
##
## FIXME: queues wrong track if track changes at time of start up

import ConfigParser
import Database
import getopt
import GUI
import Logger
import os
import platform
import Prefs
import Randomizer
import sys
import traceback
import Track
import wx

class Main(wx.App):
    def __init__(self):
        wx.App.__init__(self, False)
        self._prefsFile = os.path.realpath("settings")

        self._configParser = ConfigParser.SafeConfigParser()
        self._configParser.read(self._prefsFile)

        self._noQueue = False
        self._debugMode = False
        
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
        self._logger.critical("Uncaught exception:\n\n"+"".join([
            line for line in traceback.format_exception(type, value, traceBack)
            ]))
        sys.exit(1)## poss remove for non-dev versions?
##        sys.__excepthook__(type, value, traceBack)
                
    def run(self):
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

        modules = [player, trackFactory, db, randomizer]
        prefsFactory = Prefs.PrefsFactory(self._prefsFile, self._loggerFactory,
                                          modules, self._configParser)
        
        self._logger.debug("Initializing GUI.")
        title = "NQr"
        if self._noQueue:
            title = title + " (no queue)"
        gui = GUI.MainWindow(None, db, randomizer, player, trackFactory, system,
                             self._loggerFactory, prefsFactory,
                             self._configParser, title=title)
        gui.Center()
        self._logger.info("Initialization complete.")
        self._logger.info("Starting main loop.")
        ## TODO: remove command window at this point and stop logging to stream
        ##       if we are not in dev mode
        self._loggerFactory.refreshStreamHandler()
        self.MainLoop()
        
if __name__ == '__main__':
    NQr = Main()
    NQr.run()