## Database Control
## TODO: check metadata haven't changed when grabbing track?
## TODO: use a hash as a track identifier instead of path to allow for path
##       changes.
## TODO: add a function to remove the last play record (to undo the play)
## TODO: add ignore list
## TODO: check if track table already exists first to confirm whether or not
##       to create other tables (poss corruption)
## TODO: add more attributes to tracks

##import Track
import os
import sqlite3

class NoTrackError(Exception):
    def __init__(self):
        return

    def __str__(self):
        print "\nNo track has been identified"

class Database:
    def __init__(self, trackFactory, databasePath="database", defaultScore=10):
        self._trackFactory = trackFactory
        self._databasePath = databasePath
        self._defaultScore = defaultScore
        self._conn = sqlite3.connect(self._databasePath)
        self._initCreateTrackTable()
        self._initCreateDirectoryTable()
        self._initCreatePlaysTable()
        self._initCreateScoresTable()
        self._initCreateLinksTable()
        self._initCreateIgnoreTable()
        self._conn.commit()

    def _initCreateTrackTable(self):
        c = self._conn.cursor()
        try:
            c.execute("""create table tracks (trackid integer primary key
                                              autoincrement, path text,
                                              artist text, album text,
                                              title text, tracknumber text,
                                              unscored integer)""")
            print "Tracks table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table tracks already exists":
                raise e
            print "Tracks table found."
        c.close()

    def _initCreateDirectoryTable(self):
        c = self._conn.cursor()
        try:
            c.execute("""create table directories (directoryid integer primary
                                                   key autoincrement,
                                                   path text)""")
            print "Directories table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table directories already exists":
                raise e
            print "Directories table found."
        c.close()

    def _initCreatePlaysTable(self):
        c = self._conn.cursor()
        try:
            c.execute("""create table plays (playid integer primary key
                                             autoincrement, trackid integer,
                                             datetime text)""")
            print "Plays table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table plays already exists":
                raise e
            print "Plays table found."
        c.close()

    def _initCreateScoresTable(self):
        c = self._conn.cursor()
        try:
            c.execute("""create table scores (scoreid integer primary key
                                              autoincrement, trackid integer,
                                              score integer, datetime text)""")
            print "Scores table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table scores already exists":
                raise e
            print "Scores table found."
        c.close()

    def _initCreateLinksTable(self):
        c = self._conn.cursor()
        try:
            c.execute("""create table links (linkid integer primary key
                                             autoincrement, firsttrackid
                                             integer, secondtrackid integer)""")
            print "Track links table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table links already exists":
                raise e
            print "Track links table found."
        c.close()

    def _initCreateIgnoreTable(self):
        c = self._conn.cursor()
        try:
            c.execute("""create table ignore (ignoreid integer primary key
                                              autoincrement, trackid
                                              integer)""")
            print "Ignore table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table ignore already exists":
                raise e
            print "Ignore table found."
        c.close()

    def addTrack(self, path, hasTrackID=True):
        track = self._trackFactory.getTrackFromPathNoID(self, path)
        if track == None:
            print "Invalid file."
            return None
        c = self._conn.cursor()
        trackID = None
        if hasTrackID == True:
            trackID = self._getTrackID(track)
        path = track.getPath()
        if hasTrackID == False or trackID == None:
            c.execute("""insert into tracks (path, artist, album, title,
                      tracknumber, unscored) values (?, ?, ?, ?, ?, 1)""",
                      (path, track.getArtist(), track.getAlbum(),
                       track.getTitle(), track.getTrackNumber()))
            trackID = c.lastrowid
            print "\'"+path+"\' has been added to the library."
        else:
            print "\'"+path+"\' is already in the library."
        c.close()
        self._conn.commit()
        track.setID(self._trackFactory, trackID)
        return trackID

    def addDirectoryNoWatch(self, directory):
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = directory+'/'+contents[n]
            if os.path.isdir(path):
                self.addDirectoryNoWatch(path)
            else: ## or: elif contents[n][-4:]=='.mp3':
                self.addTrack(path)

    def addDirectory(self, directory):
        c = self._conn.cursor()
        directoryID = self.getDirectoryID(directory)
        if directoryID == None:
            c.execute("insert into directories (path) values (?)",
                      (directory, ))
            print "\'"+directory+"\' has been added to the watch list."
        else:
            print "\'"+directory+"\' is already in the watch list."
        c.close()
        self._conn.commit()
        self.addDirectoryNoWatch(directory)

    def removeDirectory(self, directory):
        c = self._conn.cursor()
        directoryID = self.getDirectoryID(directory)
        if directoryID != None:
            c.execute("delete from directories where path = ?", (directory, ))
            print "\'"+directory+"\' has been removed from the watch list."
        else:
            print "\'"+directory+"\' is not in the watch list."
        c.close()
        self._conn.commit()

    def rescanDirectories(self):
        c = self._conn.cursor()
        c.execute("select path from directories")
        result = c.fetchall()
        for n in result:
            self.addDirectoryNoWatch(n[0])
        self._conn.commit()

