## Database Control
##
## TODO: use a hash as a track identifier instead of path to allow for path
##       changes.
## TODO: add a function to remove the last play record (to undo the play)?
## TODO: add functions to populate ignore list
## TODO: check if track table already exists first to confirm whether or not
##       to create other tables (poss corruption)
## TODO: finish asyncing everything
##
## FIXME: make tracebacks work properly for all completions?

import ConfigParser
import datetime
from Errors import *
import os
import Queue
import sqlite3
import sys
import threading
import traceback
from Util import *

import wxversion
wxversion.select([x for x in wxversion.getInstalled()
                  if x.find('unicode') != -1])
import wx

class Thread(threading.Thread): # FIXME: add interrupt?
    def __init__(self, db, path, name):
        threading.Thread.__init__(self, name=name)
        self._db = db
        self._databasePath = os.path.realpath(path)
        self._queue = Queue.PriorityQueue()
        
    def queue(self, thing, priority=1):
        self._queue.put((priority, thing))

    def run(self):
        conn = sqlite3.connect(self._databasePath)
        cursor = conn.cursor()
        while True:
            got = self._queue.get()[1] # appears not to get in order of put
            got(self, cursor)
            
class EventHandler(wx.EvtHandler):
    def __init__(self, dbThread):
        wx.EvtHandler.__init__(self)
        self._dbThread = dbThread
        
        EVT_DATABASE(self, self._onDatabaseEvent)
        EVT_EXCEPTION(self, self._onExceptionEvent)
        
    def _onDatabaseEvent(self, e):
        self._logger.debug("Got event.")
        e.complete()
        
    def _onExceptionEvent(self, e):
        raise e.getException()
        
    def _asyncExecute(self, stmt, args, completion, priority=1):
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.execute(stmt, args, mycompletion, priority)
    
    def _asyncExecuteAndFetchOne(self, stmt, args, completion, priority=1):
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchOne(stmt, args, mycompletion, priority)
        
    def _asyncExecuteAndFetchOneOrNull(self, stmt, args, completion,
                                       priority=1):
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchOneOrNull(stmt, args, mycompletion,
                                                priority)
        
    def _asyncExecuteAndFetchAll(self, stmt, args, completion, priority=1):
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchAll(stmt, args, mycompletion, priority)
        
    def _asyncExecuteAndFetchLastRowID(self, stmt, args, completion,
                                       priority=1):
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchLastRowID(stmt, args, mycompletion,
                                                priority)

class DirectoryWalkThread(Thread, EventHandler):
    def __init__(self, db, path, logger, trackFactory, dbThread):
        EventHandler.__init__(self, dbThread)
        Thread.__init__(self, db, path, "Directory Walk")
        self._logger = logger
        self._trackFactory = trackFactory

    def _getTrackIDCompletion(self, track, path, trackID, completion):
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        if trackID == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
        track.setID(self._trackFactory, trackID)
        completion(trackID)
    
    def getTrackID(self, track, path, completion):
        mycompletion = lambda trackID: self._getTrackIDCompletion(track, path,
                                                                  trackID,
                                                                  completion)
        self._asyncExecuteAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ), mycompletion,
            priority=2)
        
    def _addTrackCompletion(self, path, track, trackID):
        self._logger.debug("Adding \'"+path+"\' to the library.")
#        if hasTrackID == False or trackID == None:
        if trackID == None:
            mycompletion = lambda result:\
                self._logger.info("\'"+path+"\' has been added to the library.")
            self._asyncExecute("""insert into tracks (path, artist, album,
                                  title, tracknumber, unscored, length, bpm,
                                  historical) values
                                  (?, ?, ?, ?, ?, 1, ?, ?, 0)""",
                               (path, track.getArtist(), track.getAlbum(),
                                track.getTitle(), track.getTrackNumber(),
                                track.getLength(), track.getBPM()),
                               mycompletion, priority=2)
#            trackID = cursor.lastrowid
#            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self._logger.debug("\'"+path+"\' is already in the library.")
        track.setID(self._trackFactory, trackID)
#        return trackID
        
    def doAddTrack(self, path):
        try:
            track = self._trackFactory.getTrackFromPathNoID(self, path,
                                                            useCache=False,
                                                            useCompletion=True)
        except NoTrackError:
#            track = None
            self._logger.debug("\'"+path+"\' is an invalid file.")
            return
#        if track == None:
#            self._logger.debug("\'"+path+"\' is an invalid file.")
#            return None
#        trackID = None
#        if hasTrackID == True:
        mycompletion = lambda trackID: self._addTrackCompletion(path, track,
                                                                trackID)
        track.getID(mycompletion)
