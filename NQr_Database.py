## Database Control

import os
from NQr_Track import ID3Track
import mutagen
import sqlite3

class Database:
    databasePath = "database"
    defaultScore = 10

    ## TODO: check if track table already exists first to confirm whether or not
    ##       to create other tables (poss corruption)
    def __init__(self):
        self.conn = sqlite3.connect(self.databasePath)
##        c = self.conn.cursor()
        
        self.initCreateTrackTable()
        self.initCreatePlaysTable()
        self.conn.commit()

    ## poss add boolean unplayed? to table
    def initCreateTrackTable(self):
        c = self.conn.cursor()
        try:
            c.execute("""create table tracks (trackid integer primary key
                                              autoincrement, path text,
                                              score integer)""")
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
                                              date text)""")
            print "Plays table created."
        except sqlite3.OperationalError as e:
            if str(e) != "table plays already exists":
                raise e
            print "Plays table found."
        c.close()

    def addTrack(self, path):
        c = self.conn.cursor()
        try:
            track = ID3Track(path)
        except mutagen.id3.ID3NoHeaderError as e:
            if path[0] != "\'":
                fullPath = "\'"+path+"\'"
            else:
                fullPath = path
            if str(e) != fullPath+" doesn't start with an ID3 tag":
                raise e
            print fullPath+" does not have an ID3 tag."
            return
        if self.getTrack(track.getPath()) == None:
            c.execute("insert into tracks values (null, ?, ?)",
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

    def getTrack(self, path):
        c = self.conn.cursor()
        c.execute("select path from tracks where path = ?", (path, ))
        result = c.fetchone()
        c.close()
        return result
        

db = Database()
