# List which tracks won't import...

import mutagen
import os
import sys

class TrackTrier:
    def __init__(self, path):
        self.path_ = path
        self.track_ = mutagen.File(path, easy=True)
        artist = self.getAttr('artist')
        album = self.getAttr('album')
        title = self.getAttr('title')
        trackNumber = self.getAttr('tracknumber')
        bpm = self.getAttr('bpm')
        
    def getAttr(self, attr):
        try:
            got = self.track_[attr]
        except KeyError as err:
            if str(err) not in ("'TRCK'", "'TALB'","'TPE1'", "'TBPM'",
                                "'TIT2'"):
                print self.path_
                print self.track_
                print attr
                #            print str(err)
                raise err

def recurseDir(dir):
    files = os.listdir(dir)
    for file in files:
        f = dir + '/' + file
#        print f
        if f in exceptions:
            print "  SKIP!"
            continue
        if os.path.isdir(f):
            recurseDir(f)
        else:
            TrackTrier(f)

def main():
    dir = sys.argv[1]
    global exceptions
    exceptions = sys.argv[2:]
    recurseDir(dir)

if __name__ == '__main__':
    main()
