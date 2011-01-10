## Database Control
##
## TODO: use a hash as a track identifier instead of path to allow for path
##       changes - maybe use path as backup reference?
## TODO: add a function to remove the last play record (to undo the play)?
## TODO: add functions to populate ignore list - poss now unnecessary
## TODO: check if track table already exists first to confirm whether or not
##       to create other tables (poss corruption)
## TODO: finish asyncing track links
##
## FIXME: make tracks that were historical which are added again non-historical

import ConfigParser
import datetime
from Errors import NoResultError, EmptyQueueError, NoTrackError,\
    EmptyDatabaseError
import Events
import os.path
import sqlite3
import time
from Util import MultiCompletion, ErrorCompletion, doNothing, formatLength,\
    BasePrefsPage, validateNumeric, EventPoster, BaseThread, getTrace, wx

class Thread(BaseThread):
    def __init__(self, db, path, name, logger, errcallback, lock,
                 mainThread=None, raiseEmpty=False):
        BaseThread.__init__(self, db, name, logger, errcallback, lock,
                            raiseEmpty=raiseEmpty)
        self._mainThread = mainThread
        self._path = path

    def _run(self):
        # FIXME: set isolation_level arg
        self._conn = sqlite3.connect(self._path)
        self._cursor = self._conn.cursor()

    def _queueCallback(self, completion):
        completion(self._cursor)
        self._commit()

    def _abort(self):
        self._commit()
        self._cursor.close()
        self._conn.close()
        if self._mainThread and self._abortMainThread:
            self._mainThread.abort()
            
    def _commit(self):
        try:
            self._conn.commit()
        except sqlite3.OperationalError as err:
            if str(err) != "disk I/O error":
                raise err
            self.postErrorLog("Got a disk I/O error. Retrying commit.")
            time.sleep(.01)
            self._commit()
        
class DatabaseEventHandler(wx.EvtHandler, EventPoster):
    def __init__(self, db, dbThread, logger, threadLock, priority, eventLogger):
        wx.EvtHandler.__init__(self)
        EventPoster.__init__(self, db, logger, threadLock)
        self._dbThread = dbThread
        self._priority = priority
        self._eventLogger = eventLogger
        
        Events.EVT_DATABASE(self, self._onDatabaseEvent)
        Events.EVT_EXCEPTION(self, self._onExceptionEvent)
        
    def _onDatabaseEvent(self, e):
        self.postDebugLog("Got event.")
        e.complete()
        self._eventLogger("Database Complete", e)
        
    def _onExceptionEvent(self, e):
        self._eventLogger("Database Exception", e)
        raise e.getException()
    
    def _completionEvent(self, completion, returnData=True):
        if returnData == False:
            return lambda thisCallback, completion=completion:\
                self._completionEventCompletion(completion, thisCallback,
                                                returnData=False)
        return lambda thisCallback, result, completion=completion:\
            self._completionEventCompletion(completion, thisCallback,
                                            result=result)

    def _completionEventCompletion(self, completion, traceCallback,
                                   result=None, returnData=True):
        if returnData == False:
            self.postEvent(
                Events.DatabaseEvent(completion, traceCallback,
                                     returnData=False))
        else:
            self.postEvent(
                Events.DatabaseEvent(completion, traceCallback,
                                     result=result))

    def complete(self, completion, priority=None, traceCallback=None):
        if priority == None:
            priority = self._priority
        self._dbThread.complete(
            self._completionEvent(completion, returnData=False), priority,
            traceCallback=traceCallback)
        
    def _execute(self, stmt, args, completion, priority=None,
                 traceCallback=None):
        if priority == None:
            priority = self._priority
        self._dbThread.execute(
            stmt, args, self._completionEvent(completion, returnData=False),
            priority, traceCallback=traceCallback)
    
    def _executeMany(self, stmts, args, completion, priority=None,
                     traceCallback=None):
        if priority == None:
            priority = self._priority
        self._dbThread.executeMany(
            stmts, args, self._completionEvent(completion, returnData=False),
            priority, traceCallback=traceCallback)
    
    def _executeAndFetchOne(self, stmt, args, completion, priority=None,
                            returnTuple=False, traceCallback=None,
                            errcompletion=None):
        if priority == None:
            priority = self._priority
        self._dbThread.executeAndFetchOne(
            stmt, args, self._completionEvent(completion), priority,
            returnTuple, traceCallback=traceCallback,
            errcompletion=errcompletion)
        
    def _executeAndFetchOneOrNull(self, stmt, args, completion, priority=None,
                                  returnTuple=False, traceCallback=None):
        if priority == None:
            priority = self._priority
        self._dbThread.executeAndFetchOneOrNull(
            stmt, args, self._completionEvent(completion), priority,
            returnTuple, traceCallback=traceCallback)
        
    def _executeAndFetchAll(self, stmt, args, completion, priority=None,
                            throwException=True, traceCallback=None,
                            errcompletion=None):
        if priority == None:
            priority = self._priority
        self._dbThread.executeAndFetchAll(
            stmt, args, self._completionEvent(completion), priority,
            throwException, traceCallback=traceCallback,
            errcompletion=errcompletion)
        
    def _executeAndFetchLastRowID(self, stmt, args, completion, priority=None,
                                  traceCallback=None, errcompletion=None):
        if priority == None:
            priority = self._priority
        self._dbThread.executeAndFetchLastRowID(
            stmt, args, self._completionEvent(completion), priority,
            traceCallback=traceCallback,
            errcompletion=errcompletion)
        
    def getTrackID(self, track, completion, priority=None,
                   traceCallback=None):
        mycompletion = lambda thisCallback, trackID, track=track,\
            completion=completion, priority=priority:\
                self._getTrackIDCompletion(track, trackID, completion,
                                           thisCallback, priority=priority)
        self._getTrackID(track, mycompletion, priority=priority,
                         traceCallback=traceCallback)

    def _getTrackID(self, track, completion, priority=None,
                    traceCallback=None):
        path = track.getPath()
        self._executeAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ), completion,
            priority=priority, traceCallback=traceCallback)

    def _getDirectoryID(self, directory, completion, traceCallback=None):
        directory = os.path.realpath(directory)
        mycompletion = lambda thisCallback, directoryID, directory=directory,\
            completion=completion: self._getDirectoryIDCompletion(directory,
                                                                  directoryID,
                                                                  completion,
                                                                  thisCallback)
        self._executeAndFetchOneOrNull(
            "select directoryid from directories where path = ?", (directory, ),
            mycompletion, traceCallback=traceCallback)
        
    def _getDirectoryIDCompletion(self, directory, directoryID, completion,
                                  traceCallback=None):
        self.postDebugLog("Retrieving directory ID for \'"+directory+"\'.")
        if directoryID == None:
            self.postDebugLog("\'"+directory+"\' is not in the watch list.")
        completion(traceCallback, directoryID)
            
    def _updateTrackDetails(self, track, infoLogging=True,
                            traceCallback=None):
        mycompletion = lambda thisCallback, trackID, track=track,\
            infoLogging=infoLogging: self._updateTrackDetailsCompletion(
                track, trackID, infoLogging, thisCallback)
        self._getTrackID(track, mycompletion,
                         traceCallback=traceCallback)

    def _updateTrackDetailsCompletion(self, track, trackID, infoLogging=True,
                                      traceCallback=None):
        path = track.getPath()
        self.postDebugLog("Updating \'"+path+"\' in the library.")
        if trackID != None:
            if infoLogging == True:
                mycompletion = lambda thisCallback, path=path:\
                    self._logger.info("\'"+path\
                                      +"\' has been updated in the library.")
            else:
                mycompletion = lambda thisCallback, path=path:\
                    self._logger.debug("\'"+path\
                                       +"\' has been updated in the library.")
            self._execute(
                """update tracks set path = ?, artist = ?, album = ?, title = ?,
                   tracknumber = ?, length = ?, bpm = ? where trackid = ?""",
                (path, track.getArtist(), track.getAlbum(), track.getTitle(),
                 track.getTrackNumber(), track.getLength(), track.getBPM(),
                 trackID), mycompletion,
                traceCallback=traceCallback)
        else:
            self.postDebugLog("\'"+path+"\' is not in the library.")
            
    def setHistorical(self, historical, trackID, traceCallback=None):
        if historical == True:
            mycompletion = lambda thisCallback: self._logger.debug(
                "Making track non-current.")
            historical = 1
        elif historical == False:
            mycompletion = lambda thisCallback: self._logger.debug(
                "Making track current.")
            historical = 0
        self._execute("update tracks set historical = ? where trackID = ?",
                      (historical, trackID), mycompletion,
                      traceCallback=traceCallback)
        