## FIXME: needs to deal with two links using the same first or second track
    def addLink(self, firstTrack, secondTrack):
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        if firstTrackID == None:
            print "\'"+self.getPath(firstTrack)+"\' is not in the library."
            return
        if secondTrackID == None:
            print "\'"+self.getPath(secondTrack)+"\' is not in the library."
            return
        linkID = self.getLinkID(firstTrack, secondTrack)
        if linkID == None:
            c.execute("""insert into links (firsttrackid, secondtrackid) values
                      (?, ?)""", (firstTrackID, secondTrackID))
            print "The link has been added."
        else:
            print "The link already exists."
        c.close()
        self._conn.commit()

    def getLinkID(self, firstTrack, secondTrack):
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        if firstTrackID == None:
            print "\'"+self.getPath(firstTrack)+"\' is not in the library."
            return
        if secondTrackID == None:
            print "\'"+self.getPath(secondTrack)+"\' is not in the library."
            return
        c.execute("""select linkid from links where firsttrackid = ? and
                  secondtrackid = ?""", (firstTrackID, secondTrackID))
        result = c.fetchone()
        c.close()
        if result == None:
            return None
        else:
            return result[0]

## if there are two links for a track, returns the link with track as second
## track first for queueing ease
    def getLinkIDs(self, track):
        c = self._conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
            return
        c.execute("select linkid from links where secondtrackid = ?",
                  (trackID, ))
        firstResult = c.fetchone()
        c.execute("select linkid from links where firsttrackid = ?",
                  (trackID, ))
        secondResult = c.fetchone()
        c.close()
        if firstResult == None:
            if secondResult == None:
                return None
            else:
                return secondResult[0]
        else:
            if secondResult == None:
                return firstResult[0]
            else:
                return firstResult[0], secondResult[0]

    def getLinkedTrackIDs(self, linkID):
        c = self._conn.cursor()
        c.execute("""select firsttrackid, secondtrackid from links where
                  linkid = ?""", (linkID, ))
        result = c.fetchone()
        c.close()
        if result == None:
            return None
        else:
            return result

    def removeLink(self, firstTrack, secondTrack):
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        if firstTrackID == None:
            print "\'"+self.getPath(firstTrack)+"\' is not in the library."
            return
        if secondTrackID == None:
            print "\'"+self.getPath(secondTrack)+"\' is not in the library."
            return
        linkID = self.getLinkID(firstTrack, secondTrack)
        if linkID != None:
            c.execute("""delete from links where firsttrackid = ? and
                      secondtrackid = ?""", (firstTrackID, secondTrackID))
            print "The link has been removed."
        else:
            print "The link does not exist."
        c.close()
        self._conn.commit()

    ## poss add track if track not in library
    def addPlay(self, track):
        c = self._conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
            return
        c.execute("""insert into plays (trackid, datetime) values
                  (?, datetime('now'))""", (trackID, ))
        c.close()
        self._conn.commit()

## returns a list of tuples of the form (trackID, )
    def getAllTrackIDs(self):
        c = self._conn.cursor()
        c.execute("select trackid from tracks")
        result = c.fetchall()
        c.close()
        return result

    def _getTrackID(self, track):
        c = self._conn.cursor()
        c.execute("select trackid from tracks where path = ?",
                  (track.getPath(), ))
        result = c.fetchone()
        c.close()
        if result == None:
            return None
        else:
            return result[0]

    def getTrackID(self, track):
        trackID = self._getTrackID(track)
        if trackID == None:
            return self.addTrack(track.getPath(), hasTrackID=False)
        return trackID

    def getDirectoryID(self, path):
        c = self._conn.cursor()
        c.execute("select directoryid from directories where path = ?",
                  (path, ))
        result = c.fetchone()
        c.close()
        if result == None:
            return None
        else:
            return result[0]

    def _getLastPlayed(self, track=None, trackID=None):
        (self.basicLastPlayedIndex, self.localLastPlayedIndex,
        self.secondSinceLastPlayedIndex) = range(3)
        if trackID == None:
            if track == None:
                raise NoTrackError
