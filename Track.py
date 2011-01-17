## Track information
##
## TODO: create clearCache function for when user has changed metadata? (done)
##       * I would actually make tracks update themselves and the
##       database when you spot a metadata change. (Ben)
##       * but how would you get them to find out that their metadata
##       has changed without querying the file all the time? (Felix)

from Errors import NoTrackError, UnknownTrackType, NoMetadataError,\
    DuplicateTagError, InvalidIDError
import mutagen
import mutagen.mp3
import os.path
from Util import BasePrefsPage, formatLength, getTrace

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

    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger), "Track"

    def loadSettings(self):
        pass

    def getTrackFromPath(self, db, path, traceCallback=None):
        track = self.getTrackFromPathNoID(db, path, traceCallback=traceCallback)
        self.addTrackToCache(track, traceCallback=traceCallback)
        return track

    def getTrackFromPathNoID(self, db, path, useCache=True, traceCallback=None):
        path = os.path.realpath(path)
        if useCache == True:
            track = self._trackPathCache.get(path)
        else:
            track = None
        if track != None:
            return track
        try:
            track = AudioTrack(db, path, self._logger, useCache=useCache,
                               traceCallback=None)
            track.getID(
                lambda thisCallback, id, db=db: db.setHistorical(
                    False, id, traceCallback=thisCallback),
                traceCallback=traceCallback)
        except UnknownTrackType:
            raise NoTrackError(trace=getTrace(traceCallback))
#            return None
        except NoMetadataError:
            raise NoTrackError(trace=getTrace(traceCallback))
#            return None
##            track = VideoTrack()
##            if track == None:
##                return None
        return track

    def _getTrackFromCache(self, trackID, traceCallback):
#        self._logger.debug("Retrieving track from cache.")
        if type(trackID) is not int:
            self._logger.error(str(trackID)+" is not a valid track ID")
            raise InvalidIDError(trace=getTrace(traceCallback))
        return self._trackCache.get(trackID, None)
    
    def _getTrackFromIDCompletion(self, db, path, completion, traceCallback,
                                  errcompletion=None):
        try:
            track = self.getTrackFromPath(db, path, traceCallback=traceCallback)
            completion(traceCallback, track)
        except NoTrackError as err:
            if errcompletion == None:
                raise err
            errcompletion(err)
    
    def getTrackFromID(self, db, trackID, completion, priority=None,
                       errcompletion=None, traceCallback=None):
        track = self._getTrackFromCache(trackID, traceCallback)
        if track == None:
            self._logger.debug("Track not in cache.")
            db.getPathFromID(
                trackID,
                lambda thisCallback, path, db=db, completion=completion,\
                    errcompletion=errcompletion: self._getTrackFromIDCompletion(
                        db, path, completion, thisCallback, errcompletion),
                priority=priority, traceCallback=traceCallback)
        else:
            completion(traceCallback, track)
    
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

    def addTrackToCache(self, track, traceCallback=None):
        track.getID(
            lambda thisCallback, id, track=track:\
                self._addTrackToCacheCompletion(track, id),
            traceCallback=traceCallback)
        
    def clearCache(self):
        self._logger.debug("Clearing track cache.")
        self._trackCache = {}
        self._trackIDList = []
        self._trackPathCache = {}
        self._trackPathList = []

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
    
    def _getIDCompletion(self, id, completion, traceCallback):
        self._id = id
        completion(traceCallback, id)