#        self.getTrackID(path, mycompletion)

    def _addTrack(self, path):
        self.queue(lambda thread, cursor: thread.doAddTrack(path))
            
    def doWalkDirectoryNoWatch(self, directory, callback):
        self._logger.debug("Finding files from \'"+directory+"\'.")
        contents = os.listdir(directory)
        for n in range(len(contents)):
            path = os.path.realpath(directory+'/'+contents[n])
            if os.path.isdir(path):
                self.walkDirectoryNoWatch(path, callback)
            else:
                callback(path)
    
    def walkDirectoryNoWatch(self, directory, callback):
        directory = os.path.realpath(directory)
        self.queue(lambda thread, cursor:
                   thread.doWalkDirectoryNoWatch(directory, callback))
        
    def addDirectoryNoWatch(self, directory):
        mycallback = lambda path: self._addTrack(path)
        self.walkDirectoryNoWatch(directory, mycallback)
        
    def _getDirectoryIDCompletion(self, directory, directoryID, completion):
        self._logger.debug("Retrieving directory ID for \'"+directory+"\'.")
        if directoryID == None:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
        completion(directoryID)
        
    def doGetDirectoryID(self, directory, completion):
        mycompletion = lambda directoryID:\
            self._getDirectoryIDCompletion(directory, directoryID, completion)
        self._asyncExecuteAndFetchOneOrNull(
            "select directoryid from directories where path = ?", (directory, ),
            mycompletion, priority=2)
        
    def getDirectoryID(self, directory, completion):
        directory = os.path.realpath(directory)
        self.queue(lambda thread, cursor:
                   thread.doGetDirectoryID(directory, completion))
        
    def maybeAddToWatch(self, directory, directoryID):
        if directoryID == None:
            mycompletion = lambda result: self._logger.info(
                "\'"+directory+"\' has been added to the watch list.")
            self._asyncExecute("insert into directories (path) values (?)",
                               (directory, ), mycompletion, priority=2)
        else:
            self._logger.debug("\'"+directory\
                               +"\' is already in the watch list.")
    
    def doWalkDirectory(self, directory, callback):
        self._logger.debug("Adding \'"+directory+"\' to the watch list.")
        mycompletion = lambda directoryID: self.maybeAddToWatch(directory,
                                                                directoryID)
        self.getDirectoryID(directory, mycompletion)
        self.walkDirectoryNoWatch(directory, callback)
        
    def walkDirectory(self, directory, callback):
        directory = os.path.realpath(directory)
        self.queue(lambda thread, cursor: thread.doWalkDirectory(directory,
                                                                 callback))
        
    def addDirectory(self, directory):
        mycallback = lambda path: self._addTrack(path)
        self.walkDirectory(directory, mycallback)
        
    def _rescanDirectoriesCompletion(self, paths):
        for (directory, ) in paths:
            self.addDirectoryNoWatch(directory)
        
    def doRescanDirectories(self):
        self._logger.info("Rescanning the watch list for new files.")
        try:
            mycompletion = lambda paths:\
                self._rescanDirectoriesCompletion(paths)
            self._asyncExecuteAndFetchAll("select path from directories", (),
                                          mycompletion, priority=2)
        except NoResultError: # FIXME: does this work?
            self._logger.info("The watch list is empty.")
    
    def rescanDirectories(self):
        self.queue(lambda thread, cursor:
                   thread.doRescanDirectories())
        
    def maybeUpdateTrackDetails(self, track):
        self._updateTrackDetails(track)
        
    def _updateTrackDetailsCompletion(self, path, track, trackID):
        self._logger.debug("Updating \'"+path+"\' in the library.")
        if trackID != None:
            mycompletion = lambda result:\
                self._logger.info("\'"+path\
                                  +"\' has been updated in the library.")
            self._asyncExecute(
                """update tracks set path = ?, artist = ?, album = ?, title = ?,
                   tracknumber = ?, length = ?, bpm = ? where trackid = ?""",
                (path, track.getArtist(), track.getAlbum(), track.getTitle(),
                 track.getTrackNumber(), track.getLength(), track.getBPM(),
                 trackID), mycompletion, priority=2)
        else:
            self._logger.debug("\'"+path+"\' is not in the library.")

    def _updateTrackDetails(self, track):
        path = track.getPath()
        mycompletion = lambda trackID:\
            self._updateTrackDetailsCompletion(path, track, trackID)
        track.getID(mycompletion)
