## Database Control

from NQr_Track import ID3Track
import mutagen
import os
import sqlite3

class Database:
    databasePath = "database"
    defaultScore = 10
    now = "datetime('now')"

    ## TODO: check if track table already exists first to confirm whether or not
    ##       to create other tables (poss corruption)
    def __init__(self):
        self.conn = sqlite3.connect(self.databasePath)        
        self.initCreateTrackTable()
        self.initCreatePlaysTable()
        self.initCreateScoresTable()
        self.conn.commit()

    def initCreateTrackTable(self):
        c = self.conn.cursor()
        try:
            c.execute("""create table tracks (trackid integer primary key
                                              autoincrement, path text,
                                              score integer, unscored
                                              integer)""")
            print "Tracks table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table tracks already exists":
                raise e
            print "Tracks table found."
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
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            if self.getTrackID(track.getPath()) == None:
                c.execute("insert into tracks values (null, ?, ?, 1)",
                          (track.getPath(), self.defaultScore))
                print "\'"+track.getPath()+"\' has been added to the library."
            else:
                print "\'"+track.getPath()+"\' is already in the library."
            c.close()
            self.conn.commit()

    def addDirectory(self, directory):
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = directory+'/'+contents[n]
            if os.path.isdir(path):
                self.addDirectory(path)
            else:
                self.addTrack(path)

    def removeTrack(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            if self.getTrackID(track.getPath()) != None:
                trackID = self.getTrackID(track.getPath())
                c.execute("delete from tracks where path = ? ",
                          (track.getPath(), ))
                c.execute("delete from plays where trackid = ?", (trackID, ))
                print "\'"+track.getPath()+"\' and associated plays have been removed from the library."
            else:
                print "\'"+track.getPath()+"\' is not in the library."
            c.close()
            self.conn.commit()

    def removeDirectory(self, directory):
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = directory+'/'+contents[n]
            if os.path.isdir(path):
                self.removeDirectory(path)
            else:
                self.removeTrack(path)

    ## poss add track if track not in library
    ## poss use (sqlite) datetime('now', 'localtime') for date 
    def addPlay(self, path, datetime):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            if self.getTrackID(track.getPath()) == None:
                print "\'"+track.getPath()+"\' is not in the library."
            else:
                trackID = self.getTrackID(track.getPath())
                c.execute("insert into plays values (null, ?, ?)", (trackID,
                                                                    datetime))
            c.close()
            self.conn.commit()
            
    ## poss add track if track not in library
    def setScore(self, path, score, datetime):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            if self.getTrackID(track.getPath()) == None:
                print "\'"+track.getPath()+"\' is not in the library."
            else:
                trackID = self.getTrackID(track.getPath())[0]
                c.execute("update tracks set score = ?, unscored = 0 where trackid = ?",
                          (score, trackID))
                c.execute("insert into scores values (null, ?, ?, ?)",
                          (trackID, score, datetime))
            c.close()
            self.conn.commit()

    ## poss should add a record to scores table
    def setUnscored(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            if self.getTrackID(track.getPath()) == None:
                print "\'"+track.getPath()+"\' is not in the library."
            else:
                trackID = self.getTrackID(track.getPath())[0]
                c.execute("update tracks set score = ?, unscored = 1 where trackid = ?",
                          (self.defaultScore, trackID))
##                c.execute("insert into scores values (null, ?, ?, ?)",
##                          (trackID, self.defaultScore, datetime))
            c.close()
            self.conn.commit()

    def getTrackID(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            c.execute("select trackid from tracks where path = ?",
                      (track.getPath(), ))
            result = c.fetchone()
            c.close()
            if result == None:
                return result
            else:
                return result[0]

    def getTrackDetails(self, path):
        track = ''
        try:
            track = ID3Track(path)
##            return True
        except mutagen.id3.ID3NoHeaderError as e:
            if path[0] != "\'":
                fullPath = "\'"+path+"\'"
            else:
                fullPath = path
            if str(e) != fullPath+" doesn't start with an ID3 tag":
                raise e
            print fullPath+" does not have an ID3 tag."
##            try:
##                track.MP4Track(path)
            return False
        return track

    ## determines whether user has changed score for this track
    def isScored(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            c.execute("select unscored from tracks where path = ?",
                      (track.getPath(), ))
            result = c.fetchone()
            c.close()
            if result[0] == 1:
                return False
            elif result[0] == 0:
                return True

    def getScore(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            if self.isScored(path) == True:
                c = self.conn.cursor()
                c.execute("select score from tracks where path = ?",
                          (track.getPath(), ))
                result = c.fetchone()
                c.close()
                if result != None:
                    return result[0]
                else:
                    print "\'"+track.getPath()+"\' has no score associated with it in the library."
            elif self.isScored(path) == False:
                return "None"

    def getScoreValue(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            c.execute("select score from tracks where path = ?",
                      (track.getPath(), ))
            result = c.fetchone()
            c.close()
            if result != None:
                return result[0]
            else:
                print "\'"+track.getPath()+"\' has no score associated with it in the library."
        
    def getLastPlayed(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            c = self.conn.cursor()
            trackID = self.getTrackID(track.getPath())
            c.execute("""select datetime from plays where trackid = ? order by
                      playid desc""", (trackID, ))
            result = c.fetchone()
            c.close()
            if result != None:
                return result[0]
            else:
                return False

    def getArtist(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            return track.getArtist()

    def getAlbum(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            return track.getAlbum()

    def getTitle(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            return track.getTitle()

    def getPath(self, path):
        track = self.getTrackDetails(path)
        if track != False:
            return track.getPath()

data = Database()