class DirectoryWalkThread(Thread, DatabaseEventHandler):
    def __init__(self, db, lock, path, logger, trackFactory, dbThread,
                 eventLogger):
        self._working = False
        self._errorCount = 0
        errcallback = ErrorCompletion(EmptyQueueError,
                                      lambda: self._onEmptyQueueError())
        Thread.__init__(self, db, path, "Directory Walk", logger,
                        lambda err: errcallback(err), lock, dbThread,
                        raiseEmpty=True)
        DatabaseEventHandler.__init__(self, db, dbThread, logger, lock, 3, 
                                      eventLogger)
        self._logger = logger
        self._trackFactory = trackFactory
        
    def _onEmptyQueueError(self):
        if self._working == True:
            self._working = False
            self.postInfoLog("Probably finished directory walk.")
        
    def getWorking(self):
        return self._working
        
    def _getTrackIDCompletion(self, track, trackID, completion, traceCallback,
                              priority=None):
        path = track.getPath()
        self.postDebugLog("Retrieving track ID for \'"+path+"\'.")
        if trackID == None:
            self.postDebugLog("\'"+path+"\' is not in the library.")
        track.setID(self._trackFactory, trackID, traceCallback=traceCallback)
        completion(traceCallback, trackID)

    def _addTrack(self, path, traceCallback=None):
        self.queue(
            lambda thisCallback, cursor, path=path: self._doAddTrack(
                path, thisCallback), traceCallback)
        
    def _doAddTrack(self, path, traceCallback):
        try:
            track = self._trackFactory.getTrackFromPathNoID(
                self, path, useCache=False, traceCallback=traceCallback)
        except NoTrackError:
#            track = None
            self.postDebugLog("\'"+path+"\' is an invalid file.")
            return
#        if track == None:
#            self._logger.debug("\'"+path+"\' is an invalid file.")
#            return None
#        trackID = None
#        if hasTrackID == True:
        mycompletion = lambda thisCallback, trackID, path=path, track=track:\
            self._doAddTrackCompletion(path, track, trackID, thisCallback)
        track.getID(mycompletion, traceCallback)

    def _doAddTrackCompletion(self, path, track, trackID, traceCallback):
        self.postDebugLog("Adding \'"+path+"\' to the library.")
#        if hasTrackID == False or trackID == None:
        if trackID == None:
            self._execute(
                """insert into tracks (path, artist, album, title, tracknumber,
                                       unscored, length, bpm, historical)
                   values (?, ?, ?, ?, ?, 1, ?, ?, 0)""",
                (path, track.getArtist(), track.getAlbum(), track.getTitle(),
                 track.getTrackNumber(), track.getLength(), track.getBPM()),
                lambda thisCallback, path=path: self._logger.info(
                    "\'"+path+"\' has been added to the library."),
                traceCallback=traceCallback)
#            trackID = cursor.lastrowid
#            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self.postDebugLog("\'"+path+"\' is already in the library.")
        track.setID(self._trackFactory, trackID, traceCallback=traceCallback)
#        return trackID

    def addDirectory(self, directory, traceCallback=None):
        mycallback = lambda thisCallback, path: self._addTrack(path,
                                                               thisCallback)
        self.walkDirectory(directory, mycallback, traceCallback=traceCallback)

    def walkDirectory(self, directory, callback, traceCallback=None):
        self._working = True
        directory = os.path.realpath(directory)
        self.queue(
            lambda thisCallback, cursor, directory=directory:\
                self.doWalkDirectory(directory, callback, thisCallback),
                    traceCallback=traceCallback)

    def doWalkDirectory(self, directory, callback, traceCallback):
        self.postDebugLog("Adding \'"+directory+"\' to the watch list.")
        mycompletion = lambda thisCallback, directoryID, directory=directory:\
            self.maybeAddToWatch(directory, directoryID, thisCallback)
        self.getDirectoryID(directory, mycompletion,
                            traceCallback=traceCallback)
        self.walkDirectoryNoWatch(directory, callback,
                                  traceCallback=traceCallback)

    def maybeAddToWatch(self, directory, directoryID, traceCallback=None):
        self._working = True
        if directoryID == None:
            mycompletion = lambda thisCallback, directory=directory:\
                self._logger.info("\'"+directory\
                                  +"\' has been added to the watch list.")
            self._execute("insert into directories (path) values (?)",
                          (directory, ), mycompletion,
                          traceCallback=traceCallback)
        else:
            self.postDebugLog("\'"+directory+"\' is already in the watch list.")

    def addDirectoryNoWatch(self, directory, traceCallback=None):
        mycallback = lambda thisCallback, path: self._addTrack(path,
                                                               thisCallback)
        self.walkDirectoryNoWatch(directory, mycallback,
                                  traceCallback=traceCallback)

    def walkDirectoryNoWatch(self, directory, callback, traceCallback=None):
        self._working = True
        directory = os.path.realpath(directory)
        self.queue(
            lambda thisCallback, cursor, directory=directory,\
                callback=callback: self.doWalkDirectoryNoWatch(
                    directory, callback, thisCallback), traceCallback)
            
    def doWalkDirectoryNoWatch(self, directory, callback, traceCallback):
        self.postDebugLog("Finding files from \'"+directory+"\'.")
        contents = os.listdir(directory)
        for n in range(len(contents)):
            path = os.path.realpath(directory+'/'+contents[n])
            if os.path.isdir(path):
                self.walkDirectoryNoWatch(path, callback, traceCallback)
            else:
                callback(traceCallback, path)
    
    def getDirectoryID(self, directory, completion, traceCallback=None):
        directory = os.path.realpath(directory)
        self.queue(
            lambda thisCallback, cursor, directory=directory,\
                completion=completion: self.doGetDirectoryID(
                    directory, completion, thisCallback), traceCallback)

    def doGetDirectoryID(self, directory, completion, traceCallback):
        self._getDirectoryID(directory, completion, traceCallback=traceCallback)

    def rescanDirectories(self, traceCallback=None):
        self.queue(
            lambda thisCallback, cursor: self.doRescanDirectories(thisCallback),
            traceCallback)
        
    def doRescanDirectories(self, traceCallback=None):
        self.postInfoLog("Rescanning the watch list for new files.")
        errcompletion = ErrorCompletion(
            NoResultError,
            lambda: self._logger.info("The watch list is empty."))
        mycompletion = lambda thisCallback, paths:\
            self._doRescanDirectoriesCompletion(paths, thisCallback)
        self._executeAndFetchAll("select path from directories", (),
                                 mycompletion, errcompletion=errcompletion,
                                 traceCallback=traceCallback)

    def _doRescanDirectoriesCompletion(self, paths, traceCallback):
        for (directory, ) in paths:
            self.addDirectoryNoWatch(directory, traceCallback=traceCallback)

    def maybeUpdateTrackDetails(self, track, traceCallback=None):
        self._updateTrackDetails(track, infoLogging=False,
                                 traceCallback=traceCallback)