## poss should add to cache?
    def getID(self, completion, priority=None, traceCallback=None):
        if self._id == None:
            self._db.getTrackID(
                self,
                lambda thisCallback, id, completion=completion:\
                    self._getIDCompletion(id, completion, thisCallback),
                priority=priority, traceCallback=traceCallback)
            return
        completion(traceCallback, self._id)

    def setID(self, factory, id, traceCallback=None):
        self._logger.debug("Setting track's ID to "+str(id)+".")
        self._id = id
        if self._useCache == True:
            factory.addTrackToCache(self, traceCallback=traceCallback)
            
    def _getTagsCompletion(self, tags, completion, traceCallback):
        self._tags = tags
        completion(traceCallback, tags)

    def getTags(self, completion, priority=None, traceCallback=None):
        if self._tags == None:
            self._db.getTags(
                self,
                lambda thisCallback, tags, completion=completion:\
                    self._getTagsCompletion(tags, completion, thisCallback),
                priority=priority, traceCallback=traceCallback)
            return
        completion(traceCallback, self._tags)

    def setTag(self, tag, traceCallback=None):
        if self._tags == None:
            self._tags = []
        if tag in self._tags:
            raise DuplicateTagError(trace=getTrace(traceCallback))
        self._db.setTag(self, tag, traceCallback=traceCallback)
        self._tags.append(tag)

    def unsetTag(self, tag, traceCallback=None):
        self._db.unsetTag(self, tag, traceCallback=traceCallback)
        self._tags.remove(tag)
        
    def _addPlayCompletion(self, completion, traceCallback):
        if self._playCount == None:
            self.getPlayCount(completion, traceCallback=traceCallback)
        else:
            self._playCount += 1
            completion(traceCallback, self._playCount)

    def addPlay(self, delay=0, completion=None, priority=None,
                traceCallback=None):
        self._db.addPlay(
            self, delay,
            lambda thisCallback, completion=completion: self._addPlayCompletion(
                completion, thisCallback), priority=priority,
            traceCallback=traceCallback)
        
    def _getPlayCountCompletion(self, playCount, completion, traceCallback):
        self._playCount = playCount
        if completion != None:
            completion(traceCallback, playCount)

    def getPlayCount(self, completion, priority=None, traceCallback=None):
        if self._playCount == None:
            self._db.getPlayCount(
                lambda thisCallback, playCount, completion=completion:\
                    self._getPlayCountCompletion(playCount, completion,
                                                 thisCallback),
                track=self, priority=priority, traceCallback=traceCallback)
            return
        completion(traceCallback, self._playCount)
        
    # FIXME: make last play get stored and add play change the store (and change
    #        previous)
    def getLastPlay(self, completion, priority=None, traceCallback=None):
        self._db.getLastPlayedLocalTime(self, completion, priority=priority,
                                        traceCallback=traceCallback)

    def setPreviousPlay(self, previous):
        self._previous = previous

    def getPreviousPlay(self):
        return self._previous

    def setWeight(self, weight):
        self._weight = weight

    def getWeight(self):
        return self._weight

    def setScore(self, score, traceCallback=None):
        self._db.setScore(self, score, traceCallback=traceCallback)
        self._score = score
        self._isScored = True
        
    def _getScoreCompletion(self, isScored, completion, traceCallback,
                            priority=None):
        if isScored == False:
            completion(traceCallback, "-")
        else:
            self.getScoreValue(completion, priority=priority,
                               traceCallback=traceCallback)

    def getScore(self, completion, priority=None, traceCallback=None):
        self.getIsScored(
            lambda thisCallback, isScored, completion=completion,\
                priority=priority: self._getScoreCompletion(isScored,
                                                            completion,
                                                            thisCallback,
                                                            priority=priority),
            traceCallback=traceCallback)
        
    def _getScoreValueCompletion(self, score, completion, traceCallback):
        self._score = score
        completion(traceCallback, score)

    def getScoreValue(self, completion, priority=None, traceCallback=None):
        if self._score == None:
            self._db.getScoreValue(
                self,
                lambda thisCallback, score, completion=completion:\
                    self._getScoreValueCompletion(score, completion,
                                                  thisCallback),
                priority=priority, traceCallback=traceCallback)
            return
        completion(traceCallback, self._score)

    def setUnscored(self, traceCallback=None):
        self._isScored = False
        self._score = None
        self._db.setUnscored(self, traceCallback=traceCallback)
        
    def _getIsScoredCompletion(self, isScored, completion, traceCallback):
        self._isScored = isScored
        completion(traceCallback, isScored)

    def getIsScored(self, completion, priority=None, traceCallback=None):
        if self._isScored == None:
            self._db.getIsScored(
                self,
                lambda thisCallback, isScored, completion=completion:\
                    self._getIsScoredCompletion(isScored, completion,
                                                thisCallback),
                priority=priority, traceCallback=traceCallback)
            return
        completion(traceCallback, self._isScored)

class AudioTrack(Track):
    def __init__(self, db, path, logger, useCache=True, traceCallback=None):
        Track.__init__(self, db, path, logger, useCache=useCache)
#        self._path = self.getPath()
        try:
            self._logger.debug("Creating track from \'"+self._path+"\'.")
#            print repr(self._path), repr(self._path.encode("cp1252"))
            self._track = mutagen.File(self._path, easy=True)
        except mutagen.mp3.HeaderNotFoundError:
            self._logger.debug("File has no metadata.")
            raise NoMetadataError(trace=getTrace(traceCallback))
        if self._track is None:
            self._logger.debug("File is not a supported audio file.")
            raise UnknownTrackType(trace=getTrace(traceCallback))
        self._logger.debug("Track created.")
        self._initGetAttributes()
        #try:
        self._db.maybeUpdateTrackDetails(self, traceCallback=traceCallback)
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
    def __init__(self, parent, configParser, logger):
        BasePrefsPage.__init__(self, parent, configParser, logger, "Track")

if __name__ == '__main__':
    from mutagen.easyid3 import EasyID3

    print EasyID3.valid_keys.keys()

