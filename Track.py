## Track information
##
## TODO: check getPath gets Mac path in correct form for iTunes
## TODO: create clearCache function for when user has changed metadata?
##       * I would actually make tracks update themselves and the
##       database when you spot a metadata change. (Ben)
##       * but how would you get them to find out that their metadata
##       has changed without querying the file all the time? (Felix)

from Errors import NoTrackError, UnknownTrackType, NoMetadataError
import mutagen
import os.path
from Util import BasePrefsPage, formatLength

class TrackFactory:
    def __init__(self, loggerFactory, configParser, debugMode):
        self._logger = loggerFactory.getLogger("NQr.Track", "debug")
        self._configParser = configParser
        self.loadSettings()
        self._debugMode = debugMode
        self._logger.debug("Creating track cache.")
        self._trackCache = {}
        self._trackIDList = []
        self._trackPathCache = {}
        self._trackPathList = []

    def getPrefsPage(self, parent, logger, system):
        return PrefsPage(parent, system, self._configParser, logger), "Track"

    def loadSettings(self):
        pass

    def getTrackFromPath(self, db, path):
        track = self.getTrackFromPathNoID(db, path)
        self.addTrackToCache(track)
        return track

    def getTrackFromPathNoID(self, db, path, useCache=True):
        path = os.path.realpath(path)
        if useCache == True:
            track = self._trackPathCache.get(path)
        else:
            track = None
        if track != None:
            return track
        try:
            track = AudioTrack(db, path, self._logger, useCache=useCache)
            track.getID(lambda id, db=db: db.setHistorical(False, id))
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
    
    def _getTrackFromIDCompletion(self, db, path, completion,
                                  errcompletion=None):
        try:
            track = self.getTrackFromPath(db, path)
            completion(track)
        except NoTrackError as err:
            if errcompletion == None:
                raise err
            errcompletion(err)
    
    def getTrackFromID(self, db, trackID, completion, priority=None,
                       errcompletion=None):
        track = self._getTrackFromCache(trackID)
        if track == None:
            self._logger.debug("Track not in cache.")
            db.getPathFromID(
                trackID,
                lambda path, db=db, completion=completion,\
                    errcompletion=errcompletion: self._getTrackFromIDCompletion(
                        db, path, completion, errcompletion),
                priority=priority)
        else:
            completion(track)
    
    def _addTrackToCacheCompletion(self, track, id):
        self._logger.debug("Adding track to cache.")
        if len(self._trackCache) > 10000:
            del self._trackCache[self._trackIDList.pop(0)]
        if id not in self._trackCache:
            self._trackCache[id] = track
            self._trackIDList.append(id)
        else:
            assert track is self._trackCache[id]
            
        if len(self._trackPathCache) > 10000:
            del self._trackPathCache[self._trackPathList.pop(0)]
        path = track.getPath()
        if path not in self._trackPathCache:
            self._trackPathCache[path] = track
            self._trackPathList.append(path)
        else:
            assert track is self._trackPathCache[path]

    def addTrackToCache(self, track):
        track.getID(lambda id, track=track: self._addTrackToCacheCompletion(
                        track, id))

class Track:
    def __init__(self, db, path, logger, useCache=True):
        self._path = os.path.realpath(path)
        self._db = db
        self._logger = logger
        self._useCache = useCache
        self._id = None
        self._tags = None
        self._weight = None
        self._isScored = None
        self._score = None
        self._playCount = None

    def getPath(self):
        return self._path
    
    def _getIDCompletion(self, id, completion):
        self._id = id
        completion(id)