#        self.getTrackID(path, mycompletion)
            
    def _setHistoricalCompletion(self, historical):
        if historical == 1:
            self._logger.debug("Making track non-current.")
        elif historical == 0:
            self._logger.debug("Making track non-current.")
            
    def setHistorical(self, historical, trackID):
        if historical == True:
            historical = 1
        elif historical == False:
            historical = 0
        mycompletion = lambda result: self._setHistoricalCompletion(historical)
        self._asyncExecute("update tracks set historical = ? where trackID = ?",
                           (historical, trackID), mycompletion, priority=2)

class DatabaseThread(Thread):
    def __init__(self, db, path):
        Thread.__init__(self, db, path, "Database")
        
    def complete(self, completion, priority=1):
        self.queue(lambda thread, cursor: completion(), priority)
            
    def doExecute(self, cursor, stmt, args, completion):
        cursor.execute(stmt, args)
        completion(None)

    def execute(self, stmt, args, completion, priority=1):
        self.queue(lambda thread, cursor:
                   thread.doExecute(cursor, stmt, args, completion), priority)

    def doExecuteAndFetchOne(self, cursor, stmt, args, completion, trace):
        cursor.execute(stmt, args)
        result = cursor.fetchone()
        if result is None:
            wx.PostEvent(self._db, ExceptionEvent(NoResultError, trace))
            return
        completion(result[0])

    def executeAndFetchOne(self, stmt, args, completion, priority=1):
        trace = traceback.extract_stack()
        self.queue(lambda thread, cursor:
                   thread.doExecuteAndFetchOne(cursor, stmt, args, completion,
                                               trace), priority)
        
    def doExecuteAndFetchLastRowID(self, cursor, stmt, args, completion, trace):
        cursor.execute(stmt, args)
        result = cursor.lastrowid
        if result is None:
            wx.PostEvent(self._db, ExceptionEvent(NoResultError, trace))
            return
        completion(result)

    def executeAndFetchLastRowID(self, stmt, args, completion, priority=1):
        trace = traceback.extract_stack()
        self.queue(lambda thread, cursor:
                   thread.doExecuteAndFetchLastRowID(cursor, stmt, args,
                                                     completion, trace),
                   priority)
        
    def doExecuteAndFetchOneOrNull(self, cursor, stmt, args, completion):
        cursor.execute(stmt, args)
        result = cursor.fetchone()
        if result is None:
            completion(None)
        completion(result[0])

    def executeAndFetchOneOrNull(self, stmt, args, completion, priority=1):
        self.queue(lambda thread, cursor:
                   thread.doExecuteAndFetchOneOrNull(cursor, stmt, args,
                                                     completion), priority)

    def doExecuteAndFetchAll(self, cursor, stmt, args, completion, trace):
        cursor.execute(stmt, args)
        result = cursor.fetchall()
        if result is None:
            wx.PostEvent(self._db, ExceptionEvent(NoResultError, trace))
            return
        completion(result)

    def executeAndFetchAll(self, stmt, args, completion, priority=1):
        trace = traceback.extract_stack()
        self.queue(lambda thread, cursor:
                   thread.doExecuteAndFetchAll(cursor, stmt, args, completion,
                                               trace), priority)

ID_EVT_DATABASE = wx.NewId()

def EVT_DATABASE(handler, func):
    handler.Connect(-1, -1, ID_EVT_DATABASE, func)

class DatabaseEvent(wx.PyEvent):
    def __init__(self, result, completion):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_DATABASE)
        self._result = result
        self._completion = completion
        
    def complete(self):
        self._completion(self._result)
        
ID_EVT_EXCEPTION = wx.NewId()

def EVT_EXCEPTION(handler, func):
    handler.Connect(-1, -1, ID_EVT_EXCEPTION, func)

class ExceptionEvent(wx.PyEvent):
    def __init__(self, err, trace):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_EXCEPTION)
        self._err = err(trace=trace)
        
    def getException(self):
        return self._err

