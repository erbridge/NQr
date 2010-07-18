## Track information

import mutagen
from mutagen.easyid3 import EasyID3 as id3

##print id3.valid_keys.keys()

_trackCache = {}

def getTrackFromPathNoID(db, path):
    track = None
    try:
        track = ID3Track(db, path)
    except mutagen.id3.ID3NoHeaderError as e:
        if path[0] != "\'":
            fullPath = "\'"+path+"\'"
        else:
            fullPath = path
        if str(e) != fullPath+" doesn't start with an ID3 tag":
            raise e
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
        self.path = path
        self.db = db

    def getPath(self):
        return self.path

    def getID(self):
        return self.db.getTrackID(self)

    def setID(self, id):
        self.id = id
        addTrackToCache(self)

class ID3Track(Track):
    def __init__(self, db, path):
        Track.__init__(self, db, path)
        self.track = id3(self.getPath())

    ## ID3 tags are of the form [u'artistName']
    def getAttribute(self, attr):
        attribute = unicode(self.track[attr])[3:-2]
        return attribute
    
    def getArtist(self):
        artist = self.getAttribute('artist')
        return artist
    
    def getAlbum(self):
        album = self.getAttribute('album')
        return album

    def getTitle(self):
        title = self.getAttribute('title')
        return title
