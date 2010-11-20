# List which tracks won't import...

import mutagen
import os
import sys

def tryTrack(path):
    track = mutagen.File(path, easy=True)
    try:
        artist = track['artist']
        album = track['album']
        title = track['title']
        trackNumber = track['tracknumber']
        bpm = track['bpm']
    except KeyError as err:
        if str(err) not in ("'TRCK'", "'TALB'","'TPE1'", "'TBPM'"):
            print path
#            print track
#            print str(err)
#            raise err

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
            tryTrack(f)

def main():
    dir = sys.argv[1]
    global exceptions
    exceptions = sys.argv[2:]
    recurseDir(dir)

if __name__ == '__main__':
    main()
