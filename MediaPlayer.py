## Base class for media players

import ConfigParser
from Errors import NoTrackError
import os.path
from Util import BasePrefsPage, wx

class MediaPlayer:
    def __init__(self, loggerFactory, name, noQueue, configParser,
                 defaultPlayer, safePlayers):
        self._logger = loggerFactory.getLogger(name, "debug")
        self._configParser = configParser
        self._defaultPlayer = defaultPlayer
        self._safePlayers = safePlayers
        self.loadSettings()
        self._noQueue = noQueue

    def savePlaylist(self):
        self._logger.debug("Storing current playlist.")
        playlist = []
        for trackPosition in range(self.getPlaylistLength()):
            playlist.append(self.getTrackPathAtPos(trackPosition))
        return playlist

## FIXME: sets currently playing track to first track in the list, but continues
##        to play the old track (fixed with work-around)
    def loadPlaylist(self, playlist):
        self._logger.debug("Restoring playlist.")
        currentTrackPath = self.getCurrentTrackPath()
        self.clearPlaylist()
        self.addTrack(currentTrackPath)
        for filepath in playlist:
            self.addTrack(filepath)

    def cropPlaylist(self, number):
        if number == 1:
            self._logger.debug("Cropping playlist by "+str(number)+" track.")
        else:
            self._logger.debug("Cropping playlist by "+str(number)+" tracks.")
        for n in range(number):
            self.deleteTrack(0)
        
    def hasNextTrack(self):
        try:
            self.getTrackPathAtPos(self.getCurrentTrackPos()+1)
            return True
        except NoTrackError and TypeError:
            return False

## FIXME: gets confused if the playlist is empty (in winamp): sets currently
##        playing track to first track in the list, but continues to play the
##        old track
    def getCurrentTrackPath(self, logging=True):
        return self.getTrackPathAtPos(self.getCurrentTrackPos(), logging)

    # must always be checked for trackness
    def getTrackPathAtPos(self, trackPosition, logging=True):
        if trackPosition == None:
            return None
        path = self._getTrackPathAtPos(trackPosition, logging)
        return os.path.realpath(path)
    
    def _getUnplayedTrackIDsCallback(self, id, path):
        # The track may be one we don't know added directly to the player
        if id is not None:
            self._ids.append(id)
        else:
            ## FIXME: why skip them rather than adding them to db? (Felix)
            self._logger.info("Skipping unknown unplayed track "+path)
            
    def _getUnplayedTrackIDListCompletion(self, completion):
        completion(self._ids)
        
    def getUnplayedTrackIDs(self, db, completion):
        self._ids = []
        try:
            for pos in range(self.getCurrentTrackPos(), self.getPlaylistLength()):
                path = self.getTrackPathAtPos(pos)
                db.maybeGetIDFromPath(
                    path,
                    lambda id, path=path: self._getUnplayedTrackIDsCallback(
                        id, path))
        except TypeError:
            pass
        db.complete(lambda: self._getUnplayedTrackIDListCompletion(completion))

    def addTrack(self, filepath):
        if self._noQueue:
            self._logger.info("Not queueing "+filepath)
            return
        self._addTrack(filepath)
        
    def insertTrack(self, filepath, position):
        if self._noQueue:
            self._logger.info("Not queueing "+filepath)
            return
        self._insertTrack(filepath, position)

    def getPrefsPage(self, parent, logger, system):
        return PrefsPage(parent, system, self._configParser, logger,
                         self._defaultPlayer, self._safePlayers), "Player"

    def loadSettings(self):
        pass

class PrefsPage(BasePrefsPage):
    def __init__(self, parent, system, configParser, logger,
                 defaultPlayer, safePlayers):
        BasePrefsPage.__init__(self, parent, system, configParser, logger,
                               "Player", defaultPlayer, safePlayers)
        
        self._initCreatePlayerSizer()
        
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        mainSizer.Add(self._playerSizer, 0)

        self.SetSizer(mainSizer)
    
    def _initCreatePlayerSizer(self): # FIXME: should check which are installed
        ID_PLAYER = wx.NewId()
        
        self._playerSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        label = wx.StaticText(self, -1, "Player:  \t")
        self._playerSizer.Add(label, 0, wx.LEFT|wx.TOP|wx.BOTTOM, 3)
        
        if self._system == "Windows":
            self._winampButton = wx.RadioButton(self, ID_PLAYER, "Winamp  \t",
                                                style=wx.RB_GROUP)
            self._playerSizer.Add(self._winampButton, 0, wx.TOP|wx.BOTTOM, 3)
            
            self._iTunesButton = wx.RadioButton(self, ID_PLAYER, "iTunes  \t")
            self._playerSizer.Add(self._iTunesButton, 0, wx.TOP|wx.BOTTOM, 3)

            if self._settings["player"] == "Winamp":
                self._winampButton.SetValue(True)
            elif self._settings["player"] == "iTunes":
                self._iTunesButton.SetValue(True)
                
        elif self._system == "FreeBSD":
            self._xmmsButton = wx.RadioButton(self, ID_PLAYER, "XMMS  \t",
                                              style=wx.RB_GROUP)
            self._playerSizer.Add(self._xmmsButton, 0, wx.TOP|wx.BOTTOM, 3)
            
            if self._settings["player"] == "XMMS":
                self._xmmsButton.SetValue(True)
                
        elif self._system == "Mac OS X":
            self._iTunesButton = wx.RadioButton(self, ID_PLAYER, "iTunes  \t",
                                                style=wx.RB_GROUP)
            self._playerSizer.Add(self._iTunesButton, 0, wx.TOP|wx.BOTTOM, 3)

            if self._settings["player"] == "iTunes":
                self._iTunesButton.SetValue(True)

        wx.EVT_RADIOBUTTON(self, ID_PLAYER, self._onPlayerChange)
        
    def _onPlayerChange(self, e):
        if self._system == "Windows":
            if self._winampButton.GetValue():
                self._settings["player"] = "Winamp"
            elif self._iTunesButton.GetValue():
                self._settings["player"] = "iTunes"
                
        elif self._system == "FreeBSD":
            if self._xmmsButton.GetValue():
                self._settings["player"] = "XMMS"
                
        elif self._system == "Mac OS X":
            if self._iTunesButton.GetValue():
                self._settings["player"] = "iTunes"
        
    def _setDefaults(self, safePlayers, defaultPlayer):
        self._safePlayers = safePlayers
        self._defaultPlayer = defaultPlayer

    def _loadSettings(self):
        try:
            player = self._configParser.get("Player", "player")
            if player not in self._safePlayers:
                self._logger.warning("Chosen player is not supported.")
                player = self._defaultPlayer
            self._settings["player"] = player
        except ConfigParser.NoOptionError:
            self._settings["player"] = self._defaultPlayer