## poss should add to cache?
    def getID(self, completion, priority=None):
        if self._id == None:
            self._db.getTrackID(
                self, lambda id, completion=completion: self._getIDCompletion(
                    id, completion), priority=priority)
            return
        completion(self._id)

    def setID(self, factory, id):
        self._logger.debug("Setting track's ID to "+str(id)+".")
        self._id = id
        if self._useCache == True:
            factory.addTrackToCache(self)
            
    def _getTagsCompletion(self, tags, completion):
        self._tags = tags
        completion(tags)

    def getTags(self, completion, priority=None):
        if self._tags == None:
            self._db.getTags(self,
                             lambda tags, completion=completion:\
                                self._getTagsCompletion(tags, completion),
                             priority=priority)
            return
        completion(self._tags)

    def setTag(self, tag):
        self._db.setTag(self, tag)
        if self._tags == None:
            self._tags = []
        if tag not in self._tags:
            self._tags.append(tag)

    def unsetTag(self, tag):
        self._db.unsetTag(self, tag)
        self._tags.remove(tag)
        
    def _addPlayCompletion(self, playCount):
        self._playCount = playCount

    def addPlay(self, delay=0, completion=None):
        self._db.addPlay(self, delay, completion)
        if self._playCount == None:
            self.getPlayCount(
                lambda playCount: self._addPlayCompletion(playCount))
            return
        self._playCount += 1
        
    def _getPlayCount(self, playCount, completion):
        self._playCount = playCount
        completion(playCount)

    def getPlayCount(self, completion, priority=None):
        if self._playCount == None:
            self._db.getPlayCount(lambda playCount, completion=completion:\
                                    self._getPlayCount(playCount, completion),
                                  track=self, priority=priority)
            return
        completion(self._playCount)

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
        
    def _getScoreCompletion(self, isScored, completion, priority=None):
        if isScored == False:
            completion("-")
        else:
            self.getScoreValue(completion, priority=priority)

    def getScore(self, completion, priority=None):
        self.getIsScored(lambda isScored, completion=completion,\
                            priority=priority: self._getScoreCompletion(
                                isScored, completion, priority=priority))
        
    def _getScoreValueCompletion(self, score, completion):
        self._score = score
        completion(score)

    def getScoreValue(self, completion, priority=None):
        if self._score == None:
            self._db.getScoreValue(self,
                                   lambda score, completion=completion:\
                                        self._getScoreValueCompletion(
                                            score, completion),
                                   priority=priority)
            return
        completion(self._score)

    def setUnscored(self):
        self._isScored = False
        self._score = None
        self._db.setUnscored(self)
        
    def _getIsScoredCompletion(self, isScored, completion):
        self._isScored = isScored
        completion(isScored)

    def getIsScored(self, completion, priority=None):
        if self._isScored == None:
            self._db.getIsScored(self,
                                 lambda isScored, completion=completion:\
                                    self._getIsScoredCompletion(isScored,
                                                                completion),
                                 priority=priority)
            return
        completion(self._isScored)

class AudioTrack(Track):
    def __init__(self, db, path, logger, useCache=True):
        Track.__init__(self, db, path, logger, useCache=useCache)
#        self._path = self.getPath()
        try:
            self._logger.debug("Creating track from \'"+self._path+"\'.")
            self._track = mutagen.File(self._path, easy=True)
        except mutagen.mp3.HeaderNotFoundError:
            self._logger.debug("File has no metadata.")
            raise NoMetadataError
        if self._track is None:
            self._logger.debug("File is not a supported audio file.")
            raise UnknownTrackType
        self._logger.debug("Track created.")
        self._initGetAttributes()
        #try:
        self._db.maybeUpdateTrackDetails(self)
        #except NoTrackError:
        #    pass

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
            if str(err) not in ("'TRCK'", "'TALB'","'TPE1'", "'TBPM'",
                                "'TIT2'"):
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

class PrefsPage(BasePrefsPage):
    def __init__(self, parent, system, configParser, logger):
        BasePrefsPage.__init__(self, parent, system, configParser, logger,
                               "Track")

if __name__ == '__main__':
    from mutagen.easyid3 import EasyID3

    print EasyID3.valid_keys.keys()

