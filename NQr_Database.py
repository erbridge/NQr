## Database Control

import sqlite3
##from NQr_Track import Track

class Database:
    databasePath = "database"

    ## TODO: check if track table already exists first
    def __init__(self):
        self.conn = sqlite3.connect(self.databasePath)
##        c = self.conn.cursor()
        
        self.initCreateTrackTable()
        self.conn.commit()

    def initCreateTrackTable(self):
        c = self.conn.cursor()
        try:
            c.execute("""create table tracks (id integer primary key
                                              autoincrement, path text)""")
        except sqlite3.OperationalError as e:
            if str(e) != "table tracks already exists":
                raise e
            print "Tracks table already exists"
        c.close()

##    def addTrack(self, track):
##        c = self.conn.cursor()
##        c.execute("insert into tracks values (\"?\")", Track.getPath(track))
##        c.close()

db = Database()
