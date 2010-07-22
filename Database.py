## Database Control

import mutagen
import Track
import os
import sqlite3

class Database:
    ## TODO: check if track table already exists first to confirm whether or not
    ##       to create other tables (poss corruption)
    def __init__(self, databasePath="database", defaultScore=10):
        self.databasePath = databasePath
        self.defaultScore = defaultScore
        self.conn = sqlite3.connect(self.databasePath)        
        self.initCreateTrackTable()
        self.initCreateDirectoryTable()
        self.initCreatePlaysTable()
        self.initCreateScoresTable()
        self.conn.commit()

    def initCreateTrackTable(self):
        c = self.conn.cursor()
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

    def initCreateDirectoryTable(self):
        c = self.conn.cursor()
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

    def initCreatePlaysTable(self):
        c = self.conn.cursor()
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

    def initCreateScoresTable(self):
        c = self.conn.cursor()
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

    def addTrack(self, path):
        track = Track.getTrackFromPathNoID(self, path)
        if track != None:
            c = self.conn.cursor()
            trackID = self.getTrackID(track)
            path = track.getPath()
            if trackID == None:
                c.execute("""insert into tracks (path, artist, album, title,
                          tracknumber, unscored) values
                          (?, ?, ?, ?, ?, 1)""", (path, track.getArtist(),
                                                     track.getAlbum(),
                                                     track.getTitle(),
                                                     track.getTrackNumber(), ))
                trackID = c.lastrowid
                print "\'"+path+"\' has been added to the library."
            else:
                print "\'"+path+"\' is already in the library."                
            c.close()
            self.conn.commit()
            track.setID(trackID)
        else:
            print "Invalid file."

    def addDirectoryNoWatch(self, directory):
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = directory+'/'+contents[n]
            if os.path.isdir(path):
                self.addDirectoryNoWatch(path)
            else: ## or: elif contents[n][-4:]=='.mp3':
                self.addTrack(path)

    def addDirectory(self, directory):
        c = self.conn.cursor()
        DirectoryID = self.getDirectoryID(directory)
        if DirectoryID == None:
            c.execute("insert into directories (path) values (?)", (directory,))
            print "\'"+directory+"\' has been added to the watch list."
        else:
            print "\'"+directory+"\' is already in the watch list."
        c.close()
        self.conn.commit()
        self.addDirectoryNoWatch(directory)

    def removeDirectory(self, directory):
        c = self.conn.cursor()
        DirectoryID = self.getDirectoryID(directory)
        if DirectoryID != None:
            c.execute("delete from directories where path = ?", (directory,))
            print "\'"+directory+"\' has been removed from the watch list."
        else:
            print "\'"+directory+"\' is not in the watch list."
        c.close()
        self.conn.commit()

    def rescanDirectories(self):
        c = self.conn.cursor()
        c.execute("select path from directories")
        result = c.fetchall()
        for n in result:
            self.addDirectoryNoWatch(n[0])
        self.conn.commit()

##    def deleteTrack(self, path):
##        track = track.getTrackFromPathNoID(path)
##        if track != None:
##            c = self.conn.cursor()
##            if self.getTrackID(track.getPath()) != None:
##                trackID = self.getTrackID(track.getPath())
##                c.execute("delete from tracks where path = ? ",
##                          (track.getPath(), ))
##                c.execute("delete from plays where trackid = ?", (trackID, ))
##                track.setID(trackID)
##                print "\'"+track.getPath()+"\' and associated plays have been removed from the library."
##            else:
##                print "\'"+track.getPath()+"\' is not in the library."
##            c.close()
##            self.conn.commit()
##        else:
##            print "Invalid file."

##    def deleteDirectory(self, directory):
##        contents = os.listdir(directory)
##        for n in range(0, len(contents)):
##            path = directory+'/'+contents[n]
##            if os.path.isdir(path):
##                self.removeDirectory(path)
##            else:
##                self.removeTrack(path)

    ## poss add track if track not in library
    def addPlay(self, track):
##        track = self.getTrackDetails(path)
        c = self.conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
        else:
            c.execute("""insert into plays (trackid, datetime) values
                      (?, datetime('now'))""", (trackID, ))
        c.close()
        self.conn.commit()
            
    ## poss add track if track not in library
    def setScore(self, track, score):
        c = self.conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
        else:
