## Track information
## TODO: check getPath gets Mac path in correct form for iTunes

import mutagen
from mutagen.easyid3 import EasyID3 as id3
import os

##print id3.valid_keys.keys()

_trackCache = {}

def getTrackFromPathNoID(db, path):
    track = None
    try:
        track = ID3Track(db, path)
    except mutagen.id3.ID3NoHeaderError as err:
        if path[0] != "\'":
            fullPath = "\'"+os.path.abspath(path)+"\'"
        else:
            fullPath = os.path.abspath(path)
####        if str(err) != fullPath+" doesn't start with an ID3 tag":
##        if "doesn't start with an ID3 tag" not in str(err):
##            raise err
##        elif "too small" not in str(err):
##            raise err
        print fullPath+" does not have an ID3 tag."
##            try:
##                track.MP4Track(path)
        return None
    return track

def addTrackToCache(track):
    _trackCache[track.getID()] = track

def getTrackFromPath(db, path):
    track = getTrackFromPathNoID(db, path)
    addTrackToCache(track)
    return track

def getTrackFromCache(trackID):
    return _trackCache[trackID]

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

    def setID(self, id):
        self.id = id
        addTrackToCache(self)

class ID3Track(Track):
    def __init__(self, db, path):
        Track.__init__(self, db, path)
        self.track = id3(self.getPath()) ## poss mutagen(self.getPath()) to get all types?

    ## poss should call all attributes at once, and then read the ones required
    ## ID3 tags are of the form [u'artistName']
    def getAttribute(self, attr):
        try:
            attribute = self.track[attr][0]
##            attribute = unicode(self.track[attr])[3:-2]
            return attribute
        except KeyError as err:
            if err != 'TRCK':
                raise err
            return "None"
    
    def getArtist(self):
        artist = self.getAttribute('artist')
        return artist
    
    def getAlbum(self):
        album = self.getAttribute('album')
        return album

    def getTitle(self):
        title = self.getAttribute('title')
        return title

    def getTrackNumber(self):
        trackNumber = self.getAttribute('tracknumber')
        return trackNumber