##                print "No track has been identified."
##                return None
            trackID = track.getID()
        c = self._conn.cursor()
        c.execute("""select datetime, datetime(datetime, 'localtime'),
                  strftime('%s', 'now') - strftime('%s', datetime) from plays
                  where trackid = ? order by playid desc""", (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result
        else:
            return None

    def getLastPlayed(self, track):
        details = self._getLastPlayed(track=track)
        if details == None:
            return None
        return details[self.basicLastPlayedIndex]
##        return self._getLastPlayed("datetime", track=track)

    def getLastPlayedLocalTime(self, track):
        details = self._getLastPlayed(track=track)
        if details == None:
            return None
        return details[self.localLastPlayedIndex]
##        return self._getLastPlayed("datetime(datetime, 'localtime')",
##                                   track=track)

##    def getTimeSinceLastPlayed(self, track):
##        return self._getLastPlayed("datetime('now') - datetime", track=track)
####        return self._getLastPlayed("strftime('%J days, %H hrs, %M mins, %S secs ago', (datetime('now') - datetime))", track=track)

    def getSecondsSinceLastPlayedFromID(self, trackID):
        details = self._getLastPlayed(trackID=trackID)
        if details == None:
            return None
        return details[self.secondsSinceLastPlayedIndex]
##        return self._getLastPlayed(
##            "strftime('%s', 'now') - strftime('%s', datetime)", trackID=trackID)

    def _getTrackDetails(self, track=None, trackID=None):
        (self.pathIndex, self.artistIndex, self.albumIndex, self.titleIndex,
        self.trackNumberIndex, self.unscoredIndex) = range(6)
        if trackID == None:
            if track == None:
                raise NoTrackError
##                print "No track has been identified."
##                return None
            trackID = track.getID()
        c = self._conn.cursor()
        c.execute("""select path, artist, album, title, tracknumber, unscored
                  from tracks where trackid = ?""", (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result
        else:
            return None

    def getPath(self, track):
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.pathIndex]

    def getPathFromID(self, trackID):
        details = self._getTrackDetails(trackID=trackID)
        if details == None:
            return None
        return details[self.pathIndex]

    def getArtist(self, track):
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.artistIndex]

    def getAlbum(self, track):
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.albumIndex]

    def getTitle(self, track):
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.titleIndex]

    def getTrackNumber(self, track):
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.trackNumberIndex]

    ## determines whether user has changed score for this track
    def _isScored(self, track=None, trackID=None):
        if trackID != None:
            details = self._getTrackDetails(trackID=trackID)
        else:
            details = self._getTrackDetails(track=track)
        if details == None:
            return None
        if details[self.unscoredIndex] == 1:
            return False
        elif details[self.unscoredIndex] == 0:
            return True

    def isScored(self, track):
        return self._isScored(track=track)

    def isScoredFromID(self, trackID):
        return self._isScored(trackID=trackID)

    ## poss should add a record to scores table
    def setUnscored(self, track):
        c = self._conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
        else:
##            c.execute("""insert into scores (trackid, score, datetime) values
##                      (?, ?, datetime('now'))""", (trackID,
##                                                   self._defaultScore, ))
            c.execute("""update tracks set unscored = 1 where
                      trackid = ?""", (trackID, ))
        c.close()
        self._conn.commit()

    ## poss add track if track not in library
    def setScore(self, track, score):
        c = self._conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
            return
        c.execute("update tracks set unscored = 0 where trackid = ?",
                  (trackID, ))
        c.execute("""insert into scores (trackid, score, datetime) values
                  (?, ?, datetime('now'))""", (trackID, score, ))
        c.close()
        self._conn.commit()

    def _getScore(self, track=None, trackID=None):
        if trackID == None:
            if track == None:
                raise NoTrackError
##                print "No track has been identified."
##                return None
            trackID = track.getID()
        c = self._conn.cursor()
        c.execute("""select score from scores where trackid = ? order by
                  scoreid desc""", (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
##        else:
##            print "\'"+self.getPath(track)+"\' has no score associated with it in the library."

    def getScore(self, track):
        if self.isScored(track) == False:
            return "-"
        return self._getScore(track=track)

    def getScoreValue(self, track):
        if self.isScored(track) == False:
            return self._defaultScore
        return self._getScore(track=track)

    def getScoreValueFromID(self, trackID):
        if self.isScoredFromID(trackID) == False:
            return self._defaultScore
        return self._getScore(trackID=trackID)
