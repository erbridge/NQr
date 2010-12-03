## Database Control
##
## TODO: use a hash as a track identifier instead of path to allow for path
##       changes.
## TODO: add a function to remove the last play record (to undo the play)?
## TODO: add functions to populate ignore list
## TODO: check if track table already exists first to confirm whether or not
##       to create other tables (poss corruption)
## TODO: finish asyncing track links
##
## FIXME: make tracebacks work properly for all completions

import ConfigParser
#from collections import deque
import datetime
from Errors import *
import os
import Queue
import sqlite3
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
        self._eventCount = 0
        
    def queue(self, thing, trace, priority=1):
        self._eventCount += 1
        self._queue.put((priority, self._eventCount, thing, trace))

    def run(self):
        conn = sqlite3.connect(self._databasePath)
        cursor = conn.cursor()
        while True:
            got = self._queue.get()
            got[2](self, cursor, got[3])
            
    def _raise(self, err, errcompletion=None):
        try:
            errcompletion(err)
        except:
            wx.PostEvent(self._db, ExceptionEvent(err))
            
class DatabaseEventHandler(wx.EvtHandler):
    def __init__(self, dbThread, priority):
        wx.EvtHandler.__init__(self)
        self._dbThread = dbThread
        self._priority = priority
        
        EVT_DATABASE(self, self._onDatabaseEvent)
        EVT_EXCEPTION(self, self._onExceptionEvent)
        
    def _onDatabaseEvent(self, e):
        self._logger.debug("Got event.")
        e.complete()
        
    def _onExceptionEvent(self, e):
        raise e.getException()

    def complete(self, completion, priority=None, trace=[]):
        if priority == None:
            priority = self._priority
        trace = extractTraceStack(trace)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.complete(mycompletion, priority, trace=trace)
        
    def _execute(self, stmt, args, completion, priority=None, trace=[]):
        if priority == None:
            priority = self._priority
        trace = extractTraceStack(trace)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.execute(stmt, args, mycompletion, priority, trace=trace)
    
    def _executeAndFetchOne(self, stmt, args, completion, priority=None,
                            returnTuple=False, trace=[], errcompletion=None):
        if priority == None:
            priority = self._priority
        trace = extractTraceStack(trace)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchOne(stmt, args, mycompletion, priority,
                                          returnTuple, trace=trace,
                                          errcompletion=errcompletion)
        
    def _executeAndFetchOneOrNull(self, stmt, args, completion, priority=None,
                                  returnTuple=False, trace=[]):
        if priority == None:
            priority = self._priority
        trace = extractTraceStack(trace)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchOneOrNull(stmt, args, mycompletion,
                                                priority, returnTuple,
                                                trace=trace)
        
    def _executeAndFetchAll(self, stmt, args, completion, priority=None,
                            throwException=True, trace=[], errcompletion=None):
        if priority == None:
            priority = self._priority
        trace = extractTraceStack(trace)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchAll(stmt, args, mycompletion, priority,
                                          throwException, trace=trace,
                                          errcompletion=errcompletion)
        
    def _executeAndFetchLastRowID(self, stmt, args, completion, priority=None,
                                  trace=[]):
        if priority == None:
            priority = self._priority
        trace = extractTraceStack(trace)
        mycompletion = lambda result: wx.PostEvent(self,
                                                   DatabaseEvent(result,
                                                                 completion))
        self._dbThread.executeAndFetchLastRowID(stmt, args, mycompletion,
                                                priority, trace=trace)
        
    def _getTrackID(self, track, completion):
        path = track.getPath()
        self._executeAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ), completion)
        
    def getTrackID(self, track, completion):
        mycompletion = lambda trackID: self._getTrackIDCompletion(track,
                                                                  trackID,
                                                                  completion)
        self._getTrackID(track, mycompletion)
        
    def _getDirectoryIDCompletion(self, directory, directoryID, completion):
        self._logger.debug("Retrieving directory ID for \'"+directory+"\'.")
        if directoryID == None:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
        completion(directoryID)
        
    def _getDirectoryID(self, directory, completion):
        directory = os.path.realpath(directory)
        mycompletion = lambda directoryID:\
            self._getDirectoryIDCompletion(directory, directoryID, completion)
        self._executeAndFetchOneOrNull(
            "select directoryid from directories where path = ?", (directory, ),
            mycompletion)
        
    def _updateTrackDetailsCompletion(self, track, trackID, infoLogging=True):
        path = track.getPath()
        self._logger.debug("Updating \'"+path+"\' in the library.")
        if trackID != None:
            if infoLogging == True:
                mycompletion = lambda result: self._logger.info(
                    "\'"+path+"\' has been updated in the library.")
            else:
                mycompletion = lambda result: self._logger.debug(
                    "\'"+path+"\' has been updated in the library.")
            self._execute(
                """update tracks set path = ?, artist = ?, album = ?, title = ?,
                   tracknumber = ?, length = ?, bpm = ? where trackid = ?""",
                (path, track.getArtist(), track.getAlbum(), track.getTitle(),
                 track.getTrackNumber(), track.getLength(), track.getBPM(),
                 trackID), mycompletion)
        else:
            self._logger.debug("\'"+path+"\' is not in the library.")
            
    def _updateTrackDetails(self, track, infoLogging=True):
        mycompletion = lambda trackID:\
            self._updateTrackDetailsCompletion(track, trackID, infoLogging)
        self._getTrackID(track, mycompletion)
            
    def setHistorical(self, historical, trackID):
        if historical == True:
            mycompletion = lambda result:\
                self._logger.debug("Making track non-current.")
            historical = 1
        elif historical == False:
            mycompletion = lambda result:\
                self._logger.debug("Making track current.")
            historical = 0
        self._execute("update tracks set historical = ? where trackID = ?",
                           (historical, trackID), mycompletion)
        
