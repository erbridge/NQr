## NQr
## TODO: sort out ' and unicode in filenames
## TODO: allow use of bpm for music queueing (from ID3)
## TODO: allow user to choose default rating of unheard tracks
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score
## TODO: ORGANIZE CODE
## TODO: make all errors go to a log (including python errors)
## TODO: add track with tag retrieval?
##
## FIXME: sometimes when changing the score of a track which was selected a
##        while ago, the track replaces the current track in the track list
##        (poss now fixed)
## FIXME: scores added twice to scores table

import ConfigParser
import Database
import getopt
import GUI
import Logger
import platform
import Prefs
import Randomizer
import sys
import Track
import wx

def usage():
    print sys.argv[0], "[-h|--help] [-n|--no-queue]"
    print
    print "-n      Don't queue tracks"

## this info should be read from a settings file
if __name__ == '__main__':
    prefsFile = "settings"

    configParser = ConfigParser.RawConfigParser()
    configParser.read(prefsFile)
    
    noQueue = False
    debugMode = False
    
    opts, args = getopt.getopt(sys.argv[1:], "nh", ["no-queue", "--help"])
    for opt, arg in opts:
        if opt in ("-n", "--no-queue"):
            noQueue = True
        else:
            usage()
            sys.exit()

    loggerFactory = Logger.LoggerFactory(debugMode=debugMode)
    logger = loggerFactory.getLogger("NQr", "debug")
    
    # Do platform-dependent imports, and choose a player type. For
    # now, we just choose it based on the platform...
    system = platform.system()
    logger.debug("Running on "+system+".")
    player = None
    if system == 'Windows':
        logger.debug("Loading Winamp module.")
        import WinampWindows
        player = WinampWindows.WinampWindows(loggerFactory, noQueue,
                                             configParser)
        ## should be called early
    elif system == 'FreeBSD':
        logger.debug("Loading XMMS module.")
        import XMMS
        player = XMMS.XMMS(loggerFactory, noQueue, configParser)
    elif system == 'Mac OS X':
        logger.debug("Loading iTunes module")
        import iTunesMacOS
        player = iTunesMacOS.iTunesMacOS(noQueue)

    logger.debug("Initializing track factory.")
    trackFactory = Track.TrackFactory(loggerFactory, configParser,
                                      debugMode=debugMode)

    logger.debug("Initializing database.")
    db = Database.Database(trackFactory, loggerFactory, configParser,
                           debugMode=debugMode)

    logger.debug("Initializing randomizer.")
    randomizer = Randomizer.Randomizer(db, trackFactory, loggerFactory,
                                       configParser)

    modules = [player, trackFactory, db, randomizer]
    prefsFactory = Prefs.PrefsFactory(prefsFile, loggerFactory, modules,
                                      configParser)
    
    app = wx.App(False)
    logger.debug("Initializing GUI.")
    title = "NQr"
    if noQueue:
        title = title + " (no queue)"
    gui = GUI.MainWindow(None, db, randomizer, player, trackFactory, system,
                         loggerFactory, prefsFactory, configParser, title=title)
    gui.Center()
    logger.info("Initialization complete.")
    logger.info("Starting main loop.")
    app.MainLoop()
