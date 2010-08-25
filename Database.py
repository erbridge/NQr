## Database Control
## TODO: check metadata haven't changed when grabbing track?
## TODO: use a hash as a track identifier instead of path to allow for path
##       changes.
## TODO: add a function to remove the last play record (to undo the play)
## TODO: add ignore list
## TODO: check if track table already exists first to confirm whether or not
##       to create other tables (poss corruption)
## TODO: add more attributes to tracks

from Errors import *
import os
import sqlite3

class Database:
    def __init__(self, trackFactory, loggerFactory, databasePath="database",
                 defaultScore=10):
        self._trackFactory = trackFactory
        self._loggerFactory = loggerFactory
        self._logger = self._loggerFactory.getLogger("NQr.Database", "debug")
        self._databasePath = databasePath
        self._defaultScore = defaultScore
        self._logger.debug("Opening connection to database at "\
                           +self._databasePath+".")
        self._conn = sqlite3.connect(self._databasePath)
        self._initCreateTrackTable()
        self._initCreateDirectoryTable()
        self._initCreatePlaysTable()
        self._initCreateEnqueuesTable()
        self._initCreateScoresTable()
        self._initCreateLinksTable()
        self._initCreateIgnoreTable()
        self._conn.commit()

    def _initCreateTrackTable(self):
        self._logger.debug("Looking for track table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table tracks (trackid integer primary key
                                              autoincrement, path text,
                                              artist text, album text,
                                              title text, tracknumber text,
                                              unscored integer)""")
            self._logger.info("Track table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tracks already exists":
                raise err
            self._logger.debug("Track table found.")
##            print "Tracks table found."
        c.close()

    def _initCreateDirectoryTable(self):
        self._logger.debug("Looking for directory table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table directories (directoryid integer primary
                                                   key autoincrement,
                                                   path text)""")
            self._logger.info("Directory table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table directories already exists":
                raise err
            self._logger.debug("Directory table found.")
        c.close()

    def _initCreatePlaysTable(self):
        self._logger.debug("Looking for play table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table plays (playid integer primary key
                                             autoincrement, trackid integer,
                                             datetime text)""")
            self._logger.info("Play table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table plays already exists":
                raise err
            self._logger.debug("Play table found.")
        c.close()

    def _initCreateEnqueuesTable(self):
        self._logger.debug("Looking for enqueue table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table enqueues (enqueueid integer primary key
                                                autoincrement, trackid integer,
                                                datetime text)""")
            self._logger.info("Enqueue table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table enqueues already exists":
                raise err
            self._logger.debug("Enqueue table found.")
        c.close()

    def _initCreateScoresTable(self):
        self._logger.debug("Looking for score table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table scores (scoreid integer primary key
                                              autoincrement, trackid integer,
                                              score integer, datetime text)""")
            self._logger.info("Score table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table scores already exists":
                raise err
            self._logger.debug("Score table found.")
        c.close()

    def _initCreateLinksTable(self):
        self._logger.debug("Looking for track link table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table links (linkid integer primary key
                                             autoincrement, firsttrackid
                                             integer, secondtrackid integer)""")
            self._logger.info("Track link table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table links already exists":
                raise err
            self._logger.debug("Track link table found.")
        c.close()

    def _initCreateIgnoreTable(self):
        self._logger.debug("Looking for ignore table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table ignore (ignoreid integer primary key
                                              autoincrement, trackid
                                              integer)""")
            self._logger.info("Ignore table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table ignore already exists":
                raise err
            self._logger.debug("Ignore table found.")
        c.close()

    def addTrack(self, path, hasTrackID=True):
        self._logger.debug("Adding \'"+path+"\' to the library.")
        track = self._trackFactory.getTrackFromPathNoID(self, path)
        if track == None:
            self._logger.debug("\'"+path+"\' is an invalid file.")
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
            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self._logger.debug("\'"+path+"\' is already in the library.")
        c.close()
        self._conn.commit()
        track.setID(self._trackFactory, trackID)
        return trackID

    ## returns a list of tuples of the form (trackID, )
    def getAllTrackIDs(self):
        self._logger.debug("Retrieving all track IDs.")
        c = self._conn.cursor()
        c.execute("select trackid from tracks")
        result = c.fetchall()
        c.close()
        return result

    def _getTrackID(self, track):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        c = self._conn.cursor()
        c.execute("select trackid from tracks where path = ?",
                  (path, ))
        result = c.fetchone()
        c.close()
        if result == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
            return None
        else:
            return result[0]

    def getTrackID(self, track):
        trackID = self._getTrackID(track)
        if trackID == None:
            return self.addTrack(track.getPath(), hasTrackID=False)
        return trackID

    def addDirectory(self, directory):
        self._logger.debug("Adding \'"+directory+"\' to the watch list.")
        c = self._conn.cursor()
        directoryID = self.getDirectoryID(directory)
        if directoryID == None:
            c.execute("insert into directories (path) values (?)",
                      (directory, ))
            self._logger.info("\'"+directory\
                               +"\' has been added to the watch list.")
        else:
            self._logger.debug("\'"+directory\
                               +"\' is already in the watch list.")
        c.close()
        self._conn.commit()
        self.addDirectoryNoWatch(directory)

    def getDirectoryID(self, directory):
        self._logger.debug("Retrieving directory ID for \'"+directory+"\'.")
        c = self._conn.cursor()
        c.execute("select directoryid from directories where path = ?",
                  (directory, ))
        result = c.fetchone()
        c.close()
        if result == None:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
            return None
        else:
            return result[0]

    def addDirectoryNoWatch(self, directory):
        self._logger.debug("Adding files in \'"+directory+"\' to the library.")
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = os.path.abspath(directory+'/'+contents[n])
            if os.path.isdir(path):
                self.addDirectoryNoWatch(path)
            else: ## or: elif contents[n][-4:]=='.mp3':
                self.addTrack(path)

    def removeDirectory(self, directory):
        self._logger.debug("Removing \'"+directory+"\' from the watch list.")
        c = self._conn.cursor()
        directoryID = self.getDirectoryID(directory)
        if directoryID != None:
            c.execute("delete from directories where path = ?", (directory, ))
            self._logger.info("\'"+directory\
                               +"\' has been removed from the watch list.")
        else:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
        c.close()
        self._conn.commit()

    def rescanDirectories(self):
        self._logger.debug("Rescanning the watch list for new files.")
        c = self._conn.cursor()
        c.execute("select path from directories")
        result = c.fetchall()
        for (directory, ) in result:
            self.addDirectoryNoWatch(directory)
        self._conn.commit()

## FIXME: needs to deal with two links using the same first or second track
    def addLink(self, firstTrack, secondTrack):
        self._logger.debug("Creating track link.")
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        firstTrackPath = self.getPathFromID(firstTrackID)
        secondTrackPath = self.getPathFromID(secondTrackID)
##        if firstTrackID == None:
##            self._logger.debug("\'"+self.getPath(firstTrack)\
##                               +"\' is not in the library.")
##            return
##        if secondTrackID == None:
##            self._logger.debug("\'"+self.getPath(secondTrack)\
##                               +"\' is not in the library.")
##            return
        linkID = self.getLinkID(firstTrack, secondTrack)
        if linkID == None:
            c.execute("""insert into links (firsttrackid, secondtrackid) values
                      (?, ?)""", (firstTrackID, secondTrackID))
            self._logger.info("\'"+firstTrackPath+"\' has been linked to \'"\
                               +secondTrackPath+"\'.")
        else:
            self._logger.debug("\'"+firstTrackPath+"\' is already linked to \'"\
                               +secondTrackPath+"\'.")
        c.close()
        self._conn.commit()

    def getLinkID(self, firstTrack, secondTrack):
        self._logger.debug("Retrieving link ID.")
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        firstTrackPath = self.getPathFromID(firstTrackID)
        secondTrackPath = self.getPathFromID(secondTrackID)
##        if firstTrackID == None:
##            self._logger.debug("\'"+self.getPath(firstTrack)\
##                               +"\' is not in the library.")
##            return
##        if secondTrackID == None:
##            self._logger.debug("\'"+self.getPath(secondTrack)\
##                               +"\' is not in the library.")
##            return
        c.execute("""select linkid from links where firsttrackid = ? and
                  secondtrackid = ?""", (firstTrackID, secondTrackID))
        result = c.fetchone()
        c.close()
        if result == None:
            self._logger.debug("\'"+firstTrackPath+"\' is not linked to \'"\
                               +secondTrackPath+"\'.")
            return None
        else:
            return result[0]

    ## if there are two links for a track, returns the link with track as second
    ## track first for queueing ease
    def getLinkIDs(self, track):
        self._logger.debug("Retrieving link IDs.")
        c = self._conn.cursor()
        trackID = track.getID()
        path = self.getPathFromID(trackID)
##        if trackID == None:
##            self._logger.debug("\'"+self.getPath(track)\
##                               +"\' is not in the library.")
##            return
        c.execute("select linkid from links where secondtrackid = ?",
                  (trackID, ))
        firstResult = c.fetchone()
        c.execute("select linkid from links where firsttrackid = ?",
                  (trackID, ))
        secondResult = c.fetchone()
        c.close()
        if firstResult == None:
            if secondResult == None:
                self._logger.debug("\'"+path\
                                   +"\' is not linked to another track.")
                return None
            else:
                return secondResult[0]
        else:
            if secondResult == None:
                return firstResult[0]
            else:
                return firstResult[0], secondResult[0]

    def getLinkedTrackIDs(self, linkID):
        self._logger.debug("Retrieving track IDs for linked tracks.")
        c = self._conn.cursor()
        c.execute("""select firsttrackid, secondtrackid from links where
                  linkid = ?""", (linkID, ))
        result = c.fetchone()
        c.close()
        if result == None:
            self._logger.debug("No such link exists.")
            return None
        else:
            return result

    def removeLink(self, firstTrack, secondTrack):
        self._logger.debug("Removing link.")
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        firstTrackPath = self.getPathFromID(firstTrackID)
        secondTrackPath = self.getPathFromID(secondTrackID)
##        if firstTrackID == None:
##            self._logger.debug("\'"+self.getPath(firstTrack)\
##                               +"\' is not in the library.")
##            return
##        if secondTrackID == None:
##            self._logger.debug("\'"+self.getPath(secondTrack)\
##                               +"\' is not in the library.")
##            return
        linkID = self.getLinkID(firstTrack, secondTrack)
        if linkID != None:
            c.execute("""delete from links where firsttrackid = ? and
                      secondtrackid = ?""", (firstTrackID, secondTrackID))
            self._logger.info("\'"+firstTrackPath\
                              +"\' is no longer linked to \'"+secondTrackPath\
                              +"\'.")
        else:
            self._logger.debug("\'"+firstTrackPath+"\' is not linked to \'"\
                               +secondTrackPath+"\'.")
        c.close()
        self._conn.commit()

    def addEnqueue(self, track):
        self._logger.debug("Adding enqueue.")
        c = self._conn.cursor()
        trackID = track.getID()
##        if trackID == None:
##            self._logger.debug("\'"+self.getPath(track)\
##                               +"\' is not in the library.")
##            return
        c.execute("""insert into enqueues (trackid, datetime) values
                  (?, datetime('now'))""", (trackID, ))
        c.close()
        self._conn.commit()

    def getSecondsSinceLastEnqueuedFromID(self, trackID):
        self._logger.debug("Calculating time since last enqueued.")
        if trackID == None:
            self._logger.error("No track has been identified.")
            raise NoTrackError
##            return None
        c = self._conn.cursor()
        c.execute("""select strftime('%s', 'now') - strftime('%s', datetime)
                  from enqueues where trackid = ? order by enqueueid desc""",
                  (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            self._logger.debug("\'"+self.getPath(trackID)\
                               +"\'has never been enqueued.")
            return None

    def addPlay(self, track):
        self._logger.debug("Adding play.")
        c = self._conn.cursor()
        trackID = track.getID()
##        if trackID == None:
##            self._logger.debug("\'"+self.getPath(track)\
##                               +"\' is not in the library.")
##            return
        c.execute("""insert into plays (trackid, datetime) values
                  (?, datetime('now'))""", (trackID, ))
        c.close()
        self._conn.commit()

    def getLastPlayedTrackID(self):
        c = self._conn.cursor()
        c.execute("""select trackid from plays order by playid desc""")
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            self._logger.error("No plays recorded.")
            raise EmptyDatabaseError

    def _getLastPlayed(self, track=None, trackID=None):
        (self.basicLastPlayedIndex, self.localLastPlayedIndex,
        self.secondsSinceLastPlayedIndex) = range(3)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
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
            self._logger.debug("\'"+self.getPath(trackID)\
                               +"\'has never been played.")
            return None

    def getLastPlayed(self, track):
        self._logger.debug("Retrieving time of last play.")
        details = self._getLastPlayed(track=track)
        if details == None:
            return None
        return details[self.basicLastPlayedIndex]
##        return self._getLastPlayed("datetime", track=track)

    def getLastPlayedLocalTime(self, track):
        self._logger.debug("Retrieving time of last play in localtime.")
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
        self._logger.debug("Calculating time since last played.")
        details = self._getLastPlayed(trackID=trackID)
        if details == None:
            return None
        return details[self.secondsSinceLastPlayedIndex]
##        return self._getLastPlayed(
##            "strftime('%s', 'now') - strftime('%s', datetime)", trackID=trackID)

    def getPlayCount(self, track=None, trackID=None):
        self._logger.debug("Retrieving play count.")
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
##                return None
            trackID = track.getID()
        c = self._conn.cursor()
        c.execute("""select datetime from plays where trackid = ? order by
                  playid desc""", (trackID, ))
        result = c.fetchall()
        c.close()
        if result == None:
            return 0
        count = len(result)
        return count

    def _getTrackDetails(self, track=None, trackID=None):
        (self.pathIndex, self.artistIndex, self.albumIndex, self.titleIndex,
        self.trackNumberIndex, self.unscoredIndex) = range(6)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
##                return None
            trackID = track.getID()
        c = self._conn.cursor()
        c.execute("""select path, artist, album, title, tracknumber, unscored
                  from tracks where trackid = ?""", (trackID, ))
        result = c.fetchone()
        c.close()
##        if result != None:
        return result
##        else:
##            return None

    def getPath(self, track):
        self._logger.debug("Retrieving track's path.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.pathIndex]

    def getPathFromID(self, trackID):
        self._logger.debug("Retrieving track's path.")
        details = self._getTrackDetails(trackID=trackID)
        if details == None:
            return None
        return details[self.pathIndex]

    def getArtist(self, track):
        self._logger.debug("Retrieving track's artist.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.artistIndex]

    def getAlbum(self, track):
        self._logger.debug("Retrieving track's album.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.albumIndex]

    def getTitle(self, track):
        self._logger.debug("Retrieving track's title.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.titleIndex]

    def getTrackNumber(self, track):
        self._logger.debug("Retrieving track's number.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self.trackNumberIndex]

## FIXME: should be _getIsScored()?
    ## determines whether user has changed score for this track
    def _isScored(self, track=None, trackID=None):
        self._logger.debug("Retrieving track's unscored status.")
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
        self._logger.debug("Setting track as unscored.")
        c = self._conn.cursor()
        trackID = track.getID()
##        if trackID == None:
##            self._logger.debug("\'"+self.getPath(track)\
##                               +"\' is not in the library.")
##            c.execute("""insert into scores (trackid, score, datetime) values
##                      (?, ?, datetime('now'))""", (trackID,
##                                                   self._defaultScore, ))
        c.execute("""update tracks set unscored = 1 where trackid = ?""",
                  (trackID, ))
        c.close()
        self._conn.commit()

    ## poss add track if track not in library
    def setScore(self, track, score):
        self._logger.debug("Setting track's score.")
        c = self._conn.cursor()
        trackID = track.getID()
##        if trackID == None:
##            self._logger.debug("\'"+self.getPath(track)\
##                               +"\' is not in the library.")
##            return
        c.execute("update tracks set unscored = 0 where trackid = ?",
                  (trackID, ))
        c.execute("""insert into scores (trackid, score, datetime) values
                  (?, ?, datetime('now'))""", (trackID, score, ))
        c.close()
        self._conn.commit()

    def _getScore(self, track=None, trackID=None):
        self._logger.debug("Retrieving track's score.")
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
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
