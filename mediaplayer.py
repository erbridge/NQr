# Base class for media players
#
# TODO: Make all players behave like winamp to allow closing while NQr is
#       running and not keep reopening the player.

import ConfigParser
import os.path

import errors
import util

wx = util.wx


# FIXME: Since it now all runs in the track monitor,
#        needs to have logs post events in classes that inherit from this one.
class MediaPlayer(util.EventPoster):
    
    def __init__(self, loggerFactory, name, noQueue, configParser,
                 defaultPlayer, safePlayers, trackFactory):
        self._logger = loggerFactory.getLogger(name, "debug")
        self._configParser = configParser
        self._defaultPlayer = defaultPlayer
        self._safePlayers = safePlayers
        self._trackFactory = trackFactory
        self.loadSettings()
        self._noQueue = noQueue
        self._eventPoster = False

    def makeEventPoster(self, target, lock):
        util.EventPoster.__init__(self, target, self._logger, lock)
        self._eventPoster = True

    def _sendDebug(self, message):
        if self._eventPoster:
            self.postDebugLog(message)
        else:
            self._logger.debug(message)

    def _sendInfo(self, message):
        if self._eventPoster:
            self.postInfoLog(message)
        else:
            self._logger.info(message)

    def _sendError(self, message):
        if self._eventPoster:
            self.postErrorLog(message)
        else:
            self._logger.error(message)

    def _sendWarning(self, message):
        if self._eventPoster:
            self.postWarningLog(message)
        else:
            self._logger.warning(message)

    def savePlaylist(self, traceCallback=None):
        self._sendDebug("Storing current playlist.")
        playlist = []
        for trackPosition in range(self.getPlaylistLength()):
            playlist.append(self.getTrackPathAtPos(trackPosition,
                                                   traceCallback=traceCallback))
        return playlist

    # FIXME: Sets currently playing track to first track in the list, but
    #        continues to play the old track (fixed with work-around).
    def loadPlaylist(self, playlist, traceCallback=None):
        self._sendDebug("Restoring playlist.")
        currentTrackPath = self.getCurrentTrackPath(traceCallback=traceCallback)
        self.clearPlaylist()
        self.addTrack(currentTrackPath)
        for filepath in playlist:
            self.addTrack(filepath)

    def cropPlaylist(self, number):
        self._sendDebug(
            "Cropping playlist by " + str(number) + " track"
            + util.plural(number) + ".")
        for n in range(number):
            self.deleteTrack(0)
        
    def hasNextTrack(self, traceCallback=None):
#        try:
#            self.getTrackPathAtPos(self.getCurrentTrackPos() + 1, traceCallback)
#            return True
#        except errors.NoTrackError, TypeError:
#            return False
        if self.getPlaylistLength() <= (self.getCurrentTrackPos() + 1):
            return False
        else:
            return True

    # FIXME: Gets confused if the playlist is empty (in winamp): sets currently
    #        playing track to first track in the list, but continues to play the
    #        old track.
    def getCurrentTrackPath(self, traceCallback=None, logging=True):
        return self.getTrackPathAtPos(self.getCurrentTrackPos(), traceCallback,
                                      logging)

    def getTrackPathAtPos(self, trackPosition, traceCallback=None,
                          logging=True):
        """
           Gets filename of track at |trackPosition|.
           
           If |logging| is False, the debug log is not updated.
           
           Result should always be turned into a track object.
        """
        if trackPosition is None:
            raise errors.NoTrackError(trace=util.getTrace(traceCallback))
        path = self._getTrackPathAtPos(trackPosition, traceCallback, logging)
        if path is None:
            return None
        return os.path.realpath(path)
        
    def getUnplayedTrackIDs(self, db, completion, traceCallback=None):
        self._ids = []
        count = 0
        try:
            for pos in range(
                self.getCurrentTrackPos(traceCallback=traceCallback),
                self.getPlaylistLength()):
                    path = self.getTrackPathAtPos(pos,
                                                  traceCallback=traceCallback)
                    db.maybeGetIDFromPath(
                        path,
                        lambda thisCallback, id, db=db, path=path:
                            self._getUnplayedTrackIDsCallback(db, id, path,
                                                              thisCallback),
                        traceCallback=traceCallback)
                    count += 1
        except TypeError:
            pass
        db.complete(
            lambda thisCallback, db=db, count=count, completion=completion:
                self._getUnplayedTrackIDListCompletion(db, count, completion,
                                                       thisCallback),
            traceCallback=traceCallback)
        
    def _getUnplayedTrackIDsCallback(self, db, id, path, traceCallback):
        # The track may be one we don't know added directly to the player.
        mycompletion = lambda thisCallback, trackID: self._ids.append(trackID)
        if id is None:
            db.getTrackID(
                self._trackFactory.getTrackFromPathNoID(
                    db, path, traceCallback=traceCallback), mycompletion,
            traceCallback=traceCallback)
            return
        mycompletion(traceCallback, id)
            
    def _getUnplayedTrackIDListCompletion(self, db, count, completion,
                                          traceCallback):
        if len(self._ids) != count:
            db.complete(
                lambda thisCallback, db=db, count=count, completion=completion:
                    self._getUnplayedTrackIDListCompletion(db, count,
                                                           completion,
                                                           thisCallback),
                traceCallback=traceCallback)
            return
        completion(traceCallback, self._ids)

    def addTrack(self, filepath):
        if self._noQueue:
            self._sendInfo("Not queueing " + filepath)
            return
        self._addTrack(filepath)
        
    def insertTrack(self, filepath, position):
        if self._noQueue:
            self._sendInfo("Not queueing " + filepath)
            return
        self._insertTrack(filepath, position)

    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger,
                         self._defaultPlayer, self._safePlayers), "Player"

    def loadSettings(self):
        pass