# FIXME: should somehow indicate that it is working/finished without spamming
class DirectoryWalkThread(Thread, DatabaseEventHandler):
    def __init__(self, db, path, logger, trackFactory, dbThread):
        DatabaseEventHandler.__init__(self, dbThread, 2)
        Thread.__init__(self, db, path, "Directory Walk")
        self._logger = logger
        self._trackFactory = trackFactory
        
    def _getTrackIDCompletion(self, track, trackID, completion):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        if trackID == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
        track.setID(self._trackFactory, trackID)
        completion(trackID)
        
    def _addTrackCompletion(self, path, track, trackID):
        self._logger.debug("Adding \'"+path+"\' to the library.")
#        if hasTrackID == False or trackID == None:
        if trackID == None:
            mycompletion = lambda result:\
                self._logger.info("\'"+path+"\' has been added to the library.")
            self._execute("""insert into tracks (path, artist, album,
                                  title, tracknumber, unscored, length, bpm,
                                  historical) values
                                  (?, ?, ?, ?, ?, 1, ?, ?, 0)""",
                               (path, track.getArtist(), track.getAlbum(),
                                track.getTitle(), track.getTrackNumber(),
                                track.getLength(), track.getBPM()),
                               mycompletion)
#            trackID = cursor.lastrowid
#            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self._logger.debug("\'"+path+"\' is already in the library.")
        track.setID(self._trackFactory, trackID)
#        return trackID
        
    def doAddTrack(self, path, trace):
        try:
            track = self._trackFactory.getTrackFromPathNoID(self, path,
                                                            useCache=False)
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

    def _addTrack(self, path, trace=[]):
        trace = extractTraceStack(trace)
        self.queue(
            lambda thread, cursor, traceBack: thread.doAddTrack(path,
                                                                traceBack),
            trace)
            
    def doWalkDirectoryNoWatch(self, directory, callback, trace):
        self._logger.debug("Finding files from \'"+directory+"\'.")
        contents = os.listdir(directory)
        for n in range(len(contents)):
            path = os.path.realpath(directory+'/'+contents[n])
            if os.path.isdir(path):
                self.walkDirectoryNoWatch(path, callback)
            else:
                callback(path)
    
    def walkDirectoryNoWatch(self, directory, callback, trace=[]):
        directory = os.path.realpath(directory)
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doWalkDirectoryNoWatch(directory, callback,
                                                 traceBack), trace)
        
    def addDirectoryNoWatch(self, directory):
        mycallback = lambda path: self._addTrack(path)
        self.walkDirectoryNoWatch(directory, mycallback)
        
    def doGetDirectoryID(self, directory, completion, trace):
        self._getDirectoryID(directory, completion)
    
    def getDirectoryID(self, directory, completion, trace=[]):
        directory = os.path.realpath(directory)
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doGetDirectoryID(directory, completion, traceBack),
                   trace)
        
    def maybeAddToWatch(self, directory, directoryID):
        if directoryID == None:
            mycompletion = lambda result: self._logger.info(
                "\'"+directory+"\' has been added to the watch list.")
            self._execute("insert into directories (path) values (?)",
                               (directory, ), mycompletion)
        else:
            self._logger.debug("\'"+directory\
                               +"\' is already in the watch list.")
    
    def doWalkDirectory(self, directory, callback, trace):
        self._logger.debug("Adding \'"+directory+"\' to the watch list.")
        mycompletion = lambda directoryID: self.maybeAddToWatch(directory,
                                                                directoryID)
        self.getDirectoryID(directory, mycompletion)
        self.walkDirectoryNoWatch(directory, callback)
        
    def walkDirectory(self, directory, callback, trace=[]):
        directory = os.path.realpath(directory)
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doWalkDirectory(directory, callback, traceBack),
                   trace)
        
    def addDirectory(self, directory):
        mycallback = lambda path: self._addTrack(path)
        self.walkDirectory(directory, mycallback)
        
    def _rescanDirectoriesCompletion(self, paths):
        for (directory, ) in paths:
            self.addDirectoryNoWatch(directory)
        
    def doRescanDirectories(self, trace):
        self._logger.info("Rescanning the watch list for new files.")
        errcompletion = ErrorCompletion(
            NoResultError, lambda: self._logger.info("The watch list is empty."))
        mycompletion = lambda paths: self._rescanDirectoriesCompletion(paths)
        self._executeAndFetchAll("select path from directories", (),
                                 mycompletion, errcompletion=errcompletion)
#        except NoResultError: # FIXME: does this work?
#            self._logger.info("The watch list is empty.")
    
    def rescanDirectories(self, trace=[]):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doRescanDirectories(traceBack), trace)

    def maybeUpdateTrackDetails(self, track):
        self._updateTrackDetails(track, infoLogging=False)