class DatabaseThread(Thread):
    def __init__(self, db, lock, path, logger):
        Thread.__init__(self, db, path, "Database", logger, None, lock)
        
    def complete(self, completion, priority=2, traceCallback=None):
        self.queue(lambda thisCallback, cursor, completion=completion:\
                       completion(thisCallback), traceCallback, priority)

    def execute(self, stmt, args, completion, priority=2,
                traceCallback=None):
        self.queue(lambda thisCallback, cursor, stmt=stmt, args=args,\
                       completion=completion: self.doExecute(cursor, stmt, args,
                                                             completion,
                                                             thisCallback),
                   traceCallback, priority)

    def doExecute(self, cursor, stmt, args, completion, thisCallback):
        cursor.execute(stmt, args)
        completion(thisCallback)

    def executeMany(self, stmts, args, completion, priority=2,
                    traceCallback=None):
        self.queue(lambda thisCallback, cursor, stmts=stmts, args=args,\
                       completion=completion: self.doExecuteMany(
                           cursor, stmts, args, completion, thisCallback),
                   traceCallback, priority)

    def doExecuteMany(self, cursor, stmts, args, completion, thisCallback):
        for index in range(len(stmts)):
            cursor.execute(stmts[index], args[index])
        completion(thisCallback)

    def executeAndFetchOne(self, stmt, args, completion, priority=2,
                           returnTuple=False, traceCallback=None,
                           errcompletion=None):
        self.queue(lambda thisCallback, cursor, stmt=stmt, args=args,\
                       completion=completion, returnTuple=returnTuple,\
                       errcompletion=errcompletion: self.doExecuteAndFetchOne(
                           cursor, stmt, args, completion, thisCallback,
                           returnTuple, errcompletion), traceCallback,
                   priority)

    def doExecuteAndFetchOne(self, cursor, stmt, args, completion, thisCallback,
                             returnTuple=False, errcompletion=None):
        cursor.execute(stmt, args)
        result = cursor.fetchone()
        if result is None:
            err = NoResultError(trace=thisCallback.getTrace())
            self._raise(err, errcompletion)
            return
        if returnTuple == True:
            completion(thisCallback, result)
            return
        completion(thisCallback, result[0])

    def executeAndFetchLastRowID(self, stmt, args, completion, priority=2,
                                 traceCallback=None, errcompletion=None):
        self.queue(lambda thisCallback, cursor, stmt=stmt, args=args,\
                       completion=completion, errcompletion=errcompletion:\
                           self.doExecuteAndFetchLastRowID(cursor, stmt, args,
                                                           completion,
                                                           thisCallback,
                                                           errcompletion),
                   traceCallback, priority)

    def doExecuteAndFetchLastRowID(self, cursor, stmt, args, completion,
                                   thisCallback, errcompletion=None):
        cursor.execute(stmt, args)
        result = cursor.lastrowid
        if result is None:
            err = NoResultError(trace=thisCallback.getTrace())
            self._raise(err, errcompletion)
            return
        completion(thisCallback, result)

    def executeAndFetchOneOrNull(self, stmt, args, completion, priority=2,
                                 returnTuple=False, traceCallback=None):
        self.queue(lambda thisCallback, cursor, stmt=stmt, args=args,\
                       completion=completion, returnTuple=returnTuple:\
                           self.doExecuteAndFetchOneOrNull(cursor, stmt, args,
                                                           completion,
                                                           thisCallback,
                                                           returnTuple),
                   traceCallback, priority)

    def doExecuteAndFetchOneOrNull(self, cursor, stmt, args, completion,
                                   thisCallback, returnTuple=False):
        cursor.execute(stmt, args)
        result = cursor.fetchone()
        if result is None:
            completion(thisCallback, None)
            return
        if returnTuple == True:
            completion(thisCallback, result)
            return
        completion(thisCallback, result[0])

    def executeAndFetchAll(self, stmt, args, completion, priority=2,
                           throwException=True, traceCallback=None,
                           errcompletion=None):
        self.queue(lambda thisCallback, cursor, stmt=stmt, args=args,\
                       completion=completion, throwException=throwException,\
                       errcompletion=errcompletion: self.doExecuteAndFetchAll(
                           cursor, stmt, args, completion, thisCallback,
                           throwException, errcompletion), traceCallback,
                   priority)

    def doExecuteAndFetchAll(self, cursor, stmt, args, completion, thisCallback,
                             throwException=True, errcompletion=None):
        cursor.execute(stmt, args)
        result = cursor.fetchall()
        if result is None and throwException is True:
            err = NoResultError(trace=thisCallback.getTrace())
            self._raise(err, errcompletion)
            return
        completion(thisCallback, result)

