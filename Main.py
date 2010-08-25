## NQr
## TODO: sort out ' and unicode in filenames
## TODO: allow use of bpm for music queueing (from ID3)
## TODO: allow user to choose default rating of unheard tracks
## TODO: on startup rescan directories for new files or make an option
## TODO: allow import of directories with a score
## TODO: ORGANIZE CODE
## TODO: make all errors go to a log (including python errors)
##
## FIXME: sometimes when changing the score of a track which was selected a
##        while ago, the track replaces the current track in the track list
##        (poss now fixed)
## FIXME: scores added twice to scores table

import Database
import GUI
import Logger
import platform
import Randomizer
import Track
import wx

## this info should be read from a settings file
if __name__ == '__main__':
    debugMode = False
    loggerFactory = Logger.LoggerFactory(debugMode=debugMode)
    logger = loggerFactory.getLogger("NQr", "debug")
    # Do platform-dependent imports, and choose a player type. For
    # now, we just choose it based on the platform...
    system = platform.system()
    logger.debug("Running on "+system+".")
##    print "Running on", system
    player = None
    if system == 'Windows':
        logger.debug("Loading Winamp module.")
        import WinampWindows
        player = WinampWindows.WinampWindows(loggerFactory)
        ## should be called early
    elif system == 'FreeBSD':
        logger.debug("Loading XMMS module.")
        import XMMS
        player = XMMS.XMMS()
    elif system == 'Mac OS X':
        logger.debug("Loading iTunes module")
        import iTunesMacOS
        player = iTunesMacOS.iTunesMacOS()
    logger.debug("Initializing track factory.")
    trackFactory = Track.TrackFactory()
    logger.debug("Initializing database.")
    db = Database.Database(trackFactory, loggerFactory, debugMode=debugMode)
    logger.debug("Initializing randomizer.")
    randomizer = Randomizer.Randomizer(db, trackFactory)
    
    app = wx.App(False)
    logger.debug("Initializing GUI.")
    frame = GUI.MainWindow(None, db=db, randomizer=randomizer, player=player,
                           trackFactory=trackFactory, system=system)
    frame.Center()
    logger.info("Initialization complete.")
    logger.info("Starting main loop.")
    app.MainLoop()
