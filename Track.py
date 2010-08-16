## Track information
## TODO: check getPath gets Mac path in correct form for iTunes
## TODO: create clearCache function for when user has changed metadata?

import mutagen
##from mutagen.easyid3 import EasyID3 as id3
import os

##print mutagen.easyid3.EasyID3.valid_keys.keys()

class Factory:
    def __init__(self):
        self._trackCache = {}

    def getTrackFromPathNoID(self, db, path):
        track = AudioTrack(db, path)
        if track == None:
            print "File is not a supported audio file."
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

    def addTrackToCache(self, track):
        self._trackCache[track.getID()] = track

    def getTrackFromPath(self, db, path):
        track = self.getTrackFromPathNoID(db, path)
        self.addTrackToCache(track)
        return track

    def getTrackFromCache(self, trackID):
        if type(trackID) is not int:
            raise TypeError(trackID+" is not a valid track ID")
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
        track = self.getTrackFromCache(trackID)
        if track == None:
            path = db.getPathFromID(trackID)
            track = self.getTrackFromPath(db, path)
        return track

class Track:
    def __init__(self, db, path):
        self.path = os.path.abspath(path)
        self.db = db
        self.id = None

    def getPath(self):
        return self.path

## poss should add to cache?
    def getID(self):
        if self.id != None:
            return self.id
        else:
            return self.db.getTrackID(self)

    def setID(self, factory, id):
        self.id = id
        factory.addTrackToCache(self)

class AudioTrack(Track):
    def __init__(self, db, path):
        Track.__init__(self, db, path)
        self.track = mutagen.File(self.getPath(), easy=True)
        ## returns None if the track is not a supported file type
        self._initGetAttributes()

    ## tags are of the form [u'artistName']
    def _initGetAttributes(self):
##        attr = ['artist', 'album', 'title', 'tracknumber']
        try:
##            attributes = self.track[attr]
            self.artist = self.track['artist'][0]
            self.album = self.track['album'][0]
            self.title = self.track['title'][0]
            self.trackNumber = self.track['tracknumber'][0]
##            return attributes
        except KeyError as err:
            if "TRCK" not in err and "TALB" not in err:
                raise err
            return "-"

##    def getAttribute(self, attr):
##        try:
##            attribute = self.track[attr][0]
####            attribute = unicode(self.track[attr])[3:-2]
##            return attribute
##        except KeyError as err:
##            if "TRCK" not in err and "TALB" not in err:
##                raise err
##            return "-"
    
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
