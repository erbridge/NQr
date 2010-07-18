## Database Control
## TODO: add artist album etc. to tracks table and make them update with changes
##       and make get* calls find in the database
## TODO: remove score from tracks table and use scores table to find latest
##       score

import mutagen
from Track import ID3Track
import Track
import os
import sqlite3

class Database:
    databasePath = "database"
    defaultScore = 10

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
        track = Track.getTrackFromPathNoID(self, path)
        if track != None:
            c = self.conn.cursor()
            trackID = self.getTrackID(track)
            if trackID == None:
                c.execute("""insert into tracks (path, score, unscored) values
                          (?, ?, 1)""", (track.getPath(), self.defaultScore))
                trackID = c.lastrowid
                print "\'"+track.getPath()+"\' has been added to the library."
            else:
                print "\'"+track.getPath()+"\' is already in the library."                
            c.close()
            self.conn.commit()
            track.setID(trackID)
        else:
            print "Invalid file."

    def addDirectory(self, directory):
        contents = os.listdir(directory)
        for n in range(0, len(contents)):
            path = directory+'/'+contents[n]
            if os.path.isdir(path):
                self.addDirectory(path)
            else:
                self.addTrack(path)

##    def removeTrack(self, path):
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

##    def removeDirectory(self, directory):
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
        trackID = self.getTrackID(track)
        if trackID == None:
            print "\'"+track.getPath()+"\' is not in the library."
        else:
            c.execute("""insert into plays (trackid, datetime) values
                      (?, datetime('now'))""", (trackID, ))
        c.close()
        self.conn.commit()
            
    ## poss add track if track not in library
    def setScore(self, track, score):
        c = self.conn.cursor()
        trackID = self.getTrackID(track)
        if trackID == None:
            print "\'"+track.getPath()+"\' is not in the library."
        else:
            c.execute("update tracks set score = ?, unscored = 0 where trackid = ?",
                      (score, trackID))
            c.execute("""insert into scores (trackid, score, datetime) values
                      (?, ?, datetime('now'))""", (trackID, score, ))
        c.close()
        self.conn.commit()

    ## poss should add a record to scores table
    def setUnscored(self, track):
        c = self.conn.cursor()
        trackID = self.getTrackID(track)
        if trackID == None:
            print "\'"+track.getPath()+"\' is not in the library."
        else:
            c.execute("update tracks set score = ?, unscored = 1 where trackid = ?",
                      (self.defaultScore, trackID))
##                c.execute("""insert into scores (trackid, score, datetime)
##                          values (?, ?, datetime('now'))""",
##                          (trackID, self.defaultScore, ))
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
        trackID = self.getTrackID(track)
        c.execute("select unscored from tracks where trackid = ?",
                  (trackID, ))
        result = c.fetchone()
        c.close()
        if result[0] == 1:
            return False
        elif result[0] == 0:
            return True

    def getScore(self, track):
        if self.isScored(track) == True:
            c = self.conn.cursor()
            trackID = self.getTrackID(track)
            c.execute("select score from tracks where trackid = ?",
                      (trackID, ))
            result = c.fetchone()
            c.close()
            if result != None:
                return result[0]
            else:
                print "\'"+track.getPath()+"\' has no score associated with it in the library."
        elif self.isScored(track) == False:
            return "None"

    def getScoreValue(self, track):
        c = self.conn.cursor()
        trackID = self.getTrackID(track)
        c.execute("select score from tracks where trackid = ?",
                  (trackID(), ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            print "\'"+track.getPath()+"\' has no score associated with it in the library."
        
    def getLastPlayed(self, track):
        c = self.conn.cursor()
        trackID = self.getTrackID(track)
        c.execute("""select datetime from plays where trackid = ? order by
                  playid desc""", (trackID, ))
        result = c.fetchone()
        c.close()
        if result != None:
            return result[0]
        else:
            return False

    def getArtist(self, track):
        return track.getArtist()

    def getAlbum(self, track):
        if track != False:
            return track.getAlbum()

    def getTitle(self, track):
        if track != False:
            return track.getTitle()

    def getPath(self, track):
        return track.getPath()

    def getPathFromID(self, trackID):
        c = self.conn.cursor()
        c.execute("select path from tracks where trackid = ?",
                  (trackID, ))
        result = c.fetchone()
        c.close()
        if result == None:
            return result
        else:
            return result[0]
        

data = Database()