class Database(EventHandler):
    def __init__(self, trackFactory, loggerFactory, configParser,
                 debugMode=False, databasePath="database",
                 defaultDefaultScore=10):
        EventHandler.__init__(self, DatabaseThread(self, databasePath))
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
        
        self._dbThread.start()
        
        self._directoryWalkThread = DirectoryWalkThread(
            self, self._databasePath, self._logger, self._trackFactory,
            self._dbThread)
        self._directoryWalkThread.start()

    def async(self, stmt, args, completion):
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchOne(stmt, args, completion)

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

    def _executeAndFetchOneOrNull(self, stmt, args=()):
        self._cursor.execute(stmt, args)
        result = self._cursor.fetchone()
        if result is None:
            return None
        return result[0]

    def _executeAndFetchOne(self, stmt, args=()):
        result = self._executeAndFetchOneOrNull(stmt, args)
        if result is None:
            raise NoResultError()
        return result

    def asyncAddTrack(self, path=None, hasTrackID=True, track=None,
                      completion=None):
        mycompletion = lambda: \
            self._addTrackCompletion(path, hasTrackID, track, completion)
        mycompletion2 = lambda result: \
            wx.PostEvent(self, DatabaseEvent(result, mycompletion))
        self._dbThread.complete(mycompletion2)
        
    def _addTrackCompletion(self, path=None, hasTrackID=True, track=None,
                            completion=None):
        if path == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
            path = track.getPath()
        path = os.path.realpath(path)
        self._logger.debug("Adding \'"+path+"\' to the library.")
        if track == None:
            try:
                track = self._trackFactory.getTrackFromPathNoID(self, path)
            except NoTrackError:
                track = None
        if track == None:
            self._logger.debug("\'"+path+"\' is an invalid file.")
            return None
        c = self._conn.cursor()
        trackID = None
        if hasTrackID == True:
            mycompletion = lambda result: self._setTrackIDCompletion(track,
                                                                     result,
                                                                     completion)
            self._asyncGetTrackID(track, mycompletion)
        elif hasTrackID == False:
            mycompletion = lambda result: \
                self._setTrackIDCompletion(track, result, completion,
                                           wasAdded=True)
            self._asyncExecuteAndFetchLastRowID(
                """insert into tracks (path, artist, album, title, tracknumber,
                   unscored, length, bpm, historical) values (?, ?, ?, ?, ?, 1,
                   ?, ?, 0)""", (path, track.getArtist(), track.getAlbum(),
                                 track.getTitle(), track.getTrackNumber(),
                                 track.getLength(), track.getBPM()),
                mycompletion)

    def _setTrackIDCompletion(self, track, trackID, completion, wasAdded=False):
        path = track.getPath()
        if trackID == None:
            mycompletion = lambda result: \
                self._setTrackIDCompletion(track, result, completion,
                                           wasAdded=True)
            self._asyncExecuteAndFetchLastRowID(
                """insert into tracks (path, artist, album, title, tracknumber,
                   unscored, length, bpm, historical) values (?, ?, ?, ?, ?, 1,
                   ?, ?, 0)""", (path, track.getArtist(), track.getAlbum(),
                                 track.getTitle(), track.getTrackNumber(),
                                 track.getLength(), track.getBPM()),
                mycompletion)
            return
        if wasAdded == True:
            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self._logger.debug("\'"+path+"\' is already in the library.")
        track.setID(self._trackFactory, trackID)
        if completion == None:
            return
        completion(trackID)

    def addTrack(self, path=None, hasTrackID=True, track=None):
        if path == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
            path = track.getPath()
        path = os.path.realpath(path)
        self._logger.debug("Adding \'"+path+"\' to the library.")
        if track == None:
            try:
                track = self._trackFactory.getTrackFromPathNoID(self, path)
            except NoTrackError:
                track = None
        if track == None:
            self._logger.debug("\'"+path+"\' is an invalid file.")
            return None
        c = self._conn.cursor()
        trackID = None
        if hasTrackID == True:
            trackID = self._getTrackID(track)
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
    def asyncGetAllTrackIDs(self, completion):
        self._logger.debug("Retrieving all track IDs.")
        self._asyncExecuteAndFetchAll("select trackid from tracks", (),
                                      completion)
    
    ## FIXME: not working yet, poss works for one tag
    def asyncGetAllTrackIDsWithTags(self, completion, tags):
        self._logger.debug("Retrieving all track IDs with tags: "+str(tags)+".")
        self._cursor.execute(
            """select trackid from tracks left outer join
               (select trackid from tags left outer join tagnames using (tagid)
                on tagnames.tagid = tags.tagid, tagnames.name in ?) on
                tags.trackid = tracks.trackid""", tags)
        completion(self._cursor.fetchall())

    def _getTrackID(self, track):#, update=False):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        result = self._executeAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ))
        if result == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
