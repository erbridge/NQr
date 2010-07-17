## Track information

from mutagen.easyid3 import EasyID3 as id3

##print id3.valid_keys.keys()

class ID3Track:
    def __init__(self, path):
        self.path = path
        self.track = id3(self.path)

    ## ID3 tags are of the form [u'artistName']
    def getAttribute(self, attr):
        attribute = unicode(self.track[attr])[3:-2]
        return attribute
        
    def getPath(self):
        return self.path
    
    def getArtist(self):
        artist = self.getAttribute('artist')
        return artist
    
    def getAlbum(self):
        album = self.getAttribute('album')
        return album

    def getTitle(self):
        title = self.getAttribute('title')
        return title
