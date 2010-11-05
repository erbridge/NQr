## Database Control
##
## TODO: use a hash as a track identifier instead of path to allow for path
##       changes.
## TODO: add a function to remove the last play record (to undo the play)?
## TODO: add functions to populate ignore list
## TODO: check if track table already exists first to confirm whether or not
##       to create other tables (poss corruption)

import ConfigParser
import datetime
from Errors import *
import os
import sqlite3
from Util import *

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

class Database:
    def __init__(self, trackFactory, loggerFactory, configParser,
                 debugMode=False, databasePath="database",
                 defaultDefaultScore=10):
        self._trackFactory = trackFactory
        self._logger = loggerFactory.getLogger("NQr.Database", "debug")
        self._configParser = configParser
        self._defaultDefaultScore = defaultDefaultScore
        self.loadSettings()
        self._debugMode = debugMode
        self._databasePath = databasePath
        self._logger.debug("Opening connection to database at "\
                           +self._databasePath+".")
        self._conn = sqlite3.connect(self._databasePath)
        self._conn.isolation_level = None
        self._initMaybeCreateTrackTable()
        self._initMaybeCreateDirectoryTable()
        self._initMaybeCreatePlaysTable()
        self._initMaybeCreateEnqueuesTable()
        self._initMaybeCreateScoresTable()
        self._initMaybeCreateLinksTable()
        self._initMaybeCreateIgnoreTable()
        self._initMaybeCreateTagNamesTable()
        self._initMaybeCreateTagsTable()
        self._conn.commit()
        self._cursor = self._conn.cursor()

    def _initMaybeCreateTrackTable(self):
        self._logger.debug("Looking for track table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table tracks (trackid integer primary key
                                              autoincrement, path text,
                                              artist text, album text,
                                              title text, tracknumber text,
                                              unscored integer, length real, bpm
                                              integer, historical integer)""")
            self._logger.info("Track table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tracks already exists":
                raise err
            self._logger.debug("Track table found.")
            c.execute("pragma table_info(tracks)")
            details = c.fetchall()
            columnNames = []
            for detail in details:
                columnNames.append(detail[1])
            if columnNames.count('length') == 0:
                self._logger.debug("Adding length column to track table.")
                c.execute("alter table tracks add column length real")
            if columnNames.count('bpm') == 0:
                self._logger.debug("Adding bpm column to track table.")
                c.execute("alter table tracks add column bpm integer")
            if columnNames.count('historical') == 0:
                self._logger.debug("Adding historical column to track table.")
                c.execute("alter table tracks add column historical integer")
                c.execute("update tracks set historical = 0")
        c.close()

    def _initMaybeCreateDirectoryTable(self):
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

    def _initMaybeCreatePlaysTable(self):
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

    def _initMaybeCreateEnqueuesTable(self):
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

    def _initMaybeCreateScoresTable(self):
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

    def _initMaybeCreateLinksTable(self):
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

    def _initMaybeCreateIgnoreTable(self):
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

    def _initMaybeCreateTagNamesTable(self):
        self._logger.debug("Looking for tag names table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table tagnames (tagnameid integer primary key,
                                                name text)""")
            self._logger.info("Tag names table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tagnames already exists":
                raise err
            self._logger.debug("Tag names table found.")
        c.close()

    def _initMaybeCreateTagsTable(self):
        self._logger.debug("Looking for tags table.")
        c = self._conn.cursor()
        try:
            c.execute("""create table tags (tagid integer primary key,
                                            tagnameid integer,
                                            trackid integer)""")
            self._logger.info("Tags table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tags already exists":
                raise err
            self._logger.debug("Tags table found.")
        c.close()

    def _executeAndFetchoneOrNull(self, stmt, args = ()):
        self._cursor.execute(stmt, args)
        result = self._cursor.fetchone()
        if result is None:
            return None
        return result[0]

    def _executeAndFetchone(self, stmt, args = ()):
        result = self._executeAndFetchoneOrNull(stmt, args)
        if result is None:
            raise NoResultError()
        return result

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
                         tracknumber, unscored, length, bpm, historical) values
                         (?, ?, ?, ?, ?, 1, ?, ?, 0)""",
                      (path, track.getArtist(), track.getAlbum(),
                       track.getTitle(), track.getTrackNumber(),
                       track.getLength(), track.getBPM()))
            trackID = c.lastrowid
            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self._logger.debug("\'"+path+"\' is already in the library.")
        c.close()
        self._conn.commit()
        track.setID(self._trackFactory, trackID)
        return trackID

    ## returns a list of tuples of the form (trackID, )
    ## FIXME: make faster by doing something like: select
    ## tracks.trackid, score, plays.datetime from tracks left outer
    ## join scores using (trackid) left outer join plays using
    ## (trackid); with some select trackid, max(datetime) from plays
    ## group by trackid; thrown in.
    def getAllTrackIDs(self):
        self._logger.debug("Retrieving all track IDs.")
        c = self._conn.cursor()
        c.execute("select trackid from tracks")
        result = c.fetchall()
        c.close()
        return result

    def _getTrackID(self, track, update=False):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        result = self._executeAndFetchoneOrNull(
            "select trackid from tracks where path = ?", (path, ))
        if result == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
            if update == True:
                raise NoTrackError
        return result

    def getTrackID(self, track, update=False):
        trackID = self._getTrackID(track, update)
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
        result = self._executeAndFetchoneOrNull(
            "select directoryid from directories where path = ?", (directory, ))
        if result == None:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
        return result

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
        firstTrackPath = self.getPathFromIDNoDebug(firstTrackID)
        secondTrackPath = self.getPathFromIDNoDebug(secondTrackID)
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
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        firstTrackPath = self.getPathFromIDNoDebug(firstTrackID)
        secondTrackPath = self.getPathFromIDNoDebug(secondTrackID)
        result = self._executeAndFetchoneOrNull(
            """select linkid from links where firsttrackid = ? and
               secondtrackid = ?""", (firstTrackID, secondTrackID))
        if result == None:
            self._logger.debug("\'"+firstTrackPath+"\' is not linked to \'"\
                               +secondTrackPath+"\'.")
        return result

    ## if there are two links for a track, returns the link with track as second
    ## track first for queueing ease
    def getLinkIDs(self, track):
        self._logger.debug("Retrieving link IDs.")
        trackID = track.getID()
        path = self.getPathFromIDNoDebug(trackID)
        firstResult = self._executeAndFetchoneOrNull(
            "select linkid from links where secondtrackid = ?", (trackID, ))
        secondResult = self._executeAndFetchoneOrNull(
            "select linkid from links where firsttrackid = ?", (trackID, ))
        if firstResult == None:
            if secondResult == None:
                self._logger.debug("\'"+path\
                                   +"\' is not linked to another track.")
            return secondResult
        else:
            if secondResult == None:
                return firstResult
            else:
                return firstResult, secondResult

    def getLinkedTrackIDs(self, linkID):
        self._logger.debug("Retrieving track IDs for linked tracks.")
        result = self._executeAndFetchoneOrNull(
            "select firsttrackid, secondtrackid from links where linkid = ?",
            (linkID, ))
        if result == None:
            self._logger.debug("No such link exists.")
        return result

    def removeLink(self, firstTrack, secondTrack):
        self._logger.debug("Removing link.")
        c = self._conn.cursor()
        firstTrackID = firstTrack.getID()
        secondTrackID = secondTrack.getID()
        firstTrackPath = self.getPathFromIDNoDebug(firstTrackID)
        secondTrackPath = self.getPathFromIDNoDebug(secondTrackID)
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
        c.execute("""insert into enqueues (trackid, datetime) values
                     (?, datetime('now'))""", (trackID, ))
        c.close()
        self._conn.commit()

    def getSecondsSinceLastEnqueuedFromID(self, trackID):
        if trackID == None:
            self._logger.error("No track has been identified.")
            raise NoTrackError
        return self._executeAndFetchoneOrNull(
            """select strftime('%s', 'now') - strftime('%s', datetime)
               from enqueues where trackid = ? order by enqueueid desc""",
            (trackID, ))

    def addPlay(self, track, msDelay=0):
        self._logger.debug("Adding play.")
        trackID = track.getID()
        track.setPreviousPlay(self.getLastPlayedInSeconds(track))
        
        delay = datetime.timedelta(0, 0, 0, msDelay)
        now = datetime.datetime.now()
        playTime = now - delay
        self._cursor.execute("""insert into plays (trackid, datetime) values
                                (?, datetime(?))""", (trackID, playTime))

    def getLastPlayedTrackID(self):
        result = self._executeAndFetchoneOrNull(
            "select trackid from plays order by playid desc")
        if result != None:
            return result
        else:
            self._logger.error("No plays recorded.")
            raise EmptyDatabaseError

    def _getLastPlayed(self, track=None, trackID=None):
        (self.basicLastPlayedIndex, self.localLastPlayedIndex,
         self.secondsSinceLastPlayedIndex,
         self.lastPlayedInSecondsIndex) = range(4)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
            trackID = track.getID()
        c = self._conn.cursor()
        c.execute("""select datetime, datetime(datetime, 'localtime'),
                     strftime('%s', 'now') - strftime('%s', datetime),
                     strftime('%s', datetime) from plays
                     where trackid = ? order by playid desc""", (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result
        else:
            if self._debugMode == True:
                self._logger.debug("\'"+self.getPathFromIDNoDebug(trackID)\
                                   +"\' has never been played.")
            return None

    def getLastPlayed(self, track):
        self._logger.debug("Retrieving time of last play.")
        details = self._getLastPlayed(track=track)
        if details == None:
            return None
        return details[self.basicLastPlayedIndex]

    def getLastPlayedLocalTime(self, track):
        self._logger.debug("Retrieving time of last play in localtime.")
        details = self._getLastPlayed(track=track)
        if details == None:
            return None
        return details[self.localLastPlayedIndex]

    def getLastPlayedInSeconds(self, track):
        details = self._getLastPlayed(track=track)
        if details == None:
            return None
        return int(details[self.lastPlayedInSecondsIndex])

    def getSecondsSinceLastPlayedFromID(self, trackID):
        if self._debugMode == True:
            self._logger.debug("Calculating time since last played.")
        details = self._getLastPlayed(trackID=trackID)
        if details == None:
            return None
        return details[self.secondsSinceLastPlayedIndex]

    # FIXME: as soon as a file is deleted or moved, so it can't get
    # played again, this will get stuck. We need to keep track of
    # whether entries are current or historical. Partially fixed: 
    # currently bad tracks rely on being chosen by randomizer to update 
    # historical status.
    def getOldestLastPlayed(self):
        try:
            return self._executeAndFetchone(
                """select strftime('%s', 'now') - strftime('%s', min(datetime))
                   from (select max(playid) as id, trackid from plays,
                         (select trackid as historicalid from tracks where
                          historical = 0) as historicaltracks where
                         plays.trackid = historicaltracks.historicalid group by
                         trackid) as maxplays, plays where maxplays.id =
                   plays.playid""")
        except NoResultError:
            return 0

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
    
    def updateAllTrackDetails(self):
        trackIDs = self.getAllTrackIDs()
        for trackID in trackIDs:
            try:
                track = self._trackFactory.getTrackFromID()
                self.maybeUpdateTrackDetails(track)
            except NoTrackError:
                self.setHistorical(True, trackID)

    def maybeUpdateTrackDetails(self, track):
        if self._getTrackDetailsChange(track) == True:
            self._updateTrackDetails(track)

    def _updateTrackDetails(self, track):
        path = track.getPath()
        self._logger.debug("Updating \'"+path+"\' in the library.")
        c = self._conn.cursor()
        trackID = self._getTrackID(track, update=True)
        if trackID != None:
            c.execute("""update tracks set path = ?, artist = ?, album = ?,
                         title = ?, tracknumber = ?, length = ?, bpm = ? where
                         trackid = ?""", (path, track.getArtist(),
                                          track.getAlbum(), track.getTitle(),
                                          track.getTrackNumber(),
                                          track.getLength(), track.getBPM(),
                                          trackID))
            self._logger.info("\'"+path+"\' has been updated in the library.")
        else:
            self._logger.debug("\'"+path+"\' is not in the library.")
        c.close()
        self._conn.commit()

    def _getTrackDetailsChange(self, track):
        self._logger.debug("Checking whether track details have changed.")
        details = self._getTrackDetails(track=track, update=True)
        newDetails = {}
        newDetails[self._pathIndex] = track.getPath()
        newDetails[self._artistIndex] = track.getArtist()
        newDetails[self._albumIndex] = track.getAlbum()
        newDetails[self._titleIndex] = track.getTitle()
        newDetails[self._trackNumberIndex] = track.getTrackNumber()
        newDetails[self._lengthIndex] = track.getLength()
        newDetails[self._bpmIndex] = track.getBPM()
        for n in range(9):
            try:
                if details[n] != newDetails[n]:
                    return True
            except KeyError:
                continue
        return False

    def _getTrackDetails(self, track=None, trackID=None, update=False):
        (self._pathIndex, self._artistIndex, self._albumIndex, self._titleIndex,
         self._trackNumberIndex, self._unscoredIndex, self._lengthIndex,
         self._bpmIndex, self._historicalIndex) = range(9)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
            trackID = track.getID(update)
        c = self._conn.cursor()
        c.execute("""select path, artist, album, title, tracknumber, unscored,
                     length, bpm, historical from tracks where trackid = ?""",
                  (trackID, ))
        result = c.fetchone()
        c.close()
        return result

    def getPath(self, track):
        self._logger.debug("Retrieving track's path.")
        return self.getPathNoDebug(track)

    def getPathNoDebug(self, track):
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self._pathIndex]

    def getPathFromID(self, trackID):
        self._logger.debug("Retrieving track's path.")
        return self.getPathFromIDNoDebug(trackID)

    def getPathFromIDNoDebug(self, trackID):
        details = self._getTrackDetails(trackID=trackID)
        if details == None:
            return None
        return details[self._pathIndex]

    def getArtist(self, track):
        self._logger.debug("Retrieving track's artist.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self._artistIndex]

    def getAlbum(self, track):
        self._logger.debug("Retrieving track's album.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self._albumIndex]

    def getTitle(self, track):
        self._logger.debug("Retrieving track's title.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self._titleIndex]

    def getTrackNumber(self, track):
        self._logger.debug("Retrieving track's number.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self._trackNumberIndex]

    def getBPM(self, track):
        self._logger.debug("Retrieving track's bpm.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        bpm = details[self._bpmIndex]
        if bpm == None:
            bpm = track.getBPM()
            self.setBPM(bpm, track)
        return bpm

    def setBPM(self, bpm, track):
        self._logger.debug("Adding bpm to track.")
        trackID = track.getID()
        c = self._conn.cursor()
        c.execute("update tracks set bpm = ? where trackID = ?", (bpm, trackID))
        c.close()
        self._conn.commit()
        
    def getHistorical(self, track):
        self._logger.debug("Retrieving track's currency.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        return details[self._historicalIndex]
    
    def setHistorical(self, historical, trackID):
        self._logger.debug("Making track non-current.")
        c = self._conn.cursor()
        if historical == True:
            historical = 1
        elif historical == False:
            historical = 0
        c.execute("update tracks set historical = ? where trackID = ?",
                  (historical, trackID))
        c.close()
        self._conn.commit()

    def getLength(self, track):
        self._logger.debug("Retrieving track's length.")
        details = self._getTrackDetails(track=track)
        if details == None:
            return None
        length = details[self._lengthIndex]
        if length == None:
            length = track.getLength()
            self.setLength(length, track)
        return length

    def getLengthString(self, track):
        rawLength = self.getLength(track)
        return formatLength(rawLength)

    def setLength(self, length, track):
        self._logger.debug("Adding length to track.")
        trackID = track.getID()
        c = self._conn.cursor()
        c.execute("update tracks set length = ? where trackID = ?", (length,
                                                                     trackID))
        c.close()
        self._conn.commit()

    def addTagName(self, tagName):
        self._logger.debug("Adding tag name.")
        self._cursor.execute("insert into tagnames (name) values (?)",
                             (tagName, ))

    def getAllTagNames(self):
        self._logger.debug("Retrieving all tag names.")
        self._cursor.execute("select name from tagnames")
        results = self._cursor.fetchall()
        if results == None:
            return []
        tagNames = []
        for result in results:
            tagNames.append(result[0])
        return tagNames

    def getTagNameID(self, tagName):
        return self._executeAndFetchone(
            "select tagnameid from tagnames where name = ?", (tagName, ))

    def setTag(self, track, tagName):
        self._logger.info("Tagging track with '"+tagName+"'.")
        trackID = track.getID()
        tagNames = self.getTags(track)
        if tagName not in tagNames:
            tagNameID = self.getTagNameID(tagName)
            self._cursor.execute("""insert into tags (trackid, tagnameid) values
									(?, ?)""", (trackID, tagNameID))

    def unsetTag(self, track, tagName):
        trackID = track.getID()
        tagNameID = self.getTagNameID(tagName)
        self._cursor.execute("""delete from tags where tagnameid = ? and
                                trackid = ?""", (tagNameID, trackID))

    def getTags(self, track):
        trackID = track.getID()
        return self.getTagsFromTrackID(trackID)

    def getTagsFromTrackID(self, trackID):
        self._logger.debug("Retrieving track tags.")
        c = self._conn.cursor()
        c.execute("select tagnameid from tags where trackid = ?", (trackID, ))
        tagNameIDs = c.fetchall()
        c.close()
        if tagNameIDs == None:
            return []
        tagNames = []
        for tagNameID in tagNameIDs:
            tagNames.append(self._executeAndFetchone(
                "select name from tagnames where tagnameid = ?",
                (tagNameID[0], )))
        return tagNames

    ## determines whether user has changed score for this track
    def _getIsScored(self, track=None, trackID=None):
        if self._debugMode == True:
            self._logger.debug("Retrieving track's unscored status.")
        if trackID != None:
            details = self._getTrackDetails(trackID=trackID)
        else:
            details = self._getTrackDetails(track=track)
        if details == None:
            return None
        if details[self._unscoredIndex] == 1:
            return False
        elif details[self._unscoredIndex] == 0:
            return True

    def getIsScored(self, track):
        return self._getIsScored(track=track)

    def getIsScoredFromID(self, trackID):
        return self._getIsScored(trackID=trackID)

    ## poss should add a record to scores table
    def setUnscored(self, track):
        self._logger.debug("Setting track as unscored.")
        c = self._conn.cursor()
        trackID = track.getID()
        c.execute("""update tracks set unscored = 1 where trackid = ?""",
                  (trackID, ))
        c.close()
        self._conn.commit()

    ## poss add track if track not in library
    def setScore(self, track, score):
        self._logger.debug("Setting track's score.")
        c = self._conn.cursor()
        trackID = track.getID()
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
            trackID = track.getID()
        return self._executeAndFetchoneOrNull(
            "select score from scores where trackid = ? order by scoreid desc",
            (trackID, ))

    def getScore(self, track):
        if self.getIsScored(track) == False:
            return "-"
        return self._getScore(track=track)

    def getScoreValue(self, track):
        if self.getIsScored(track) == False:
            return self._defaultScore
        return self._getScore(track=track)

    def getScoreValueFromID(self, trackID):
        if self.getIsScoredFromID(trackID) == False:
            return self._defaultScore
        return self._getScore(trackID=trackID)

    def maybeGetIDFromPath(self, path):
        return self._executeAndFetchoneOrNull(
            "select trackid from tracks where path = ?", (path, ))

    def getIDFromPath(self, path):
        id = self.maybeGetIDFromPath(path)
        if id is None:
            raise PathNotFoundError()

    def getNumberOfTracks(self):
        return self._executeAndFetchone("select count(*) from tracks")

    # FIXME(ben): create indexes on tracks(trackid) and plays(trackid)
    # or this is slow!
    def getNumberOfUnplayedTracks(self):
        return self._executeAndFetchone(
            """select count(*) from tracks left outer join plays using(trackid)
               where plays.trackid is null""")

    # returns an array of [ score, count ]
    def getScoreTotals(self):
        self._cursor.execute(
            """select score, count(score)
               from (select max(scoreid), x.trackid, score
                     from scores, (select distinct trackid from scores) as x
                     where scores.trackid = x.trackid group by scores.trackid)
               group by score;""")
        return self._cursor.fetchall()

    def getPrefsPage(self, parent, logger):
        return PrefsPage(parent, self._configParser, logger,
                         self._defaultDefaultScore), "Database"

    def loadSettings(self):
        try:
            self._configParser.add_section("Database")
        except ConfigParser.DuplicateSectionError:
            pass
        try:
            self._defaultScore = self._configParser.getint("Database",
                                                           "defaultScore")
        except ConfigParser.NoOptionError:
            self._defaultScore = self._defaultDefaultScore

class PrefsPage(wx.Panel):
    def __init__(self, parent, configParser, logger, defaultDefaultScore):
        wx.Panel.__init__(self, parent)
        self._logger = logger
        self._defaultDefaultScore = defaultDefaultScore
        self._settings = {}
        self._configParser = configParser
        try:
            self._configParser.add_section("Database")
        except ConfigParser.DuplicateSectionError:
            pass
        self._loadSettings()
        self._initCreateDefaultScoreSizer()

        self.SetSizer(self._defaultScoreSizer)

    def _initCreateDefaultScoreSizer(self):
        self._defaultScoreSizer = wx.BoxSizer(wx.HORIZONTAL)

        defaultScoreLabel = wx.StaticText(self, -1, "Default Score: ")
        self._defaultScoreSizer.Add(defaultScoreLabel, 0,
                                    wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._defaultScoreControl = wx.TextCtrl(
            self, -1, str(self._settings["defaultScore"]), size=(35,-1))
        self._defaultScoreSizer.Add(self._defaultScoreControl, 0)

        self.Bind(wx.EVT_TEXT, self._onDefaultScoreChange,
                  self._defaultScoreControl)

    def _onDefaultScoreChange(self, e):
        defaultScore = self._defaultScoreControl.GetLineText(0)
        if defaultScore != "":
            self._settings["defaultScore"] = int(defaultScore)

    def savePrefs(self):
        self._logger.debug("Saving database preferences.")
        for (name, value) in self._settings.items():
            self.setSetting(name, value)

    def setSetting(self, name, value):
        self._configParser.set("Database", name, value)

    def _loadSettings(self):
        try:
            ## FIXME: poss should be main setting?
            defaultScore = self._configParser.getint("Database", "defaultScore")
            self._settings["defaultScore"] = defaultScore
        except ConfigParser.NoOptionError:
            self._settings["defaultScore"] = self._defaultDefaultScore
