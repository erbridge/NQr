#!/usr/local/bin/python

# export stuff in a format suitable for MRTG.

import os
import sqlite3
import sys

def scored(cursor, score):
    cursor.execute("""select count(trackid) from tracks
                      where score=""" + score)

def unscored(cursor):
    cursor.execute("select count(trackid) from tracks where score is null")

def total(cursor):
    cursor.execute("select count(trackid) from tracks")

def stat(conn, score):
    cursor = conn.cursor()
    if score == 't':
        total(cursor)
    elif score == 'u':
        unscored(cursor)
    else:
        scored(cursor, score)
    results = cursor.fetchall()
    for result in results:
        print result[0]
    

def main():
    path = os.path.dirname(sys.argv[0])
    conn = sqlite3.connect(path + "/database")

    stat(conn, sys.argv[1])
    stat(conn, sys.argv[2])
    
    # Fake uptime
    print "12:34"
    print "nqr"

if __name__ == '__main__':
    main()
