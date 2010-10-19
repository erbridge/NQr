## Track information
## TODO: check getPath gets Mac path in correct form for iTunes
## TODO: create clearCache function for when user has changed metadata?
##       * I would actually make tracks update themselves and the
##       database when you spot a metadata change. (Ben)
## TODO: make cache a limited size

from Errors import *
import math
import mutagen
import os

class TrackFactory:
    def __init__(self, loggerFactory, debugMode=False):
        self._logger = loggerFactory.getLogger("NQr.Track", "debug")
        self._debugMode = debugMode
        self._logger.debug("Creating track cache.")
        self._trackCache = {}
        self._trackPathCache = {}

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
        except UnknownTrackType:
            return None
        except NoMetadataError:
            return None
##            track = VideoTrack()
##            if track == None:
##                return None
        return track

#### os.path.abspath breaks with unicode poss use win32api.GetFullPathName
##    def getTrackFromPathNoID(self, db, path):
##        track = None
##        try:
##            track = ID3Track(db, path)
##        except mutagen.id3.ID3NoHeaderError as err:
##            if path[0] != "\'":
##                fullPath = "\'"+os.path.abspath(path)+"\'"
##            else:
##                fullPath = os.path.abspath(path)
##    ####        if str(err) != fullPath+" doesn't start with an ID3 tag":
##    ##        if "doesn't start with an ID3 tag" not in str(err):
##    ##            raise err
##    ##        elif "too small" not in str(err):
##    ##            raise err
##            print fullPath+" does not have an ID3 tag."
##    ##            try:
##    ##                track.MP4Track(path)
##            return None
##        return track

    def _getTrackFromCache(self, trackID):
        self._logger.debug("Retrieveing track from cache.")
        if type(trackID) is not int:
            self._logger.error(str(trackID)+" is not a valid track ID")
            raise TypeError(str(trackID)+" is not a valid track ID")
        return self._trackCache.get(trackID, None)
##        try:
##            return self._trackCache[trackID]
##        except KeyError as err:
##            ## FIXME: should only except errors where err is integer (fixed?)
##            try:
##                int(err)
##            except ValueError:
##                raise err
##            return None

    def getTrackFromID(self, db, trackID):
        track = self._getTrackFromCache(trackID)
        if track == None:
            self._logger.debug("Track not in cache.")
            path = db.getPathFromID(trackID)
            track = self.getTrackFromPath(db, path)
        return track

    def addTrackToCache(self, track):
        self._logger.debug("Adding track to cache.")
        self._trackCache[track.getID()] = track
        self._trackPathCache[track.getPath()] = track

class Track:
    def __init__(self, db, path, logger):
        self._path = os.path.abspath(path)
        self._db = db
        self._logger = logger
        self._id = None
        self._tags = None
        self._weight = None

    def getPath(self):
        return self._path

## poss should add to cache?
    def getID(self):
        if self._id == None:
            return self._db.getTrackID(self)
        return self._id

    def setID(self, factory, id):
        self._logger.debug("Setting track's ID to "+str(id)+".")
        self._id = id
        factory.addTrackToCache(self)

    def getTags(self):
        if self._tags == None:
            self._tags = self._db.getTags(self)
        return self._tags

    def setTags(self, tags):
        self._tags = tags

    def setPreviousPlay(self, previous):
        self._previous = previous

    def getPreviousPlay(self):
        return self._previous

    def setWeight(self, weight):
        self._weight = weight

    def getWeight(self):
        return self._weight

class AudioTrack(Track):
    def __init__(self, db, path, logger):
        Track.__init__(self, db, path, logger)
        self._path = self.getPath()
        try:
            self._logger.debug("Creating track from \'"+self._path+"\'.")
            self.track = mutagen.File(path, easy=True)
        except mutagen.mp3.HeaderNotFoundError:
            self._logger.error("File has no metadata.")
            raise NoMetadataError
        if self.track is None:
            self._logger.error("File is not a supported audio file.")
            raise UnknownTrackType
        self._logger.debug("Track created.")
        self._initGetAttributes()
        self._db.maybeUpdateTrackDetails(self)

    ## tags are of the form [u'artistName']
    def _initGetAttributes(self):
##        attr = ['artist', 'album', 'title', 'tracknumber']
        self._logger.debug("Getting basic track details.")
        self._artist = self._getAttribute('artist')
        self._album = self._getAttribute('album')
        self._title = self._getAttribute('title')
        self._trackNumber = self._getAttribute('tracknumber')
        self._bpm = self._getAttribute('bpm')
        self._length = self._getLength()

    def _getAttribute(self, attr):
        try:
            attribute = self.track[attr][0]
##           attribute = unicode(self.track[attr])[3:-2]
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
##        artist = self.getAttribute('artist')
        return self._artist
    
    def getAlbum(self):
##        album = self.getAttribute('album')
        return self._album

    def getTitle(self):
##        title = self.getAttribute('title')
        return self._title

    def getTrackNumber(self):
##        trackNumber = self.getAttribute('tracknumber')
        return self._trackNumber

    def getBPM(self):
        return self._bpm

    def getLength(self):
        return self._length

##class ID3Track(Track):
##    def __init__(self, db, path):
##        Track.__init__(self, db, path)
##        self.track = id3(self.getPath()) ## poss mutagen(self.getPath()) to get all types?
##
##    ## poss should call all attributes at once, and then read the ones required
##    ## ID3 tags are of the form [u'artistName']
##    def getAttribute(self, attr):
##        try:
##            attribute = self.track[attr][0]
####            attribute = unicode(self.track[attr])[3:-2]
##            return attribute
##        except KeyError as err:
##            if "TRCK" not in err and "TALB" not in err:
##                raise err
##            return "-"
##    
##    def getArtist(self):
##        artist = self.getAttribute('artist')
##        return artist
##    
##    def getAlbum(self):
##        album = self.getAttribute('album')
##        return album
##
##    def getTitle(self):
##        title = self.getAttribute('title')
##        return title
##
##    def getTrackNumber(self):
##        trackNumber = self.getAttribute('tracknumber')
##        return trackNumber

if __name__ == '__main__':
    from mutagen.easyid3 import EasyID3

    print EasyID3.valid_keys.keys()
    