class DatabaseThread(Thread):
    def __init__(self, db, path):
        Thread.__init__(self, db, path, "Database")
        
    def doComplete(self, completion, trace):
        completion(None)
        
    def complete(self, completion, priority=1, trace=[]):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   self.doComplete(completion, traceBack), trace, priority)
            
    def doExecute(self, cursor, stmt, args, completion, trace):
        cursor.execute(stmt, args)
        completion(None)

    def execute(self, stmt, args, completion, priority=1, trace=[]):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doExecute(cursor, stmt, args, completion, traceBack),
                   trace, priority)

    def doExecuteAndFetchOne(self, cursor, stmt, args, completion, trace,
                             returnTuple=False, errcompletion=None):
        cursor.execute(stmt, args)
        result = cursor.fetchone()
        if result is None:
            err = NoResultError(trace=trace)
            self._raise(err, errcompletion)
            return
        if returnTuple == True:
            completion(result)
            return
        completion(result[0])

    def executeAndFetchOne(self, stmt, args, completion, priority=1,
                           returnTuple=False, trace=[], errcompletion=None):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doExecuteAndFetchOne(cursor, stmt, args, completion,
                                               traceBack, returnTuple,
                                               errcompletion), trace, priority)
        
    def doExecuteAndFetchLastRowID(self, cursor, stmt, args, completion, trace,
                                   errcompletion=None):
        cursor.execute(stmt, args)
        result = cursor.lastrowid
        if result is None:
            err = NoResultError(trace=trace)
            self._raise(err, errcompletion)
            return
        completion(result)

    def executeAndFetchLastRowID(self, stmt, args, completion, priority=1,
                                 trace=[], errcompletion=None):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doExecuteAndFetchLastRowID(cursor, stmt, args,
                                                     completion, traceBack,
                                                     errcompletion),
                   trace, priority)
        
    def doExecuteAndFetchOneOrNull(self, cursor, stmt, args, completion, trace,
                                   returnTuple=False):
        cursor.execute(stmt, args)
        result = cursor.fetchone()
        if result is None:
            completion(None)
            return
        if returnTuple == True:
            completion(result)
            return
        completion(result[0])

    def executeAndFetchOneOrNull(self, stmt, args, completion, priority=1,
                                 returnTuple=False, trace=[]):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doExecuteAndFetchOneOrNull(cursor, stmt, args,
                                                     completion, traceBack,
                                                     returnTuple), trace,
                   priority)

    def doExecuteAndFetchAll(self, cursor, stmt, args, completion, trace,
                             throwException=True, errcompletion=None):
        cursor.execute(stmt, args)
        result = cursor.fetchall()
        if result is None and throwException is True:
            err = NoResultError(trace=trace)
            self._raise(err, errcompletion)
            return
        completion(result)

    def executeAndFetchAll(self, stmt, args, completion, priority=1,
                           throwException=True, trace=[], errcompletion=None):
        trace = extractTraceStack(trace)
        self.queue(lambda thread, cursor, traceBack:
                   thread.doExecuteAndFetchAll(cursor, stmt, args, completion,
                                               traceBack, throwException,
                                               errcompletion),
                   trace,
                   priority)

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
    def __init__(self, err):
        wx.PyEvent.__init__(self)
        self.SetEventType(ID_EVT_EXCEPTION)
        self._err = err
        
    def getException(self):
        return self._err

