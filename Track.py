## Track information
## TODO: check getPath gets Mac path in correct form for iTunes
## TODO: create clearCache function for when user has changed metadata?
## TODO: make cache a limited size

from Errors import *
import mutagen
##from mutagen.easyid3 import EasyID3 as id3
import os

##print mutagen.easyid3.EasyID3.valid_keys.keys()

class TrackFactory:
    def __init__(self, loggerFactory, debugMode=False):
        self._logger = loggerFactory.getLogger("NQr.Track", "debug")
        self._debugMode = debugMode
        self._logger.debug("Creating track cache.")
        self._trackCache = {}

    def getTrackFromPath(self, db, path):
        track = self.getTrackFromPathNoID(db, path)
        self.addTrackToCache(track)
        return track

    def getTrackFromPathNoID(self, db, path):
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

class Track:
    def __init__(self, db, path, logger):
        self.path = os.path.abspath(path)
        self.db = db
        self._logger = logger
        self.id = None

    def getPath(self):
        return self.path

## poss should add to cache?
    def getID(self):
        if self.id == None:
            return self.db.getTrackID(self)
        return self.id

    def setID(self, factory, id):
        self._logger.debug("Setting track's ID to "+str(id)+".")
        self.id = id
        factory.addTrackToCache(self)

class AudioTrack(Track):
    def __init__(self, db, path, logger):
        Track.__init__(self, db, path, logger)
        path = self.getPath()
        try:
            self._logger.debug("Creating track from \'"+path+"\'.")
            self.track = mutagen.File(path, easy=True)
        except mutagen.mp3.HeaderNotFoundError:
            self._logger.error("File has no metadata.")
            raise NoMetadataError
        if self.track is None:
            self._logger.error("File is not a supported audio file.")
            raise UnknownTrackType
        self._logger.debug("Track created.")
        self._initGetAttributes()

    ## tags are of the form [u'artistName']
    def _initGetAttributes(self):
##        attr = ['artist', 'album', 'title', 'tracknumber']
        self._logger.debug("Getting basic track details.")
        self.artist = self._getAttribute('artist')
        self.album = self._getAttribute('album')
        self.title = self._getAttribute('title')
        self.trackNumber = self._getAttribute('tracknumber')

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
            if "TRCK" not in err and "TALB" not in err and "TPE1" not in err:
                raise err
            return "-"
    
    def getArtist(self):
##        artist = self.getAttribute('artist')
        return self.artist
    
    def getAlbum(self):
##        album = self.getAttribute('album')
        return self.album

    def getTitle(self):
##        title = self.getAttribute('title')
        return self.title

    def getTrackNumber(self):
##        trackNumber = self.getAttribute('tracknumber')
        return self.trackNumber

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