##            c.execute("""update tracks set score = ?, unscored = 0 where
##                      trackid = ?""", (score, trackID))
            c.execute("update tracks set unscored = 0 where trackid = ?",
                      (trackID, ))
            c.execute("""insert into scores (trackid, score, datetime) values
                      (?, ?, datetime('now'))""", (trackID, score, ))
        c.close()
        self.conn.commit()

    ## poss should add a record to scores table
    def setUnscored(self, track):
        c = self.conn.cursor()
        trackID = track.getID()
        if trackID == None:
            print "\'"+self.getPath(track)+"\' is not in the library."
        else:
##            c.execute("""insert into scores (trackid, score, datetime) values
##                      (?, ?, datetime('now'))""", (trackID,
##                                                   self.defaultScore, ))
            c.execute("""update tracks set unscored = 1 where
                      trackid = ?""", (trackID, ))
        c.close()
        self.conn.commit()

    def getTrackID(self, track):
        c = self.conn.cursor()
        c.execute("select trackid from tracks where path = ?",
                  (track.getPath(), ))
        result = c.fetchone()
        c.close()
        if result == None:
            return result
        else:
            return result[0]

    def getDirectoryID(self, path):
        c = self.conn.cursor()
        c.execute("select directoryid from directories where path = ?",
                  (path, ))
        result = c.fetchone()
        c.close()
        if result == None:
            return result
        else:
            return result[0]        

##    def getTrackDetails(self, path):
##        track = ''
##        try:
##            track = ID3Track(path)
####            return True
##        except mutagen.id3.ID3NoHeaderError as e:
##            if path[0] != "\'":
##                fullPath = "\'"+path+"\'"
##            else:
##                fullPath = path
##            if str(e) != fullPath+" doesn't start with an ID3 tag":
##                raise e
##            print fullPath+" does not have an ID3 tag."
####            try:
####                track.MP4Track(path)
##            return None
##        return track

    ## determines whether user has changed score for this track
    def isScored(self, track):
        c = self.conn.cursor()
        c.execute("select unscored from tracks where trackid = ?",
                  (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result[0] == 1:
            return False
        elif result[0] == 0:
            return True

    def getScore(self, track):
        if self.isScored(track) == True:
            c = self.conn.cursor()
            c.execute("""select score from scores where trackid = ? order by
                      scoreid desc""",
                      (track.getID(), ))
            result = c.fetchone()
            c.close()
            if result != None:
                return result[0]
            else:
                print "\'"+self.getPath(track)+"\' has no score associated with it in the library."
        elif self.isScored(track) == False:
            return "-"

    def getScoreValue(self, track):
        if self.isScored(track) == True:
            c = self.conn.cursor()
            c.execute("""select score from scores where trackid = ? order by
                      scoreid desc""",
                      (track.getID(), ))
            result = c.fetchone()
            c.close()
            if result != None:
                return result[0]
            else:
                print "\'"+self.getPath(track)+"\' has no score associated with it in the library."
        elif self.isScored(track) == False:
            return self.defaultScore

    def getLastPlayed(self, track):
        c = self.conn.cursor()
        c.execute("""select datetime from plays where trackid = ? order by
                  playid desc""", (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None
        
    def getLastPlayedLocalTime(self, track):
        c = self.conn.cursor()
        c.execute("""select datetime(datetime, 'localtime') from plays where
                  trackid = ? order by playid desc""", (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None

    def getTimeSinceLastPlayed(self, track):
        c = self.conn.cursor()
        c.execute("""select datetime('now') - datetime from plays where
                  trackid = ? order by playid desc""", (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None

    def getArtist(self, track):
        c = self.conn.cursor()
        c.execute("select artist from tracks where trackid = ?",
                  (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None
##        return track.getArtist()

    def getAlbum(self, track):
        c = self.conn.cursor()
        c.execute("select album from tracks where trackid = ?",
                  (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None

    def getTitle(self, track):
        c = self.conn.cursor()
        c.execute("select title from tracks where trackid = ?",
                  (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None

    def getTrackNumber(self, track):
        c = self.conn.cursor()
        c.execute("select tracknumber from tracks where trackid = ?",
                  (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None

    def getPath(self, track):
        c = self.conn.cursor()
        c.execute("select path from tracks where trackid = ?",
                  (track.getID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None

    def getPathFromID(self, trackID):
        c = self.conn.cursor()
        c.execute("select path from tracks where trackid = ?",
                  (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return None
        

##data = Database()