class Database(DatabaseEventHandler):
    def __init__(self, trackFactory, loggerFactory, configParser,
                 debugMode=False, databasePath="database",
                 defaultDefaultScore=10):
        DatabaseEventHandler.__init__(self, DatabaseThread(self, databasePath), 1)
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
        
    def _setTrackIDCompletion(self, track, trackID, completion, wasAdded=False):
        path = track.getPath()
        if trackID == None:
            mycompletion = lambda result: \
                self._setTrackIDCompletion(track, result, completion,
                                           wasAdded=True)
            self._executeAndFetchLastRowID(
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
        if hasTrackID == True:
            mycompletion = lambda result: self._setTrackIDCompletion(track,
                                                                     result,
                                                                     completion)
            self._getTrackID(track, mycompletion)
        elif hasTrackID == False:
            mycompletion = lambda result: \
                self._setTrackIDCompletion(track, result, completion,
                                           wasAdded=True)
            self._executeAndFetchLastRowID(
                """insert into tracks (path, artist, album, title, tracknumber,
                   unscored, length, bpm, historical) values (?, ?, ?, ?, ?, 1,
                   ?, ?, 0)""", (path, track.getArtist(), track.getAlbum(),
                                 track.getTitle(), track.getTrackNumber(),
                                 track.getLength(), track.getBPM()),
                mycompletion)

    # FIXME: make clearer?
    def addTrack(self, path=None, hasTrackID=True, track=None,
                      completion=None):
        mycompletion = lambda result: \
            self._addTrackCompletion(path, hasTrackID, track, completion)
        self.complete(mycompletion)

    ## returns a list of tuples of the form (trackID, )
    ## FIXME: make faster by doing something like: select
    ## tracks.trackid, score, plays.datetime from tracks left outer
    ## join scores using (trackid) left outer join plays using
    ## (trackid); with some select trackid, max(datetime) from plays
    ## group by trackid; thrown in.
    def getAllTrackIDs(self, completion):
        self._logger.debug("Retrieving all track IDs.")
        self._executeAndFetchAll("select trackid from tracks", (),
                                      completion)
    
    ## FIXME: not working yet, poss works for one tag
    def getAllTrackIDsWithTags(self, completion, tags):
        self._logger.debug("Retrieving all track IDs with tags: "+str(tags)+".")
        self._cursor.execute(
            """select trackid from tracks left outer join
               (select trackid from tags left outer join tagnames using (tagid)
                on tagnames.tagid = tags.tagid, tagnames.name in ?) on
                tags.trackid = tracks.trackid""", tags)
        completion(self._cursor.fetchall())

#    def _getTrackID(self, track):#, update=False):
#        path = track.getPath()
#        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
#        result = self._executeAndFetchOneOrNull(
#            "select trackid from tracks where path = ?", (path, ))
#        if result == None:
#            self._logger.debug("\'"+path+"\' is not in the library.")
##            if update == True:
##                raise NoTrackError
#        return result
        
    def _getTrackIDCompletion(self, track, trackID, completion):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        if trackID == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
            self.addTrack(path=path, hasTrackID=False, track=track,
                          completion=completion)
            return
        completion(trackID)
        
    def getDirectoryID(self, directory, completion):
        self._getDirectoryID(directory, completion)
        
    def addDirectory(self, directory):
        self._directoryWalkThread.addDirectory(directory)
    
    def addDirectoryNoWatch(self, directory):
        self._directoryWalkThread.addDirectoryNoWatch(directory)
                
    def _removeDirectoryCompletion(self, directory, directoryID):
        directory = os.path.realpath(directory)
        self._logger.debug("Removing \'"+directory+"\' from the watch list.")
        if directoryID != None:
            mycompletion = lambda result: self._logger.info(
                "\'"+directory+"\' has been removed from the watch list.")
            self._execute("delete from directories where path = ?",
                               (directory, ), mycompletion)
            
        else:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")
                
    def removeDirectory(self, directory):
        mycompletion = lambda directoryID:\
            self._removeDirectoryCompletion(directory, directoryID)
        self.getDirectoryID(directory, mycompletion)

    def rescanDirectories(self):
        self._directoryWalkThread.rescanDirectories()
        
    def _getTrackPathsCompletion(self, firstTrackID, secondTrackID, linkID,
                                 completion):
        multicompletion = MultiCompletion(
            2, lambda firstPath, secondPath: completion(firstTrackID, firstPath,
                                                        secondTrackID,
                                                        secondPath, linkID))
        self.getPathFromIDNoDebug(
            firstTrackID, lambda firstPath: multicompletion.put(0, firstPath))
        self.getPathFromIDNoDebug(
            secondTrackID, lambda secondPath: multicompletion.put(0,
                                                                  secondPath))
        
    def _addLinkCompletion(self, firstTrackID, firstTrackPath, secondTrackID, 
                           secondTrackPath, linkID):
        if linkID == None:
            mycompletion = lambda result: self._logger.info(
                "\'"+firstTrackPath+"\' has been linked to \'"+secondTrackPath\
                +"\'.")
            self._execute(
                "insert into links (firsttrackid, secondtrackid) values (?, ?)",
                (firstTrackID, secondTrackID), mycompletion)
        else:
            self._logger.debug("\'"+firstTrackPath+"\' is already linked to \'"\
                               +secondTrackPath+"\'.")
        
    ## FIXME: needs to deal with two links using the same first or second track
    def addLink(self, firstTrack, secondTrack):
        mycompletion = lambda firstTrackID, firstTrackPath, secondTrackID,\
            secondTrackPath, linkID: self._addLinkCompletion(firstTrackID,
                                                             firstTrackPath,
                                                             secondTrackID,
                                                             secondTrackPath,
                                                             linkID)
        self.getLinkID(
            firstTrack, secondTrack,
            lambda firstTrackID, secondTrackID, linkID:\
                self._getTrackPathsCompletion(firstTrackID, secondTrackID,
                                              linkID, mycompletion),
            completeTrackIDs=True)
        
    def _getLinkIDCompletion2(self, firstTrackID, secondTrackID, linkID,
                              completion, completeTrackIDs=False):
        self._logger.debug("Retrieving link ID.")
        if linkID == None:
            self._logger.debug("The tracks are not linked.")
        if completeTrackIDs == True:
            completion(firstTrackID, secondTrackID, linkID)
        else:
            completion(linkID)
            
    def _getLinkIDCompletion(self, firstTrackID, secondTrackID, completion,
                             completeTrackIDs=False):
        mycompletion = lambda linkID:\
            self._getLinkIDCompletion2(firstTrackID, secondTrackID, linkID,
                                       completion, completeTrackIDs)
        self._executeAndFetchOneOrNull(
            """select linkid from links where firsttrackid = ? and
               secondtrackid = ?""", (firstTrackID, secondTrackID),
            mycompletion)
        
    def getLinkID(self, firstTrack, secondTrack, completion,
                  completeTrackIDs=False):
        multicompletion = MultiCompletion(
            2, lambda firstTrackID, secondTrackID:\
            self._getLinkIDCompletion(firstTrackID, secondTrackID, completion,
                                      completeTrackIDs))
        firstTrack.getID(lambda firstTrackID:\
                         multicompletion.put(0, firstTrackID))
        secondTrack.getID(lambda secondTrackID:\
                          multicompletion.put(1, secondTrackID))
    
#    def _returnTracksCompletion(self, callback):
#        for track in self._trackQueue:
#            callback(track)
#            
#    def _addToTrackQueueCallback(self, trackID, appendLeft=False):
#        track = self._trackFactory.getTrackFromID(self, trackID)
#        if appendLeft == True:
#            self._trackQueue.appendleft(track)
#        else:
#            self._trackQueue.append(track)
#            
#    def _getEarlierTracksCompletion(self, linkIDs, oldLinkIDs):
#        while True:
#            for linkID in linkIDs:
#                if linkID not in oldLinkIDs:
#                    (newTrackID,
#                     trackID) = self._db.getLinkedTrackIDs(linkID)
#                    track = self._trackFactory.getTrackFromID(
#                        self._db, newTrackID)
#                    self._trackQueue.appendleft(track)
#                    oldLinkIDs = linkIDs
#                    linkIDs = self._db.getLinkIDs(track)
#            if oldLinkIDs == linkIDs:
#                break
#    
#    def _getLinksCompletion3(self, linkIDs, oldLinkIDs, firstTrack,
#                             firstLinkIDs, secondTrack, secondLinkIDs,
#                             callback):
#        self._trackQueue = deque([firstTrack, secondTrack])
#        ## finds earlier tracks
#        while True:
#            for linkID in firstLinkIDs:
#                if linkID not in oldLinkIDs:
#                    (newTrackID,
#                     trackID) = self._db.getLinkedTrackIDs(linkID)
#                    track = self._trackFactory.getTrackFromID(
#                        self._db, newTrackID)
#                    self._trackQueue.appendleft(track)
#                    oldLinkIDs = firstLinkIDs
#                    firstLinkIDs = self._db.getLinkIDs(track)
#            if oldLinkIDs == firstLinkIDs:
#                break
#        self.complete(
#            lambda result: self._returnTracksCompletion(callback))
#    
#    def _getLinksCompletion2(self, linkIDs, oldLinkIDs, trackIDs, callback):
#        firstTrack = self._trackFactory.getTrackFromID(self, trackIDs[0])
#        secondTrack = self._trackFactory.getTrackFromID(self, trackIDs[1])
#        multicompletion = MultiCompletion(
#            2, lambda firstLinkIDs, secondLinkIDs: self._getLinksCompletion3(
#                linkIDs, oldLinkIDs, firstTrack, firstLinkIDs, secondTrack,
#                secondLinkIDs, callback))
#        self.getLinkIDs(
#            firstTrack, lambda firstLinkIDs: multicompletion.put(0,
#                                                                 firstLinkIDs))
#        self.getLinkIDs(
#            secondTrack, lambda secondLinkIDs: multicompletion.put(
#                                1, secondLinkIDs))
#        
#    def _getLinksCompletion(self, track, linkIDs, callback):
#        if linkIDs == (None, None):
#            callback(track)
#            return
#        elif linkIDs[0] != None:
#            linkID = linkIDs[0]
#        else:
#            linkID = linkIDs[1]
#        self.getLinkedTrackIDs(
#            linkID, lambda trackIDs: self._getLinksCompletion2(linkIDs, linkID,
#                                                               trackIDs,
#                                                               callback))
#    
#    def getLinks(self, track, callback):
#        self.getLinkIDs(
#            track, lambda linkIDs: self._getLinksCompletion(track, linkIDs,
#                                                            callback))
        
    def _getLinkIDsCompletion2(self, trackID, firstLinkID, secondLinkID,
                               completion):
        self._logger.debug("Retrieving link IDs.")
        if firstLinkID == None and secondLinkID == None:
            self.getPathFromIDNoDebug(
                trackID, lambda path: self._logger.debug(
                    "\'"+path+"\' is not linked to another track."))
        completion(firstLinkID, secondLinkID)
        
    def _getLinkIDsCompletion(self, trackID, completion):
        multicompletion = MultiCompletion(
            2, lambda firstLinkID, secondLinkID:\
            self._getLinkIDsCompletion2(trackID, firstLinkID, secondLinkID,
                                        completion))
        self._executeAndFetchOneOrNull(
            "select linkid from links where secondtrackid = ?", (trackID, ),
            lambda firstLinkID: multicompletion.put(0, firstLinkID))
        self._executeAndFetchOneOrNull(
            "select linkid from links where firsttrackid = ?", (trackID, ),
            lambda secondLinkID: multicompletion.put(1, secondLinkID))

        
    ## if there are two links for a track, returns the link with track as second
    ## track first for queueing ease
    def getLinkIDs(self, track, completion):
        track.getID(lambda trackID: self._getLinkIDsCompletion(trackID,
                                                               completion))

    def _getLinkedTrackIDsCompletion(self, trackIDs, completion):
        self._logger.debug("Retrieving track IDs for linked tracks.")
        if trackIDs == None:
            self._logger.debug("No such link exists.")
        completion(trackIDs)
            
    def getLinkedTrackIDs(self, linkID, completion):
        mycompletion = lambda trackIDs:\
            self._getLinkedTrackIDsCompletion(trackIDs, completion)
        self._executeAndFetchOneOrNull(
            "select firsttrackid, secondtrackid from links where linkid = ?",
            (linkID, ), mycompletion, returnTuple=True)
        

    def _removeLinkCompletion(self, firstTrack, secondTrack, linkID):
        self._logger.debug("Removing link.")
        firstTrackPath = firstTrack.getPath()
        secondTrackPath = secondTrack.getPath()
        if linkID != None:
            mycompletion = lambda result:\
                self._logger.info(
                    "\'"+firstTrackPath+"\' is no longer linked to \'"\
                    +secondTrackPath+"\'.")
            self._execute("delete from links where linkid = ?", (linkID, ),
                          mycompletion)
        else:
            self._logger.debug("\'"+firstTrackPath+"\' is not linked to \'"\
                               +secondTrackPath+"\'.")
            
    def removeLink(self, firstTrack, secondTrack):
        mycompletion = lambda linkID: self._removeLinkCompletion(firstTrack,
                                                                 secondTrack,
                                                                 linkID)
        self.getLinkID(firstTrack, secondTrack, mycompletion)
        
#    def asyncAddEnqueue(self, track):
#        track.getID(lambda trackID: self._addEnqueueCompletion(trackID))
#    
#    def _addEnqueueCompletion(self, trackID):
#        self._execute("""insert into enqueues (trackid, datetime) values
#                              (?, datetime('now'))""", (trackID, ),
#                           lambda result: self._logger.debug("Adding enqueue."))
#
#    def addEnqueue(self, track):
#        self._logger.debug("Adding enqueue.")
#        c = self._conn.cursor()
#        trackID = track.getID()
#        c.execute("""insert into enqueues (trackid, datetime) values
#                     (?, datetime('now'))""", (trackID, ))
#        c.close()
#        self._conn.commit()
#
#    def getSecondsSinceLastEnqueuedFromID(self, trackID):
#        if trackID == None:
#            self._logger.error("No track has been identified.")
#            raise NoTrackError
#        return self._executeAndFetchOneOrNull(
#            """select strftime('%s', 'now') - strftime('%s', datetime)
#               from enqueues where trackid = ? order by enqueueid desc""",
#            (trackID, ))

    def _addPlayCompletion(self, track, trackID, msDelay=0):
        self._logger.debug("Adding play.")
        now = datetime.datetime.now()
        delay = datetime.timedelta(0, 0, 0, msDelay)
        playTime = now - delay
        self.getLastPlayedInSeconds(
            track, lambda previousPlay: track.setPreviousPlay(previousPlay))
        self._execute("""insert into plays (trackid, datetime) values
                              (?, datetime(?))""", (trackID, playTime),
                           lambda result: doNothing())
        
    def addPlay(self, track, msDelay=0):
        mycompletion = lambda trackID: self._addPlayCompletion(track, trackID,
                                                               msDelay)
        track.getID(mycompletion)
        
    def _getLastPlayedTrackIDCompletion(self, trackID, completion,
                                        errcompletion):
        if trackID != None:
            completion(trackID)
        else:
            self._logger.error("No plays recorded.")
            errcompletion(EmptyDatabaseError)
             
    def getLastPlayedTrackID(self, completion, errcompletion):
        mycompletion = lambda trackID:\
            self._getLastPlayedTrackIDCompletion(trackID, completion,
                                                 errcompletion)
        self._executeAndFetchOneOrNull(
            "select trackid from plays order by playid desc", (), mycompletion)
        
    def _getLastPlayedCompletion2(self, trackID, playDetails, completion):
        if playDetails == None and self._debugMode == True:
            self.getPathFromIDNoDebug(
                trackID, lambda path: self._logger.debug(
                    "\'"+path+"\' has never been played."))
        completion(playDetails)
        
    def _getLastPlayedCompletion(self, trackID, completion):
        (self._basicLastPlayedIndex, self._localLastPlayedIndex,
         self._secondsSinceLastPlayedIndex,
         self._lastPlayedInSecondsIndex) = range(4)
        mycompletion = lambda playDetails:\
            self._getLastPlayedCompletion2(trackID, playDetails, completion)
        self._executeAndFetchOneOrNull(
            """select datetime, datetime(datetime, 'localtime'),
               strftime('%s', 'now') - strftime('%s', datetime),
               strftime('%s', datetime) from plays where trackid = ? order by
               playid desc""", (trackID, ), mycompletion, returnTuple=True)

    def _getLastPlayed(self, completion, track=None, trackID=None):
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError # FIXME: probably broken
            mycompletion = lambda newTrackID:\
                self._getLastPlayedCompletion(newTrackID, completion)
            track.getID(mycompletion)
            return
        self._getLastPlayedCompletion(trackID, completion)

        
    def getLastPlayed(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._basicLastPlayedIndex,
                                      completion,
                                      "Retrieving time of last play.")
        self._getLastPlayed(mycompletion, track=track)
    
    def getLastPlayedLocalTime(self, track, completion):
        mycompletion = lambda details: self._getDetailCompletion(
            details, self._localLastPlayedIndex, completion,
            "Retrieving time of last play in localtime.")
        self._getLastPlayed(mycompletion, track=track)
        
#    def _getLastPlayedInSecondsCompletion(self, lastPlayed, completion):
#        if lastPlayed != None:
#            lastPlayed = int(lastPlayed)
#        completion(lastPlayed)
            
    def getLastPlayedInSeconds(self, track, completion):
        mycompletion = lambda details: self._getDetailCompletion(
            details, self._lastPlayedInSecondsIndex,
            lambda lastPlayed: completion(lastPlayed))
        self._getLastPlayed(mycompletion, track=track)
    
    def getSecondsSinceLastPlayedFromID(self, trackID, completion):
        if self._debugMode == True:
            debugMessage = "Calculating time since last played."
        else:
            debugMessage = None
        mycompletion = lambda details: self._getDetailCompletion(
            details, self._secondsSinceLastPlayedIndex, completion,
            debugMessage)
        self._getLastPlayed(mycompletion, trackID=trackID)

    # FIXME: as soon as a file is deleted or moved, so it can't get
    # played again, this will get stuck. We need to keep track of
    # whether entries are current or historical. Partially fixed: 
    # currently bad tracks rely on being chosen by randomizer to update 
    # historical status.
    def getOldestLastPlayed(self, completion):
        errcompletion = ErrorCompletion(NoResultError, lambda: completion(0))
        self._executeAndFetchOne(
            """select strftime('%s', 'now') - strftime('%s', min(datetime))
               from (select max(playid) as id, trackid from plays,
                     (select trackid as historicalid from tracks where
                      historical = 0) as historicaltracks where
                     plays.trackid = historicaltracks.historicalid group by
                     trackid) as maxplays, plays where maxplays.id =
               plays.playid""", (), completion, errcompletion=errcompletion)

    def _getPlayCountCompletion(self, plays, completion):
        if plays == None:
            completion(0)
            return
        completion(len(plays))
        
    def getPlayCount(self, completion, track=None, trackID=None):
        self._logger.debug("Retrieving play count.")
        mycompletion = lambda plays:\
            self._getPlayCountCompletion(plays, completion)
        mycompletion2 = lambda trackID: self._executeAndFetchAll(
            "select datetime from plays where trackid = ? order by playid desc",
            (trackID, ), mycompletion)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError # FIXME: probably broken
            trackID = track.getID(mycompletion2)
            return
        mycompletion2(trackID)
    
#    def updateAllTrackDetails(self):
#        trackIDs = self.getAllTrackIDs()
#        for trackID in trackIDs:
#            try:
#                track = self._trackFactory.getTrackFromID()
#                self.maybeUpdateTrackDetails(track)
#            except NoTrackError:
#                self.setHistorical(True, trackID)

    def _getTrackDetails(self, completion, track=None, trackID=None):
        self._numberIndices = 9
        (self._pathIndex, self._artistIndex, self._albumIndex, self._titleIndex,
         self._trackNumberIndex, self._unscoredIndex, self._lengthIndex,
         self._bpmIndex, self._historicalIndex) = range(self._numberIndices)
        mycompletion = lambda trackID: self._executeAndFetchOne(
            """select path, artist, album, title, tracknumber, unscored, length,
               bpm, historical from tracks where trackid = ?""", (trackID, ),
            completion, returnTuple=True)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError
            track.getID(mycompletion)
        else:
            mycompletion(trackID)
        
    def _getTrackDetailsChangeCompletion(self, track, details, completion):
        self._logger.debug("Checking whether track details have changed.")
        newDetails = {}
        newDetails[self._pathIndex] = track.getPath()
        newDetails[self._artistIndex] = track.getArtist()
        newDetails[self._albumIndex] = track.getAlbum()
        newDetails[self._titleIndex] = track.getTitle()
        newDetails[self._trackNumberIndex] = track.getTrackNumber()
        newDetails[self._lengthIndex] = track.getLength()
        newDetails[self._bpmIndex] = track.getBPM()
        for n in range(self._numberIndices):
            try:
                if details[n] != newDetails[n]:
                    completion(True)
                    return
            except KeyError:
                continue
        completion(False)
    
    def _getTrackDetailsChange(self, track, completion):
        mycompletion = lambda details:\
            self._getTrackDetailsChangeCompletion(track, details, completion)
        self._getTrackDetails(mycompletion, track=track)
        
    def _maybeUpdateTrackDetailsCompletion(self, track, change):
        if change == True:
            self._updateTrackDetails(track)
            
    def maybeUpdateTrackDetails(self, track):
        mycompletion = lambda change:\
            self._maybeUpdateTrackDetailsCompletion(track, change)
        self._getTrackDetailsChange(track, mycompletion)
            
    def _getPathCompletion(self, path, completion):
        self._logger.debug("Retrieving track's path.")
        completion(path)
    
    def getPath(self, track, completion):
        mycompletion = lambda path: self._getPathCompletion(path, completion)
        self.getPathNoDebug(track, mycompletion)
        
    def _getDetailCompletion(self, details, index, completion,
                             debugMessage=None):
        if debugMessage != None:
            self._logger.debug(debugMessage)
        if details == None:
            completion(None)
            return
        completion(details[index])
    
    def getPathNoDebug(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._pathIndex, completion)
        self._getTrackDetails(mycompletion, track=track)
            
    def _getPathFromIDCompletion(self, path, completion):
        self._logger.debug("Retrieving track's path.")
        completion(path)
            
    def getPathFromID(self, trackID, completion):
        mycompletion = lambda path: self._getPathFromIDCompletion(path,
                                                                  completion)
        self.getPathFromIDNoDebug(trackID, mycompletion)
    
    def getPathFromIDNoDebug(self, trackID, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._pathIndex, completion)
        self._getTrackDetails(mycompletion, trackID=trackID)
    
    def getArtist(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._artistIndex, completion,
                                      debugMessage="Retrieving track's artist.")
        self._getTrackDetails(mycompletion, track=track)
    
    def getAlbum(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._albumIndex, completion,
                                      debugMessage="Retrieving track's album.")
        self._getTrackDetails(mycompletion, track=track)
    
    def getTitle(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._titleIndex, completion,
                                      debugMessage="Retrieving track's title.")
        self._getTrackDetails(mycompletion, track=track)
    
    def getTrackNumber(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(details, self._trackNumberIndex,
                                      completion,
                                      debugMessage="Retrieving track's number.")
        self._getTrackDetails(mycompletion, track=track)

    def _getBPMCompletion(self, track, details, completion):
        self._logger.debug("Retrieving track's bpm.")
        if details == None:
            completion(None)
            return
        bpm = details[self._bpmIndex]
        if bpm == None:
            bpm = track.getBPM()
            self.setBPM(bpm, track)
        completion(bpm)
    
    def getBPM(self, track, completion):
        mycompletion = lambda details:\
            self._getBPMCompletion(track, details, completion)
        self._getTrackDetails(mycompletion, track=track)    
            
    def _setBPMCompletion(self, bpm, trackID):
        mycompletion = lambda result: self._logger.debug("Adding bpm to track.")
        self._execute("update tracks set bpm = ? where trackID = ?",
                           (bpm, trackID), mycompletion)
    
    def setBPM(self, bpm, track):
        mycompletion = lambda trackID: self._setBPMCompletion(bpm, trackID)
        track.getID(mycompletion)
    
    def getHistorical(self, track, completion):
        mycompletion = lambda details:\
            self._getDetailCompletion(
                details, self._historicalIndex, completion,
                debugMessage="Retrieving track's currency.")
        self._getTrackDetails(mycompletion, track=track)
    
    def _getLengthCompletion(self, track, details, completion):
        self._logger.debug("Retrieving track's length.")
        if details == None:
            completion(None)
            return
        length = details[self._lengthIndex]
        if length == None:
            length = track.getLength()
            self.setLength(length, track)
        completion(length)
        
    def getLength(self, track, completion):
        mycompletion = lambda details:\
            self._getLengthCompletion(track, details, completion)
        self._getTrackDetails(mycompletion, track=track)
        

    
    def getLengthString(self, track, completion):
        mycompletion = lambda rawLength: completion(formatLength(rawLength))
        self.getLength(track, mycompletion)
        
    def _setLengthCompletion(self, length, trackID):
        mycompletion = lambda result:\
            self._logger.debug("Adding length to track.")
        self._execute("update tracks set length = ? where trackID = ?",
                           (length, trackID), mycompletion)
        
    def setLength(self, length, track):
        mycompletion = lambda trackID: self._setLengthCompletion(length, trackID)
        track.getID(mycompletion)
        
    def addTagName(self, tagName):
        mycompletion = lambda result: self._logger.debug("Adding tag name.")
        self._execute("insert into tagnames (name) values (?)",
                           (tagName, ), mycompletion)
        
    def _getAllTagNamesCompletion(self, names, completion):
        self._logger.debug("Retrieving all tag names.")
        if names == None:
            completion([])
            return
        tagNames = []
        for (name, ) in names:
            tagNames.append(name)
        completion(tagNames)#
            
    def getAllTagNames(self, completion):
        mycompletion = lambda names: self._getAllTagNamesCompletion(names,
                                                                    completion)
        self._executeAndFetchAll("select name from tagnames", (),
                                      mycompletion)
        
    def getTagNameID(self, tagName, completion):
        self._executeAndFetchOne(
            "select tagnameid from tagnames where name = ?", (tagName, ),
            completion)
            
    def _setTagCompletion(self, trackID, tagName, tagNameID, tagNames):
        if tagName not in tagNames:
            mycompletion = lambda result:\
                self._logger.info("Tagging track with '"+tagName+"'.")
            self._execute("""insert into tags (trackid, tagnameid) values
                                  (?, ?)""", (trackID, tagNameID), mycompletion)
            
    def setTag(self, track, tagName):
        multicompletion =\
            MultiCompletion(3, lambda trackID, tagNames, tagNameID:\
                            self._setTagCompletion(trackID, tagName, tagNameID,
                                                   tagNames))
        track.getID(lambda trackID: multicompletion.put(0, trackID))
        self.getTags(track, lambda tagNames: multicompletion.put(1,
                                                                      tagNames))
        self.getTagNameID(tagName,
                               lambda tagNameID: multicompletion.put(2,
                                                                     tagNameID))
        
    def _unsetTagCompletion(self, trackID, tagNameID):
        self._execute("""delete from tags where tagnameid = ? and
                              trackid = ?""", (tagNameID, trackID),
                           lambda result: doNothing())
        
    def unsetTag(self, track, tagName):
        multicompletion =\
            MultiCompletion(2, lambda trackID, tagNameID:\
                            self._unsetTagCompletion(trackID, tagNameID))
        track.getID(lambda trackID: multicompletion.put(0, trackID))
        self.getTagNameID(tagName,
                               lambda tagNameID: multicompletion.put(1,
                                                                     tagNameID))
        
    def _getTagNameListCompletion(self, completion):
        completion(self._tagNames)
        
    def getTagNameFromID(self, tagNameID, completion):
        self._executeAndFetchOne(
            "select name from tagnames where tagnameid = ?", (tagNameID, ),
            completion)
        
    def _getTagsFromTrackIDCompletion(self, tagNameIDs, completion):
        self._logger.debug("Retrieving track tags.")
        if tagNameIDs == None:
            completion([])
            return
        self._tagNames = []
        for (tagNameID, ) in tagNameIDs:
            mycompletion = lambda tagName: self._tagNames.append(tagName)
            self.getTagNameFromID(tagNameID, mycompletion)
        self.complete(
            lambda result: self._getTagNameListCompletion(completion))
    
    def getTagsFromTrackID(self, trackID, completion):
        mycompletion = lambda tagNameIDs:\
            self._getTagsFromTrackIDCompletion(tagNameIDs, completion)
        self._executeAndFetchAll(
            "select tagnameid from tags where trackid = ?", (trackID, ),
            mycompletion, throwException=False)
        
    def getTags(self, track, completion):
        mycompletion = lambda trackID: self.getTagsFromTrackID(trackID,
                                                                    completion)
        track.getID(mycompletion)
        
    def _getIsScoredCompletion(self, unscored, completion):
        if unscored == None:
            completion(None)
        elif unscored == 1:
            completion(False)
        elif unscored == 0:
            completion(True)

    ## determines whether user has changed score for this track
    def _getIsScored(self, completion, track=None, trackID=None):
        if self._debugMode == True:
            debugMessage = "Retrieving track's unscored status."
        else:
            debugMessage = None
        mycompletion = lambda details: self._getDetailCompletion(
            details, self._unscoredIndex,
            lambda unscored: self._getIsScoredCompletion(unscored, completion),
            debugMessage=debugMessage)
        if trackID != None:
            self._getTrackDetails(mycompletion, trackID=trackID)
        else:
            self._getTrackDetails(mycompletion, track=track)

    def getIsScored(self, track, completion):
        self._getIsScored(completion, track=track)

    def getIsScoredFromID(self, trackID, completion):
        self._getIsScored(completion, trackID=trackID)
    
    ## poss should add a record to scores table
    def setUnscored(self, track):
        track.getID(
            lambda trackID: self._execute(
                "update tracks set unscored = 1 where trackid = ?", (trackID, ),
                lambda result: self._logger.debug(
                    "Setting track as unscored.")))
        
    def _setScoreCompletion(self, trackID, score):
        self._execute("update tracks set unscored = 0 where trackid = ?",
                           (trackID, ), lambda result: doNothing())
        self._execute("""insert into scores (trackid, score, datetime)
                              values (?, ?, datetime('now'))""",
                           (trackID, score), lambda result: self._logger.debug(
                                                "Setting track's score."))
        
    ## poss add track if track not in library
    def setScore(self, track, score):
        track.getID(lambda trackID: self._setScoreCompletion(trackID, score))
        
    def _internalGetScoreCompletion(self, score, completion):
        self._logger.debug("Retrieving track's score.")
        completion(score)
        
    def _getScore(self, completion, track=None, trackID=None):
        mycompletion = lambda trackID: self._executeAndFetchOneOrNull(
            "select score from scores where trackid = ? order by scoreid desc",
            (trackID, ),
            lambda score: self._internalGetScoreCompletion(score, completion))
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError # FIXME: probably doesn't work
            trackID = track.getID(mycompletion)
            return
        mycompletion(trackID)
    
    def _getScoreCompletion(self, isScored, completion, completeWithDash=False,
                            track=None, trackID=None):
        if isScored == False:
            if completeWithDash == True:
                completion("-")
            else:
                completion(self._defaultScore)
        else:
            self._getScore(completion, track=track, trackID=trackID)
            
    def getScore(self, track, completion):
        self.getIsScored(
            track, lambda isScored: self._getScoreCompletion(
                        isScored, completion, completeWithDash=True,
                        track=track))
    
    def getScoreValue(self, track, completion):
        self.getIsScored(
            track, lambda isScored: self._getScoreCompletion(isScored,
                                                             completion,
                                                             track=track))
    
    def getScoreValueFromID(self, trackID, completion):
        self.getIsScoredFromID(
            trackID, lambda isScored: self._getScoreCompletion(isScored,
                                                               completion,
                                                               trackID=trackID))

    def maybeGetIDFromPath(self, path, completion):
        path = os.path.realpath(path)
        self._executeAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ), completion)

#    def getIDFromPath(self, path):
#        id = self.maybeGetIDFromPath(path)
#        if id is None:
#            raise PathNotFoundError()

    def getNumberOfTracks(self, completion):
        self._executeAndFetchOne("select count(*) from tracks", (),
                                      completion)
    
    # FIXME(ben): create indexes on tracks(trackid) and plays(trackid)
    # or this is slow!
    def getNumberOfUnplayedTracks(self, completion):
        self._executeAndFetchOne(
            """select count(*) from tracks left outer join plays using(trackid)
               where plays.trackid is null""", (), completion)
        
    # returns an array of [ score, count ]
    def getScoreTotals(self, completion):
        self._executeAndFetchAll(
            """select score, count(score)
               from (select max(scoreid), x.trackid, score
                     from scores, (select distinct trackid from scores) as x
                     where scores.trackid = x.trackid group by scores.trackid)
               group by score;""", (), completion)

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