#            if update == True:
#                raise NoTrackError
        return result

    def getTrackID(self, track):#, update=False):
        trackID = self._getTrackID(track)#, update)
        if trackID == None:
            return self.addTrack(hasTrackID=False, track=track)
        return trackID
    
    def asyncGetTrackID(self, track, completion):
        mycompletion = lambda trackID: self._getTrackIDCompletion(track,
                                                                  trackID,
                                                                  completion)
        self._asyncGetTrackID(track, mycompletion)
        
    def _asyncGetTrackID(self, track, completion):
        path = track.getPath()
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._asyncExecuteAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ), mycompletion)
        
    def _getTrackIDCompletion(self, track, trackID, completion):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        if trackID == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
            self.asyncAddTrack(path=path, hasTrackID=False, track=track,
                               completion=completion)
            return
        completion(trackID)

    def addDirectory(self, directory):
        directory = os.path.realpath(directory)
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
        
    def asyncAddDirectory(self, directory):
        self._directoryWalkThread.addDirectory(directory)
        
    def asyncGetDirectoryID(self, directory, completion):
        directory = os.path.realpath(directory)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._asyncExecuteAndFetchOneOrNull(
            "select directoryid from directories where path = ?", (directory, ),
            mycompletion)

    def getDirectoryID(self, directory):
        directory = os.path.realpath(directory)
        self._logger.debug("Retrieving directory ID for \'"+directory+"\'.")
        result = self._executeAndFetchOneOrNull(
            "select directoryid from directories where path = ?", (directory, ))
        if result == None:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
        return result
    
    def asyncAddDirectoryNoWatch(self, directory):
        self._directoryWalkThread.addDirectoryNoWatch(directory)

    def addDirectoryNoWatch(self, directory):
        directory = os.path.realpath(directory)
        self._logger.debug("Adding files in \'"+directory+"\' to the library.")
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = os.path.realpath(directory+'/'+contents[n])
            if os.path.isdir(path):
                self.addDirectoryNoWatch(path)
            else: ## or: elif contents[n][-4:]=='.mp3':
                self.addTrack(path)

    def removeDirectory(self, directory):
        directory = os.path.realpath(directory)
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

    def asyncRescanDirectories(self):
        self._directoryWalkThread.rescanDirectories()

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
        result = self._executeAndFetchOneOrNull(
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
        firstResult = self._executeAndFetchOneOrNull(
            "select linkid from links where secondtrackid = ?", (trackID, ))
        secondResult = self._executeAndFetchOneOrNull(
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
        result = self._executeAndFetchOneOrNull(
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
        return self._executeAndFetchOneOrNull(
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
        result = self._executeAndFetchOneOrNull(
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
    def asyncGetOldestLastPlayed(self, completion):
        try:
            self._asyncExecuteAndFetchOne(
                """select strftime('%s', 'now') - strftime('%s', min(datetime))
                   from (select max(playid) as id, trackid from plays,
                         (select trackid as historicalid from tracks where
                          historical = 0) as historicaltracks where
                         plays.trackid = historicaltracks.historicalid group by
                         trackid) as maxplays, plays where maxplays.id =
                   plays.playid""", (), completion)
        except NoResultError:
            completion(0)

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
        trackID = self._getTrackID(track)#, update=True)
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
        details = self._getTrackDetails(track=track)#, update=True)
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

    def _getTrackDetails(self, track=None, trackID=None):#, update=False):
        (self._pathIndex, self._artistIndex, self._albumIndex, self._titleIndex,
         self._trackNumberIndex, self._unscoredIndex, self._lengthIndex,
         self._bpmIndex, self._historicalIndex) = range(9)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
            trackID = track.getID()#update)
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
        c = self._conn.cursor()
        if historical == True:
            self._logger.debug("Making track non-current.")
            historical = 1
        elif historical == False:
            self._logger.debug("Making track current.")
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
        return self._executeAndFetchOne(
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
            tagNames.append(self._executeAndFetchOne(
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
        c.execute("update tracks set unscored = 1 where trackid = ?",
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
        return self._executeAndFetchOneOrNull(
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
        path = os.path.realpath(path)
        return self._executeAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ))

    def getIDFromPath(self, path):
        id = self.maybeGetIDFromPath(path)
        if id is None:
            raise PathNotFoundError()

    def getNumberOfTracks(self):
        return self._executeAndFetchOne("select count(*) from tracks")

    # FIXME(ben): create indexes on tracks(trackid) and plays(trackid)
    # or this is slow!
    def getNumberOfUnplayedTracks(self):
        return self._executeAndFetchOne(
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
        self._configParser.set("Database", name, str(value))

    def _loadSettings(self):
        try:
            ## FIXME: poss should be main setting?
            defaultScore = self._configParser.getint("Database", "defaultScore")
            self._settings["defaultScore"] = defaultScore
        except ConfigParser.NoOptionError:
            self._settings["defaultScore"] = self._defaultDefaultScore
