## Track information
##
## TODO: check getPath gets Mac path in correct form for iTunes
## TODO: create clearCache function for when user has changed metadata?
##       * I would actually make tracks update themselves and the
##       database when you spot a metadata change. (Ben)
##       * but how would you get them to find out that their metadata
##       has changed without querying the file all the time? (Felix)

import ConfigParser
from Errors import *
import mutagen
import os
from Util import *

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

class TrackFactory:
    def __init__(self, loggerFactory, configParser, debugMode=False):
        self._logger = loggerFactory.getLogger("NQr.Track", "debug")
        self._configParser = configParser
        self.loadSettings()
        self._debugMode = debugMode
        self._logger.debug("Creating track cache.")
        self._trackCache = {}
        self._trackIDList = []
        self._trackPathCache = {}
        self._trackPathList = []

    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger), "Track"

    def loadSettings(self):
        pass

    def getTrackFromPath(self, db, path):
        track = self.getTrackFromPathNoID(db, path)
        self.addTrackToCache(track)
        return track

    def getTrackFromPathNoID(self, db, path):
        track = self._trackPathCache.get(path)
        if track != None:
            return track
        try:
            track = AudioTrack(db, path, self._logger)
            db.setHistorical(False, track.getID())
        except UnknownTrackType:
            raise NoTrackError
#            return None
        except NoMetadataError:
            raise NoTrackError
#            return None
##            track = VideoTrack()
##            if track == None:
##                return None
        return track

    def _getTrackFromCache(self, trackID):
        self._logger.debug("Retrieving track from cache.")
        if type(trackID) is not int:
            self._logger.error(str(trackID)+" is not a valid track ID")
            raise TypeError(str(trackID)+" is not a valid track ID")
        return self._trackCache.get(trackID, None)

    def getTrackFromID(self, db, trackID):
        track = self._getTrackFromCache(trackID)
        if track == None:
            self._logger.debug("Track not in cache.")
            path = db.getPathFromID(trackID)
            track = self.getTrackFromPath(db, path)
        return track

    def addTrackToCache(self, track):
        self._logger.debug("Adding track to cache.")
        if len(self._trackCache) > 10000:
            del self._trackCache[self.trackIDList.pop(0)]
        self._trackCache[track.getID()] = track
        self._trackIDList.append(track.getID())

        if len(self._trackPathCache) > 10000:
            del self._trackPathCache[self.trackPathList.pop(0)]
        self._trackPathCache[track.getPath()] = track
        self._trackPathList.append(track.getPath())

class Track:
    def __init__(self, db, path, logger):
        self._path = os.path.abspath(path)
        self._db = db
        self._logger = logger
        self._id = None
        self._tags = None
        self._weight = None
        self._isScored = None
        self._score = None
        self._playCount = None

    def getPath(self):
        return self._path

## poss should add to cache?
    def getID(self, update=False):
        if self._id == None:
            return self._db.getTrackID(self, update)
        return self._id

    def setID(self, factory, id):
        self._logger.debug("Setting track's ID to "+str(id)+".")
        self._id = id
        factory.addTrackToCache(self)

    def getTags(self):
        if self._tags == None:
            self._tags = self._db.getTags(self)
        return self._tags

    def setTag(self, tag):
        self._db.setTag(self, tag)
        if self._tags == None:
            self._tags = []
        self._tags.append(tag)

    def unsetTag(self, tag):
        self._db.unsetTag(self, tag)
        self._tags.remove(tag)

    def addPlay(self, delay=0):
        self._db.addPlay(self, delay)
        self._playCount = self.getPlayCount() + 1

    def getPlayCount(self):
        if self._playCount == None:
            self._playCount = self._db.getPlayCount(self)
        return self._playCount

    def setPreviousPlay(self, previous):
        self._previous = previous

    def getPreviousPlay(self):
        return self._previous

    def setWeight(self, weight):
        self._weight = weight

    def getWeight(self):
        return self._weight

    def setScore(self, score):
        self._db.setScore(self, score)
        self._score = score
        self._isScored = True

    def getScore(self):
        if self.getIsScored == False:
            return "-"
        return self.getScoreValue()

    def getScoreValue(self):
        if self._score == None:
            self._score = self._db.getScoreValue(self)
        return self._score

    def setUnscored(self):
        self._isScored = False
        self._score = None
        self._db.setUnscored(self)

    def getIsScored(self):
        if self._isScored == None:
            self._isScored = self._db.getIsScored(self)
        return self._isScored

class AudioTrack(Track):
    def __init__(self, db, path, logger):
        Track.__init__(self, db, path, logger)
        self._path = self.getPath()
        try:
            self._logger.debug("Creating track from \'"+self._path+"\'.")
            self._track = mutagen.File(path, easy=True)
        except mutagen.mp3.HeaderNotFoundError:
            self._logger.error("File has no metadata.")
            raise NoMetadataError
        if self._track is None:
            self._logger.error("File is not a supported audio file.")
            raise UnknownTrackType
        self._logger.debug("Track created.")
        self._initGetAttributes()
        try:
            self._db.maybeUpdateTrackDetails(self)
        except NoTrackError:
            pass

    ## tags are of the form [u'artistName']
    def _initGetAttributes(self):
        self._logger.debug("Getting basic track details.")
        self._artist = self._getAttribute('artist')
        self._album = self._getAttribute('album')
        self._title = self._getAttribute('title')
        self._trackNumber = self._getAttribute('tracknumber')
        self._bpm = self._getAttribute('bpm')
        self._length = self._getLength()

    def _getAttribute(self, attr):
        try:
            attribute = self._track[attr][0]
            return attribute
        except KeyError as err:
            # if 'artist' is thrown then the track doesn't have any ID3
            # which is an error we should not accept - so for now, die
            ## poss should die on no title not no artist?
            ## what is key for artist?
            if "TRCK" not in err and "TALB" not in err and "TPE1" not in err\
               and "TBPM" not in err:
                raise err
            return "-"

    def _getLength(self):
        audio = mutagen.mp3.MP3(self._path)
        length = audio.info.length
        return length

    def getArtist(self):
        return self._artist

    def getAlbum(self):
        return self._album

    def getTitle(self):
        return self._title

    def getTrackNumber(self):
        return self._trackNumber

    def getBPM(self):
        return self._bpm

    def getLength(self):
        return self._length
    
    def getLengthString(self):
        self._lengthString = formatLength(self._length)
        return self._lengthString

class PrefsPage(wx.Panel):
    def __init__(self, parent, configParser, logger):
        wx.Panel.__init__(self, parent)
        self._logger = logger
        self._settings = {}
        self._configParser = configParser
        try:
            self._configParser.add_section("Track")
        except ConfigParser.DuplicateSectionError:
            pass
        self._loadSettings()

    def savePrefs(self):
        self._logger.debug("Saving track preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set("Track", name, str(value))

    def _loadSettings(self):
        pass

if __name__ == '__main__':
    from mutagen.easyid3 import EasyID3

    print EasyID3.valid_keys.keys()