class PrefsPage(util.BasePrefsPage):
    
    def __init__(self, parent, configParser, logger, defaultPlayer,
                 safePlayers):
        util.BasePrefsPage.__init__(self, parent, configParser, logger,
                                    "Player", defaultPlayer, safePlayers)
        
        self._initCreatePlayerSizer()
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._playerSizer, 0)

        self.SetSizer(mainSizer)
    
    def _initCreatePlayerSizer(self):
        ID_PLAYER = wx.NewId()
        
        self._playerSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        label = wx.StaticText(self, wx.NewId(), "Player:  \t")
        self._playerSizer.Add(label, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)
        
        if util.SYSTEM_NAME in util.WINDOWS_NAMES:
            self._winampButton = wx.RadioButton(self, ID_PLAYER, "Winamp  \t",
                                                style=wx.RB_GROUP)
            self._playerSizer.Add(self._winampButton, 0, wx.TOP|wx.BOTTOM, 3)
            
            self._iTunesButton = wx.RadioButton(self, ID_PLAYER, "iTunes  \t")
            self._playerSizer.Add(self._iTunesButton, 0, wx.TOP|wx.BOTTOM, 3)
            
            if self._settings["player"] == "Winamp":
                self._winampButton.SetValue(True)
            elif self._settings["player"] == "iTunes":
                self._iTunesButton.SetValue(True)
                
            if not util.getIsInstalled("Winamp"):
                self._winampButton.Enable(False)
            # FIXME: May not be correct display name for iTunes (untested).
            if not util.getIsInstalled("iTunes"):
                self._iTunesButton.Enable(False)
                
        elif util.SYSTEM_NAME in util.FREEBSD_NAMES:
            self._xmmsButton = wx.RadioButton(self, ID_PLAYER, "XMMS  \t",
                                              style=wx.RB_GROUP)
            self._playerSizer.Add(self._xmmsButton, 0, wx.TOP|wx.BOTTOM, 3)
            
            if self._settings["player"] == "XMMS":
                self._xmmsButton.SetValue(True)
                
            if not util.getIsInstalled("XMMS"):
                self._xmmsButton.Enable(False)
                
        elif util.SYSTEM_NAME in util.MAC_NAMES:
            self._iTunesButton = wx.RadioButton(self, ID_PLAYER, "iTunes  \t",
                                                style=wx.RB_GROUP)
            self._playerSizer.Add(self._iTunesButton, 0, wx.TOP|wx.BOTTOM, 3)

            if self._settings["player"] == "iTunes":
                self._iTunesButton.SetValue(True)
                
            if not util.getIsInstalled("iTunes"):
                self._iTunesButton.Enable(False)

        wx.EVT_RADIOBUTTON(self, ID_PLAYER, self._onPlayerChange)
        
    def _onPlayerChange(self, e):
        if util.SYSTEM_NAME in util.WINDOWS_NAMES:
            if self._winampButton.GetValue():
                self._settings["player"] = "Winamp"
            elif self._iTunesButton.GetValue():
                self._settings["player"] = "iTunes"
                
        elif util.SYSTEM_NAME in util.FREEBSD_NAMES:
            if self._xmmsButton.GetValue():
                self._settings["player"] = "XMMS"
                
        elif util.SYSTEM_NAME in util.MAC_NAMES:
            if self._iTunesButton.GetValue():
                self._settings["player"] = "iTunes"
        
    def _setDefaults(self, safePlayers, defaultPlayer):
        self._safePlayers = safePlayers
        self._defaultPlayer = defaultPlayer

    def _loadSettings(self):
        try:
            player = self._configParser.get("Player", "player")
            if player not in self._safePlayers:
                self._sendWarning("Chosen player is not supported.")
                player = self._defaultPlayer
            self._settings["player"] = player
        except ConfigParser.NoOptionError:
            self._settings["player"] = self._defaultPlayer