class Database(DatabaseEventHandler):
    def __init__(self, threadLock, trackFactory, loggerFactory, configParser,
                 debugMode, databasePath, defaultDefaultScore, eventLogger):
        self._logger = loggerFactory.getLogger("NQr.Database", "debug")
        DatabaseEventHandler.__init__(
            self, self,
            DatabaseThread(self, threadLock, databasePath, self._logger),
            self._logger, threadLock, 2, eventLogger)
        self._db = self
        self._trackFactory = trackFactory
        self._configParser = configParser
        self._defaultDefaultScore = defaultDefaultScore
        self._ignoreNewTracks = False
        self._addingTracks = {}
        self.loadSettings()
        self._debugMode = debugMode
        self._logger.debug("Opening connection to database at \'"+databasePath\
                           +"\'.")
        conn = sqlite3.connect(databasePath) # FIXME: set isolation_level arg
        self._cursor = conn.cursor()
        self._initMaybeCreateTrackTable()
        self._initMaybeCreateDirectoryTable()
        self._initMaybeCreatePlaysTable()
        self._initMaybeCreateEnqueuesTable()
        self._initMaybeCreateScoresTable()
        self._initMaybeCreateLinksTable()
        self._initMaybeCreateIgnoreTable()
        self._initMaybeCreateTagNamesTable()
        self._initMaybeCreateTagsTable()
        self._initMaybeCreateTableIndices()
        conn.commit()
        self._cursor.close()
        conn.close()
        
        Events.EVT_LOG(self, self._onLogEvent)
        
        self._dbThread.start_()
        
        self._directoryWalkThread = DirectoryWalkThread(
            self, threadLock, databasePath, self._logger, self._trackFactory,
            self._dbThread, eventLogger)
        self._directoryWalkThread.start_()
        
    def _onLogEvent(self, e):
        e.doLog()
        self._eventLogger("Database Log", e)

    def _initMaybeCreateTrackTable(self):
        self._logger.debug("Looking for track table.")
        try:
            self._cursor.execute(
                """create table tracks (trackid integer primary key
                                        autoincrement, path text, artist text,
                                        album text, title text, tracknumber
                                        text, unscored integer, length real, bpm
                                        integer, historical integer, score
                                        integer, lastplayed datetime)""")
            self._logger.debug("Track table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tracks already exists":
                raise err
            self._logger.debug("Track table found.")
            self._cursor.execute("pragma table_info(tracks)")
            details = self._cursor.fetchall()
            columnNames = []
            for detail in details:
                columnNames.append(detail[1])
            if columnNames.count('length') == 0:
                self._logger.debug("Adding length column to track table.")
                self._cursor.execute(
                    "alter table tracks add column length real")
            if columnNames.count('bpm') == 0:
                self._logger.debug("Adding bpm column to track table.")
                self._cursor.execute(
                    "alter table tracks add column bpm integer")
            if columnNames.count('historical') == 0:
                self._logger.debug("Adding historical column to track table.")
                self._cursor.execute(
                    "alter table tracks add column historical integer")
                self._cursor.execute("update tracks set historical = 0")
            if columnNames.count('score') == 0:
                self._logger.debug("Adding score column to track table.")
                self._cursor.execute(
                    "alter table tracks add column score integer")
                self._cursor.execute(
                    """update tracks set
                       score = (select scores.score from scores where
                                scores.trackid = tracks.trackid order by
                                scores.scoreid desc limit 1)
                       where exists (select scores.score from scores where
                                     scores.trackid = tracks.trackid)""")
            if columnNames.count('lastplayed') == 0:
                self._logger.debug("Adding last played column to track table.")
                self._cursor.execute(
                    "alter table tracks add column lastplayed datetime")
                self._cursor.execute(
                    """update tracks set
                       lastplayed = (select plays.datetime from plays where
                                     plays.trackid = tracks.trackid order by
                                     plays.playid desc limit 1)
                       where exists (select plays.datetime from plays where
                                     plays.trackid = tracks.trackid)""")

    def _initMaybeCreateDirectoryTable(self):
        self._logger.debug("Looking for directory table.")
        try:
            self._cursor.execute(
                """create table directories (directoryid integer primary key
                                             autoincrement, path text)""")
            self._logger.debug("Directory table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table directories already exists":
                raise err
            self._logger.debug("Directory table found.")

    def _initMaybeCreatePlaysTable(self):
        self._logger.debug("Looking for play table.")
        try:
            self._cursor.execute(
                """create table plays (playid integer primary key autoincrement,
                                       trackid integer, datetime text)""")
            self._logger.debug("Play table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table plays already exists":
                raise err
            self._logger.debug("Play table found.")

    def _initMaybeCreateEnqueuesTable(self):
        self._logger.debug("Looking for enqueue table.")
        try:
            self._cursor.execute(
                """create table enqueues (enqueueid integer primary key
                                          autoincrement, trackid integer,
                                          datetime text)""")
            self._logger.debug("Enqueue table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table enqueues already exists":
                raise err
            self._logger.debug("Enqueue table found.")

    def _initMaybeCreateScoresTable(self):
        self._logger.debug("Looking for score table.")
        try:
            self._cursor.execute(
                """create table scores (scoreid integer primary key
                                        autoincrement, trackid integer, score
                                        integer, datetime text)""")
            self._logger.debug("Score table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table scores already exists":
                raise err
            self._logger.debug("Score table found.")

    def _initMaybeCreateLinksTable(self):
        self._logger.debug("Looking for track link table.")
        try:
            self._cursor.execute(
                """create table links (linkid integer primary key autoincrement,
                                       firsttrackid integer, secondtrackid
                                       integer)""")
            self._logger.debug("Track link table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table links already exists":
                raise err
            self._logger.debug("Track link table found.")
    
    # FIXME: poss unnecessary with historical
    def _initMaybeCreateIgnoreTable(self):
        self._logger.debug("Looking for ignore table.")
        try:
            self._cursor.execute(
                """create table ignore (ignoreid integer primary key
                                        autoincrement, trackid integer)""")
            self._logger.debug("Ignore table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table ignore already exists":
                raise err
            self._logger.debug("Ignore table found.")

    def _initMaybeCreateTagNamesTable(self):
        self._logger.debug("Looking for tag names table.")
        try:
            self._cursor.execute(
                """create table tagnames (tagnameid integer primary key, name
                                          text)""")
            self._logger.debug("Tag names table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tagnames already exists":
                raise err
            self._logger.debug("Tag names table found.")

    def _initMaybeCreateTagsTable(self):
        self._logger.debug("Looking for tags table.")
        try:
            self._cursor.execute(
                """create table tags (tagid integer primary key, tagnameid
                                      integer, trackid integer)""")
            self._logger.debug("Tags table created.")
        except sqlite3.OperationalError as err:
            if str(err) != "table tags already exists":
                raise err
            self._logger.debug("Tags table found.")
        
    def _initMaybeCreateTableIndices(self):
        # primary keys are already indexed
        self._logger.debug("Creating table indices")
        self._cursor.execute(
            "create unique index if not exists t0 on tracks(path)")
        self._cursor.execute(
            "create unique index if not exists d0 on directories(path)")
        self._cursor.execute("create index if not exists p0 on plays(trackid)")
        self._cursor.execute("create index if not exists s0 on scores(trackid)")
        self._cursor.execute(
            "create unique index if not exists s1 on scores(scoreid, trackid)")
        self._cursor.execute(
            "create unique index if not exists tn0 on tagnames(name)")
        self._cursor.execute(
            """create unique index if not exists tg0 on tags(tagnameid,
                                                             trackid)""")

    def setIgnoreNewTracks(self, status):
        self._ignoreNewTracks = status

    def addTrack(self, path=None, track=None, completion=None, priority=None,
                 traceCallback=None):
        if path == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError(trace=getTrace(traceCallback))
            path = track.getPath()
        else:
            path = os.path.realpath(path)
        self._logger.debug("Adding \'"+path+"\' to the library.")
        if track == None:
            try:
                track = self._trackFactory.getTrackFromPathNoID(
                    self, path, traceCallback=traceCallback)
            except NoTrackError:
                self._logger.debug("\'"+path+"\' is an invalid file.")
                completion(traceCallback, None)
        mycompletion = lambda thisCallback, trackID, track=track,\
            completion=completion, priority=priority:\
                self._maybeAddTrackCallback(track, trackID, completion,
                                            thisCallback, priority=priority)
        self._getTrackID(track, mycompletion, priority=priority,
                         traceCallback=traceCallback)
        
    def _maybeAddTrackCallback(self, track, trackID, completion,
                               traceCallback, wasAdded=False,
                               priority=None):
        path = track.getPath()
        if wasAdded == False and path in self._addingTracks:
            self._addingTracks[path].append((completion, traceCallback))
            return
        elif wasAdded == False:
            self._addingTracks[path] = [(completion, traceCallback)]
        if trackID == None and wasAdded == False:
            mycompletion = lambda thisCallback, id, track=track,\
                completion=completion: self._maybeAddTrackCallback(
                    track, id, completion, thisCallback, wasAdded=True)
            self._executeAndFetchLastRowID(
                """insert into tracks (path, artist, album, title, tracknumber,
                   unscored, length, bpm, historical) values (?, ?, ?, ?, ?, 1,
                   ?, ?, 0)""", (path, track.getArtist(), track.getAlbum(),
                                 track.getTitle(), track.getTrackNumber(),
                                 track.getLength(), track.getBPM()),
                mycompletion, priority=priority,
                traceCallback=traceCallback)
            return
        if wasAdded == True:
            self._logger.info("\'"+path+"\' has been added to the library.")
        else:
            self._logger.debug("\'"+path+"\' is already in the library.")
        track.setID(self._trackFactory, trackID)
        for compTuple in self._addingTracks[path]:
            if compTuple[0] != None:
                compTuple[0](compTuple[1], trackID)
        del self._addingTracks[path]

    ## returns a list of tuples of the form (trackID, )
    ## FIXME: make faster by doing something like: select
    ##        tracks.trackid, score, plays.datetime from tracks left outer
    ##        join scores using (trackid) left outer join plays using
    ##        (trackid); with some select trackid, max(datetime) from plays
    ##        group by trackid; thrown in.
    def getAllTrackIDs(self, completion, traceCallback=None):
        self._logger.debug("Retrieving all track IDs.")
        self._executeAndFetchAll("select trackid from tracks", (), completion,
                                 traceCallback=traceCallback)
        
    def _getTrackIDCompletion(self, track, trackID, completion,
                              traceCallback, priority=None):
        path = track.getPath()
        self._logger.debug("Retrieving track ID for \'"+path+"\'.")
        if trackID == None:
            self._logger.debug("\'"+path+"\' is not in the library.")
            self.addTrack(path=path, track=track, completion=completion,
                          priority=priority,
                          traceCallback=traceCallback)
            return
        completion(traceCallback, trackID)
        
    def getDirectoryID(self, directory, completion, traceCallback=None):
        self._getDirectoryID(directory, completion,
                             traceCallback=traceCallback)
        
    def addDirectory(self, directory, traceCallback=None):
        self._directoryWalkThread.addDirectory(
            directory, traceCallback=traceCallback)
    
    def addDirectoryNoWatch(self, directory, traceCallback=None):
        self._directoryWalkThread.addDirectoryNoWatch(
            directory, traceCallback=traceCallback)

    def removeDirectory(self, directory, traceCallback=None):
        mycompletion = lambda thisCallback, directoryID, directory=directory:\
            self._removeDirectoryCompletion(directory, directoryID,
                                            thisCallback)
        self.getDirectoryID(directory, mycompletion,
                            traceCallback=traceCallback)
                
    def _removeDirectoryCompletion(self, directory, directoryID,
                                   traceCallback):
        directory = os.path.realpath(directory)
        self._logger.debug("Removing \'"+directory+"\' from the watch list.")
        if directoryID != None:
            mycompletion = lambda thisCallback, directory=directory:\
                self._logger.info("\'"+directory\
                                  +"\' has been removed from the watch list.")
            self._execute("delete from directories where path = ?",
                          (directory, ), mycompletion,
                          traceCallback=traceCallback)
            
        else:
            self._logger.debug("\'"+directory+"\' is not in the watch list.")

    def rescanDirectories(self, traceCallback=None):
        self._directoryWalkThread.rescanDirectories(
            traceCallback=traceCallback)

    ## FIXME: needs to deal with two links using the same first or second track
    def addLink(self, firstTrack, secondTrack, traceCallback=None):
        self.getLinkID(
            firstTrack, secondTrack,
            lambda thisCallback, firstTrackID, secondTrackID, linkID:\
                self._getTrackPathsCompletion(firstTrackID, secondTrackID,
                                              linkID, self._addLinkCompletion,
                                              thisCallback),
            completeTrackIDs=True, traceCallback=traceCallback)
        
    def _addLinkCompletion(self, traceCallback, firstTrackID,
                           firstTrackPath, secondTrackID,  secondTrackPath,
                           linkID):
        if linkID == None:
            mycompletion = lambda thisCallback, firstTrackPath=firstTrackPath,\
                secondTrackPath=secondTrackPath: self._logger.info(
                    "\'"+firstTrackPath+"\' has been linked to \'"\
                    +secondTrackPath+"\'.")
            self._execute(
                "insert into links (firsttrackid, secondtrackid) values (?, ?)",
                (firstTrackID, secondTrackID), mycompletion,
                traceCallback=traceCallback)
        else:
            self._logger.debug("\'"+firstTrackPath+"\' is already linked to \'"\
                               +secondTrackPath+"\'.")

    def _getTrackPathsCompletion(self, firstTrackID, secondTrackID, linkID,
                                 completion, traceCallback):
        multicompletion = MultiCompletion(
            2,
            lambda firstPath, secondPath, firstTrackID=firstTrackID,\
                secondTrackID=secondTrackID, linkID=linkID:\
                    completion(firstTrackID, firstPath, secondTrackID,
                               secondPath, linkID), traceCallback)
        self.getPathFromIDNoDebug(
            firstTrackID,
            lambda thisCallback, firstPath, multicompletion=multicompletion:\
                multicompletion(0, firstPath), traceCallback)
        self.getPathFromIDNoDebug(
            secondTrackID,
            lambda thisCallback, secondPath, multicompletion=multicompletion:\
                multicompletion(1, secondPath), traceCallback)
        
    def getLinkID(self, firstTrack, secondTrack, completion,
                  completeTrackIDs=False, traceCallback=None):
        multicompletion = MultiCompletion(
            2,
            lambda firstTrackID, secondTrackID, completion=completion,\
                completeTrackIDs=completeTrackIDs,\
                traceCallback=traceCallback:\
                    self._getLinkIDCompletion(firstTrackID, secondTrackID,
                                              completion, traceCallback,
                                              completeTrackIDs),
            traceCallback)
        firstTrack.getID(
            lambda thisCallback, firstTrackID, multicompletion=multicompletion:\
                multicompletion(0, firstTrackID),
            traceCallback=traceCallback)
        secondTrack.getID(
            lambda thisCallback, secondTrackID,\
                multicompletion=multicompletion: multicompletion(1,
                                                                 secondTrackID),
            traceCallback=traceCallback)
            
    def _getLinkIDCompletion(self, firstTrackID, secondTrackID, completion,
                             traceCallback, completeTrackIDs):
        mycompletion = lambda thisCallback, linkID, firstTrackID=firstTrackID,\
            secondTrackID=secondTrackID, completion=completion,\
            completeTrackIDs=completeTrackIDs:\
                self._getLinkIDCompletion2(firstTrackID, secondTrackID, linkID,
                                           completion, thisCallback,
                                           completeTrackIDs)
        self._executeAndFetchOneOrNull(
            """select linkid from links where firsttrackid = ? and
               secondtrackid = ?""", (firstTrackID, secondTrackID),
            mycompletion, traceCallback=traceCallback)

    def _getLinkIDCompletion2(self, firstTrackID, secondTrackID, linkID,
                              completion, traceCallback,
                              completeTrackIDs):
        self._logger.debug("Retrieving link ID.")
        if linkID == None:
            self._logger.debug("The tracks are not linked.")
        if completeTrackIDs == True:
            completion(traceCallback, firstTrackID, secondTrackID, linkID)
        else:
            completion(traceCallback, linkID)
    
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
#            firstTrack, lambda firstLinkIDs: multicompletion(0,
#                                                                 firstLinkIDs))
#        self.getLinkIDs(
#            secondTrack, lambda secondLinkIDs: multicompletion(
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

    ## if there are two links for a track, returns the link with track as second
    ## track first for queueing ease
    def getLinkIDs(self, track, completion, traceCallback=None):
        track.getID(
            lambda thisCallback, trackID, completion=completion:\
                self._getLinkIDsCompletion(trackID, completion, thisCallback),
            traceCallback=traceCallback)
        
    def _getLinkIDsCompletion(self, trackID, completion, traceCallback):
        multicompletion = MultiCompletion(
            2, lambda firstLinkID, secondLinkID, trackID=trackID,\
                completion=completion, traceCallback=traceCallback:\
                    self._getLinkIDsCompletion2(trackID, firstLinkID,
                                                secondLinkID, completion,
                                                traceCallback))
        self._executeAndFetchOneOrNull(
            "select linkid from links where secondtrackid = ?", (trackID, ),
            lambda thisCallback, firstLinkID, multicompletion=multicompletion:\
                multicompletion(0, firstLinkID),
            traceCallback=traceCallback)
        self._executeAndFetchOneOrNull(
            "select linkid from links where firsttrackid = ?", (trackID, ),
            lambda thisCallback, secondLinkID, multicompletion=multicompletion:\
                multicompletion(1, secondLinkID),
            traceCallback=traceCallback)

    def _getLinkIDsCompletion2(self, trackID, firstLinkID, secondLinkID,
                               completion, traceCallback):
        self._logger.debug("Retrieving link IDs.")
        if firstLinkID == None and secondLinkID == None:
            self.getPathFromIDNoDebug(
                trackID,
                lambda thisCallback, path: self._logger.debug(
                    "\'"+path+"\' is not linked to another track."),
                traceCallback)
        completion(traceCallback, firstLinkID, secondLinkID)
            
    def getLinkedTrackIDs(self, linkID, completion, traceCallback=None):
        mycompletion = lambda thisCallback, trackIDs, completion=completion:\
            self._getLinkedTrackIDsCompletion(trackIDs, completion,
                                              thisCallback)
        self._executeAndFetchOneOrNull(
            "select firsttrackid, secondtrackid from links where linkid = ?",
            (linkID, ), mycompletion, returnTuple=True,
            traceCallback=traceCallback)

    def _getLinkedTrackIDsCompletion(self, trackIDs, completion,
                                     traceCallback):
        self._logger.debug("Retrieving track IDs for linked tracks.")
        if trackIDs == None:
            self._logger.debug("No such link exists.")
        completion(traceCallback, trackIDs)

    def removeLink(self, firstTrack, secondTrack, traceCallback=None):
        mycompletion = lambda thisCallback, linkID, firstTrack=firstTrack,\
            secondTrack=secondTrack: self._removeLinkCompletion(firstTrack,
                                                                secondTrack,
                                                                linkID,
                                                                thisCallback)
        self.getLinkID(firstTrack, secondTrack, mycompletion,
                       traceCallback=traceCallback)

    def _removeLinkCompletion(self, firstTrack, secondTrack, linkID,
                              traceCallback):
        self._logger.debug("Removing link.")
        firstTrackPath = firstTrack.getPath()
        secondTrackPath = secondTrack.getPath()
        if linkID != None:
            mycompletion = lambda thisCallback, firstTrackPath=firstTrackPath,\
                secondTrackPath=secondTrackPath: self._logger.info(
                    "\'"+firstTrackPath+"\' is no longer linked to \'"\
                    +secondTrackPath+"\'.")
            self._execute("delete from links where linkid = ?", (linkID, ),
                          mycompletion, traceCallback=traceCallback)
        else:
            self._logger.debug("\'"+firstTrackPath+"\' is not linked to \'"\
                               +secondTrackPath+"\'.")

    def addPlay(self, track, msDelay=0, completion=None, priority=None,
                traceCallback=None):
        mycompletion = lambda thisCallback, trackID, track=track,\
            msDelay=msDelay, completion=completion: self._addPlayCompletion(
                track, trackID, thisCallback, msDelay, completion, priority)
        track.getID(mycompletion, priority=priority,
                    traceCallback=traceCallback)

    def _addPlayCompletion(self, track, trackID, traceCallback, msDelay=0,
                           completion=None, priority=None):
        self._logger.debug("Adding play.")
        now = datetime.datetime.now()
        delay = datetime.timedelta(0, 0, 0, msDelay)
        playTime = now - delay
        self.getLastPlayedInSeconds(
            track,
            lambda thisCallback, previousPlay, track=track:\
                track.setPreviousPlay(previousPlay), traceCallback)
        if completion == None:
            mycompletion = lambda thisCallback: doNothing()
        else:
            mycompletion = lambda thisCallback: completion(thisCallback)
        self._executeMany(["""insert into plays (trackid, datetime) values
                              (?, datetime(?))""",
                           """update tracks set lastplayed = datetime(?) where
                              trackid = ?"""],
                          [(trackID, playTime), (playTime, trackID)],
                          mycompletion, priority=priority,
                          traceCallback=traceCallback)
             
    def getLastPlayedTrackID(self, completion, errcompletion, priority=None,
                             traceCallback=None):
        mycompletion = lambda thisCallback, trackID, completion=completion,\
            errcompletion=errcompletion: self._getLastPlayedTrackIDCompletion(
                trackID, completion, errcompletion, thisCallback)
        self._executeAndFetchOneOrNull(
            "select trackid from plays order by playid desc", (), mycompletion,
            priority=priority, traceCallback=traceCallback)
        
    def _getLastPlayedTrackIDCompletion(self, trackID, completion,
                                        errcompletion, traceCallback):
        if trackID != None:
            completion(traceCallback, trackID)
        else:
            self._logger.error("No plays recorded.")
            errcompletion(EmptyDatabaseError)

    def _getLastPlayed(self, completion, track=None, trackID=None, debug=True,
                       priority=None, traceCallback=None):
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                # FIXME: cannot be handled
                raise NoTrackError(trace=getTrace(traceCallback))
            mycompletion = lambda thisCallback, newTrackID, completion=completion,\
                priority=priority: self._getLastPlayedCompletion(
                    newTrackID, completion, thisCallback, priority=priority)
            track.getID(mycompletion, priority=priority,
                        traceCallback=traceCallback)
            return
        self._getLastPlayedCompletion(trackID, completion, traceCallback,
                                      debug=debug, priority=priority)
        
    def _getLastPlayedCompletion(self, trackID, completion, traceCallback,
                                 debug=True, priority=None):
        (self._basicLastPlayedIndex, self._localLastPlayedIndex,
         self._secondsSinceLastPlayedIndex,
         self._lastPlayedInSecondsIndex) = range(4)
        mycompletion = lambda thisCallback, playDetails, trackID=trackID,\
            completion=completion, debug=debug: self._getLastPlayedCompletion2(
                trackID, playDetails, completion, thisCallback, debug=debug)
        self._executeAndFetchOneOrNull(
            """select datetime, datetime(datetime, 'localtime'),
               strftime('%s', 'now') - strftime('%s', datetime),
               strftime('%s', datetime) from plays where trackid = ? order by
               playid desc""", (trackID, ), mycompletion, returnTuple=True,
            priority=priority, traceCallback=traceCallback)
        
    def _getLastPlayedCompletion2(self, trackID, playDetails, completion,
                                  traceCallback, debug=True):
        if playDetails == None and self._debugMode == True and debug == True:
            self.getPathFromIDNoDebug(
                trackID,
                lambda thisCallback, path: self._logger.debug(
                    "\'"+path+"\' has never been played."), traceCallback)
        completion(traceCallback, playDetails)

    def getLastPlayed(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._basicLastPlayedIndex,
                                      completion, thisCallback,
                                      "Retrieving time of last play.")
        self._getLastPlayed(traceCallback, mycompletion, track=track,
                            traceCallback=traceCallback)
    
    def getLastPlayedLocalTime(self, track, completion, priority=None,
                               traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(
                details, self._localLastPlayedIndex, completion, thisCallback,
                "Retrieving time of last play in localtime.")
        self._getLastPlayed(mycompletion, track=track, priority=priority,
                            traceCallback=traceCallback)
            
    def getLastPlayedInSeconds(self, track, completion, priority=None,
                               traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(
                details, self._lastPlayedInSecondsIndex,
                lambda callback, lastPlayed, completion=completion:\
                    self._getLastPlayedInSecondsCompletion(lastPlayed,
                                                           completion,
                                                           callback),
                thisCallback)
        self._getLastPlayed(mycompletion, track=track, priority=priority,
                            traceCallback=traceCallback)

    def _getLastPlayedInSecondsCompletion(self, lastPlayed, completion,
                                          traceCallback):
        if lastPlayed != None:
            lastPlayed = int(lastPlayed)
        completion(traceCallback, lastPlayed)
    
    def getSecondsSinceLastPlayedFromID(self, trackID, completion, debug=True,
                                        traceCallback=None):
        if self._debugMode == True and debug == True:
            debugMessage = "Calculating time since last played."
        else:
            debugMessage = None
        mycompletion = lambda thisCallback, details, completion=completion,\
            debugMessage=debugMessage: self._getDetailCompletion(
                details, self._secondsSinceLastPlayedIndex, completion,
                thisCallback, debugMessage)
        self._getLastPlayed(mycompletion, trackID=trackID, debug=debug,
                            traceCallback=traceCallback)

    def getRandomizerList(self, completion, traceCallback=None):
        self._executeAndFetchAll("""select trackid, strftime('%s', 'now') - 
                                    strftime('%s', lastplayed), score, unscored
                                    from tracks""", (),
                                 completion, traceCallback=traceCallback)

    # FIXME: as soon as a file is deleted or moved, so it can't get
    #        played again, this will get stuck. We need to keep track of
    #        whether entries are current or historical. Partially fixed: 
    #        currently bad tracks rely on being chosen by randomizer to update 
    #        historical status.
    def getOldestLastPlayed(self, completion, priority=None,
                            traceCallback=None):
        self._executeAndFetchOneOrNull(
            """select strftime('%s', 'now') - strftime('%s', min(datetime))
               from (select max(playid) as id, trackid from plays,
                     (select trackid as historicalid from tracks where
                      historical = 0) as historicaltracks where
                     plays.trackid = historicaltracks.historicalid group by
                     trackid) as maxplays, plays where maxplays.id =
               plays.playid""", (),
            lambda thisCallback, oldest, completion=completion:\
                self._getOldestLastPlayedCompletion(oldest, completion,
                                                    thisCallback),
            priority=priority, traceCallback=traceCallback)

    def _getOldestLastPlayedCompletion(self, oldest, completion, traceCallback):
        if oldest == None:
            oldest = 0
        completion(traceCallback, oldest)
        
    def getPlayCount(self, completion, track=None, trackID=None, priority=None,
                     traceCallback=None):
        self._logger.debug("Retrieving play count.")
        mycompletion = lambda thisCallback, plays, completion=completion:\
            self._getPlayCountCompletion(plays, completion, thisCallback)
        mycompletion2 = lambda thisCallback, trackID,\
            mycompletion=mycompletion, priority=priority:\
                self._executeAndFetchAll(
                    """select datetime from plays where trackid = ? order by
                       playid desc""", (trackID, ), mycompletion,
                    priority=priority, traceCallback=thisCallback)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                # FIXME: probably broken
                raise NoTrackError(trace=getTrace(traceCallback))
            trackID = track.getID(mycompletion2, priority=priority,
                                  traceCallback=traceCallback)
            return
        mycompletion2(traceCallback, trackID)

    def _getPlayCountCompletion(self, plays, completion, traceCallback):
        if plays == None:
            completion(traceCallback, 0)
            return
        completion(traceCallback, len(plays))
    
#    def updateAllTrackDetails(self):
#        trackIDs = self.getAllTrackIDs()
#        for trackID in trackIDs:
#            try:
#                track = self._trackFactory.getTrackFromID()
#                self.maybeUpdateTrackDetails(track)
#            except NoTrackError:
#                self.setHistorical(True, trackID)

    def _getTrackDetails(self, completion, track=None, trackID=None,
                         priority=None, traceCallback=None):
        self._numberIndices = 9
        (self._pathIndex, self._artistIndex, self._albumIndex, self._titleIndex,
         self._trackNumberIndex, self._unscoredIndex, self._lengthIndex,
         self._bpmIndex, self._historicalIndex) = range(self._numberIndices)
        mycompletion = lambda thisCallback, trackID, completion=completion,\
            priority=priority: self._executeAndFetchOne(
                """select path, artist, album, title, tracknumber, unscored,
                   length, bpm, historical from tracks where trackid = ?""",
                (trackID, ), completion, returnTuple=True, priority=priority,
                traceCallback=thisCallback)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                raise NoTrackError(trace=getTrace(traceCallback))
            track.getID(mycompletion, priority=priority,
                        traceCallback=traceCallback)
        else:
            mycompletion(traceCallback, trackID)

    def maybeUpdateTrackDetails(self, track, traceCallback=None):
        mycompletion = lambda thisCallback, change, track=track:\
            self._maybeUpdateTrackDetailsCompletion(track, change, thisCallback)
        self._getTrackDetailsChange(track, mycompletion, traceCallback)
        
    def _maybeUpdateTrackDetailsCompletion(self, track, change, traceCallback):
        if change == True:
            self._updateTrackDetails(track, traceCallback=traceCallback)

    def _getTrackDetailsChange(self, track, completion, traceCallback):
        mycompletion = lambda thisCallback, details, track=track,\
            completion=completion: self._getTrackDetailsChangeCompletion(
                track, details, completion, thisCallback)
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
        
    def _getTrackDetailsChangeCompletion(self, track, details, completion,
                                         traceCallback):
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
                    completion(traceCallback, True)
                    return
            except KeyError:
                continue
        completion(traceCallback, False)
    
    def getPath(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, path, completion=completion:\
            self._getPathCompletion(path, completion, thisCallback)
        self.getPathNoDebug(track, mycompletion, traceCallback=traceCallback)

    def _getPathCompletion(self, path, completion, traceCallback):
        self._logger.debug("Retrieving track's path.")
        completion(traceCallback, path)
        
    def _getDetailCompletion(self, details, index, completion, traceCallback,
                             debugMessage=None):
        if debugMessage != None:
            self._logger.debug(debugMessage)
        if details == None:
            completion(traceCallback, None)
            return
        completion(traceCallback, details[index])
    
    def getPathNoDebug(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._pathIndex, completion,
                                      thisCallback)
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
            
    def getPathFromID(self, trackID, completion, priority=None,
                      traceCallback=None):
        mycompletion = lambda thisCallback, path, completion=completion:\
            self._getPathFromIDCompletion(path, completion, thisCallback)
        self.getPathFromIDNoDebug(trackID, mycompletion, priority=priority,
                                  traceCallback=traceCallback)

    def _getPathFromIDCompletion(self, path, completion, traceCallback):
        self._logger.debug("Retrieving track's path.")
        completion(traceCallback, path)
    
    def getPathFromIDNoDebug(self, trackID, completion, priority=None,
                             traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._pathIndex, completion,
                                      thisCallback)
        self._getTrackDetails(mycompletion, trackID=trackID, priority=priority,
                              traceCallback=traceCallback)
    
    def getArtist(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._artistIndex, completion,
                                      thisCallback,
                                      debugMessage="Retrieving track's artist.")
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
    
    def getAlbum(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._albumIndex, completion,
                                      thisCallback,
                                      debugMessage="Retrieving track's album.")
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
    
    def getTitle(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._titleIndex, completion,
                                      thisCallback,
                                      debugMessage="Retrieving track's title.")
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
    
    def getTrackNumber(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(details, self._trackNumberIndex,
                                      completion, thisCallback,
                                      debugMessage="Retrieving track's number.")
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
    
    def getBPM(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, track=track,\
            completion=completion: self._getBPMCompletion(track, details,
                                                          completion,
                                                          thisCallback)
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)

    def _getBPMCompletion(self, track, details, completion, traceCallback):
        self._logger.debug("Retrieving track's bpm.")
        if details == None:
            completion(traceCallback, None)
            return
        bpm = details[self._bpmIndex]
        if bpm == None:
            bpm = track.getBPM()
            self.setBPM(bpm, track, traceCallback=traceCallback)
        completion(traceCallback, bpm)
    
    def setBPM(self, bpm, track, traceCallback=None):
        mycompletion = lambda thisCallback, trackID, bpm=bpm:\
            self._setBPMCompletion(bpm, trackID, thisCallback)
        track.getID(mycompletion, traceCallback=traceCallback)
            
    def _setBPMCompletion(self, bpm, trackID, traceCallback):
        mycompletion = lambda thisCallback: self._logger.debug(
            "Adding bpm to track.")
        self._execute("update tracks set bpm = ? where trackID = ?",
                      (bpm, trackID), mycompletion, traceCallback=traceCallback)
    
    def getHistorical(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, completion=completion:\
            self._getDetailCompletion(
                details, self._historicalIndex, completion, thisCallback,
                debugMessage="Retrieving track's currency.")
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
    
    def getLengthString(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, rawLength, completion=completion:\
            completion(thisCallback, formatLength(rawLength))
        self.getLength(track, mycompletion, traceCallback=traceCallback)
        
    def getLength(self, track, completion, traceCallback=None):
        mycompletion = lambda thisCallback, details, track=track,\
            completion=completion: self._getLengthCompletion(track, details,
                                                             completion,
                                                             thisCallback)
        self._getTrackDetails(mycompletion, track=track,
                              traceCallback=traceCallback)
    
    def _getLengthCompletion(self, track, details, completion, traceCallback):
        self._logger.debug("Retrieving track's length.")
        if details == None:
            completion(traceCallback, None)
            return
        length = details[self._lengthIndex]
        if length == None:
            length = track.getLength()
            self.setLength(length, track, traceCallback=traceCallback)
        completion(traceCallback, length)
        
    def setLength(self, length, track, traceCallback=None):
        mycompletion = lambda thisCallback, trackID, length=length:\
            self._setLengthCompletion(length, trackID, thisCallback)
        track.getID(mycompletion, traceCallback=traceCallback)

    def _setLengthCompletion(self, length, trackID, traceCallback=None):
        mycompletion = lambda thisCallback: self._logger.debug(
            "Adding length to track.")
        self._execute("update tracks set length = ? where trackID = ?",
                      (length, trackID), mycompletion,
                      traceCallback=traceCallback)
        
    def addTagName(self, tagName, traceCallback=None):
        mycompletion = lambda thisCallback: self._logger.debug(
            "Adding tag name.")
        self._execute("insert into tagnames (name) values (?)", (tagName, ),
                      mycompletion, traceCallback=traceCallback)
            
    def getAllTagNames(self, completion, priority=None, traceCallback=None):
        mycompletion = lambda thisCallback, names, completion=completion:\
            self._getAllTagNamesCompletion(names, completion, thisCallback)
        self._executeAndFetchAll("select name from tagnames", (), mycompletion,
                                 priority=priority, traceCallback=traceCallback)
        
    def _getAllTagNamesCompletion(self, names, completion, traceCallback):
        self._logger.debug("Retrieving all tag names.")
        if names == None:
            completion(traceCallback, [])
            return
        tagNames = []
        for (name, ) in names:
            tagNames.append(name)
        completion(traceCallback, tagNames)
        
    def getTagNameID(self, tagName, completion, traceCallback=None):
        self._executeAndFetchOne(
            "select tagnameid from tagnames where name = ?", (tagName, ),
            completion, traceCallback=traceCallback)
            
    def setTag(self, track, tagName, traceCallback=None):
        multicompletion = MultiCompletion(
            3,
            lambda trackID, tagNames, tagNameID, tagName=tagName,
                traceCallback=traceCallback: self._setTagCompletion(
                    trackID, tagName, tagNameID, tagNames, traceCallback),
            traceCallback)
        track.getID(
            lambda thisCallback, trackID, multicompletion=multicompletion:\
                multicompletion(0, trackID), traceCallback=traceCallback)
        self.getTags(
            track,
            lambda thisCallback, tagNames, multicompletion=multicompletion:\
                multicompletion(1, tagNames), traceCallback=traceCallback)
        self.getTagNameID(
            tagName,
            lambda thisCallback, tagNameID, multicompletion=multicompletion:\
                multicompletion(2, tagNameID), traceCallback=traceCallback)
            
    def _setTagCompletion(self, trackID, tagName, tagNameID, tagNames,
                          traceCallback):
        if tagName not in tagNames:
            mycompletion = lambda thisCallback, tagName=tagName:\
                self._logger.info("Tagging track with '"+tagName+"'.")
            self._execute("insert into tags (trackid, tagnameid) values (?, ?)",
                          (trackID, tagNameID), mycompletion,
                          traceCallback=traceCallback)
        
    def unsetTag(self, track, tagName, traceCallback=None):
        multicompletion = MultiCompletion(3, self._unsetTagCompletion)
        track.getID(
            lambda trackID, multicompletion=multicompletion: multicompletion(
                0, trackID))
        self.getTagNameID(
            tagName,
            lambda tagNameID, multicompletion=multicompletion: multicompletion(
                1, tagNameID))
        multicompletion(2, traceCallback)
        
    def _unsetTagCompletion(self, trackID, tagNameID, traceCallback):
        self._execute("delete from tags where tagnameid = ? and trackid = ?",
                      (tagNameID, trackID), lambda thisCallback: doNothing(),
                      traceCallback)
        
    def getTagNameFromID(self, tagNameID, completion, priority=None,
                         traceCallback=None):
        self._executeAndFetchOne(
            "select name from tagnames where tagnameid = ?", (tagNameID, ),
            completion, priority=priority, traceCallback=traceCallback)

    def getTags(self, track, completion, priority=None, traceCallback=None):
        mycompletion = lambda thisCallback, trackID, completion=completion,\
            priority=priority: self.getTagsFromTrackID(
                trackID, completion, priority=priority,
                traceCallback=thisCallback)
        track.getID(mycompletion, traceCallback=traceCallback)

    def getTagsFromTrackID(self, trackID, completion, priority=None,
                           traceCallback=None):
        mycompletion = lambda thisCallback, tagNameIDs, completion=completion,\
            priority=priority: self._getTagsFromTrackIDCompletion(
                tagNameIDs, completion, thisCallback, priority=priority)
        self._executeAndFetchAll(
            "select tagnameid from tags where trackid = ?", (trackID, ),
            mycompletion, priority=priority, throwException=False,
            traceCallback=traceCallback)
        
    def _getTagsFromTrackIDCompletion(self, tagNameIDs, completion,
                                      traceCallback, priority=None):
        self._logger.debug("Retrieving track tags.")
        if tagNameIDs == None:
            completion(traceCallback, [])
            return
        self._tagNames = []
        for (tagNameID, ) in tagNameIDs:
            mycompletion = lambda thisCallback, tagName: self._tagNames.append(
                tagName)
            self.getTagNameFromID(tagNameID, mycompletion, priority=priority,
                                  traceCallback=traceCallback)
        self.complete(
            lambda thisCallback: completion(thisCallback, self._tagNames),
            priority=priority, traceCallback=traceCallback)

    def getIsScored(self, track, completion, priority=None, traceCallback=None):
        self._getIsScored(completion, track=track, priority=priority,
                          traceCallback=None)

    def getIsScoredFromID(self, trackID, completion, debug=True,
                          traceCallback=None):
        self._getIsScored(completion, trackID=trackID, debug=debug,
                          traceCallback=None)
        
    ## determines whether user has changed score for this track
    def _getIsScored(self, completion, track=None, trackID=None, debug=True,
                     priority=None, traceCallback=None):
        if self._debugMode == True and debug == True:
            debugMessage = "Retrieving track's unscored status."
        else:
            debugMessage = None
        mycompletion = lambda thisCallback, details, completion=completion,\
            debugMessage=debugMessage: self._getDetailCompletion(
                details, self._unscoredIndex, lambda callback, unscored,\
                    completion=completion: self._getIsScoredCompletion(
                        unscored, completion, callback), thisCallback,
                debugMessage=debugMessage)
        if trackID != None:
            self._getTrackDetails(mycompletion, trackID=trackID,
                                  priority=priority,
                                  traceCallback=traceCallback)
        else:
            self._getTrackDetails(mycompletion, track=track, priority=priority,
                                  traceCallback=traceCallback)
        
    def _getIsScoredCompletion(self, unscored, completion, traceCallback):
        if unscored == None:
            completion(traceCallback, None)
        elif unscored == 1:
            completion(traceCallback, False)
        elif unscored == 0:
            completion(traceCallback, True)
    
    ## poss should add a record to scores table
    def setUnscored(self, track, traceCallback=None):
        track.getID(
            lambda thisCallback, trackID: self._execute(
                "update tracks set unscored = 1 where trackid = ?", (trackID, ),
                lambda thisCallback: self._logger.debug(
                    "Setting track as unscored."), traceCallback=thisCallback),
            traceCallback)
        
    ## poss add track if track not in library
    def setScore(self, track, score, traceCallback=None):
        track.getID(
            lambda thisCallback, trackID, score=score: self._setScoreCompletion(
                trackID, score, thisCallback), traceCallback)

    def _setScoreCompletion(self, trackID, score, traceCallback):
        self._executeMany(
            ["update tracks set unscored = 0, score = ? where trackid = ?",
             """insert into scores (trackid, score, datetime) values
                (?, ?, datetime('now'))"""],
            [(score, trackID), (trackID, score)],
            lambda thisCallback: self._logger.debug("Setting track's score."),
            traceCallback=traceCallback)

    def _getScore(self, completion, track=None, trackID=None, debug=True,
                  priority=None, traceCallback=None):
        mycompletion = lambda thisCallback, trackID, completion=completion,\
            debug=debug, priority=priority: self._executeAndFetchOneOrNull(
                """select score from scores where trackid = ? order by scoreid
                   desc""", (trackID, ),
                lambda callback, score, completion=completion, debug=debug:\
                    self._internalGetScoreCompletion(score, completion,
                                                     callback, debug=debug),
                priority=priority, traceCallback=thisCallback)
        if trackID == None:
            if track == None:
                self._logger.error("No track has been identified.")
                # FIXME: probably doesn't work
                raise NoTrackError(trace=getTrace(traceCallback))
            track.getID(mycompletion, priority=priority,
                        traceCallback=traceCallback)
            return
        mycompletion(traceCallback, trackID)
        
    def _internalGetScoreCompletion(self, score, completion, traceCallback,
                                    debug=True):
        if debug == True:
            self._logger.debug("Retrieving track's score.")
        completion(traceCallback, score)
            
    def getScore(self, track, completion, traceCallback=None):
        self.getIsScored(
            track,
            lambda thisCallback, isScored, completion=completion, track=track:\
                self._getScoreCompletion(isScored, completion, thisCallback,
                                         completeWithDash=True, track=track),
            traceCallback=traceCallback)
    
    def _getScoreCompletion(self, isScored, completion, completeWithDash=False,
                            track=None, trackID=None, debug=True,
                            priority=None, traceCallback=None):
        if isScored == False:
            if completeWithDash == True:
                completion(traceCallback, "-")
            else:
                completion(traceCallback, self._defaultScore)
        else:
            self._getScore(completion, track=track, trackID=trackID,
                           debug=debug, priority=priority,
                           traceCallback=traceCallback)
    
    def getScoreValue(self, track, completion, priority=None,
                      traceCallback=None):
        self.getIsScored(
            track,
            lambda thisCallback, isScored, completion=completion, track=track,\
                priority=priority: self._getScoreCompletion(
                    isScored, completion, track=track, priority=priority,
                    traceCallback=thisCallback),
            priority=priority, traceCallback=traceCallback)
    
    def getScoreValueFromID(self, trackID, completion, debug=True,
                            traceCallback=None):
        self.getIsScoredFromID(
            trackID,
            lambda thisCallback, isScored, completion=completion,\
                trackID=trackID, debug=debug: self._getScoreCompletion(
                    isScored, completion, trackID=trackID, debug=debug,
                    traceCallback=thisCallback),
            debug=debug, traceCallback=traceCallback)

    def maybeGetIDFromPath(self, path, completion, traceCallback=None):
        path = os.path.realpath(path)
        self._executeAndFetchOneOrNull(
            "select trackid from tracks where path = ?", (path, ), completion,
            traceCallback=traceCallback)

#    def getIDFromPath(self, path):
#        id = self.maybeGetIDFromPath(path)
#        if id is None:
#            raise PathNotFoundError()

    def getNumberOfTracks(self, completion, priority=None, traceCallback=None):
        self._executeAndFetchOne("select count(*) from tracks", (), completion,
                                 priority=priority, traceCallback=traceCallback)
    
    # FIXME(ben): create indexes on tracks(trackid) and plays(trackid)
    # or this is slow!
    def getNumberOfUnplayedTracks(self, completion, priority=None,
                                  traceCallback=None):
        self._executeAndFetchOne(
            """select count(*) from tracks left outer join plays using(trackid)
               where plays.trackid is null""", (), completion,
            priority=priority, traceCallback=traceCallback)
        
    # returns an array of [ score, count ]
    def getScoreTotals(self, completion, priority=None, traceCallback=None):
        self._executeAndFetchAll(
            """select score, count(score)
               from (select max(scoreid), x.trackid, score
                     from scores, (select distinct trackid from scores) as x
                     where scores.trackid = x.trackid group by scores.trackid)
               group by score;""", (), completion, priority=priority,
            traceCallback=traceCallback)

    def abort(self, interruptWalk=False, traceCallback=None):
        self._directoryWalkThread.setAbortInterrupt(interruptWalk)
        self._directoryWalkThread.abort()
    
    def dumpQueues(self, path):
        self._directoryWalkThread.dumpQueue(path+"DirectoryWalkerQueue.dump", 1)
        self._dbThread.dumpQueue(path+"DatabaseQueue.dump", 1) 
    
    def getDirectoryWalking(self):
        return self._directoryWalkThread.getWorking()

    def getPrefsPage(self, parent, logger, system):
        return PrefsPage(parent, system, self._configParser, logger,
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

class PrefsPage(BasePrefsPage):
    def __init__(self, parent, system, configParser, logger,
                 defaultDefaultScore):
        BasePrefsPage.__init__(self, parent, system, configParser, logger,
                               "Database", defaultDefaultScore)
        
        self._initCreateDefaultScoreSizer()

        self.SetSizer(self._defaultScoreSizer)

    def _initCreateDefaultScoreSizer(self):
        self._defaultScoreSizer = wx.BoxSizer(wx.HORIZONTAL)

        defaultScoreLabel = wx.StaticText(self, wx.NewId(), "Default Score: ")
        self._defaultScoreSizer.Add(defaultScoreLabel, 0,
                                    wx.LEFT|wx.TOP|wx.BOTTOM, 3)

        self._defaultScoreControl = wx.TextCtrl(
            self, wx.NewId(), str(self._settings["defaultScore"]), size=(35,-1))
        self._defaultScoreSizer.Add(self._defaultScoreControl, 0)

        self.Bind(wx.EVT_TEXT, self._onDefaultScoreChange,
                  self._defaultScoreControl)

    def _onDefaultScoreChange(self, e):
        if validateNumeric(self._defaultScoreControl):
            defaultScore = self._defaultScoreControl.GetLineText(0)
            if defaultScore != "":
                self._settings["defaultScore"] = int(defaultScore)

    def _setDefaults(self, defaultDefaultScore):
        self._defaultDefaultScore = defaultDefaultScore

    def _loadSettings(self):
        try:
            ## FIXME: poss should be main setting?
            defaultScore = self._configParser.getint("Database", "defaultScore")
            self._settings["defaultScore"] = defaultScore
        except ConfigParser.NoOptionError:
            self._settings["defaultScore"] = self._defaultDefaultScore
