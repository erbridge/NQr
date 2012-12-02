#!/usr/local/bin/python

# export stuff in a format suitable for Munin.

import os
import sqlite3
import sys

def scored(cursor, score):
    cursor.execute("""select count(trackid) from tracks
                      where score=""" + str(score))
    results = cursor.fetchall()
    return results[0][0]

def unscored(cursor):
    cursor.execute("select count(trackid) from tracks where score is null")
    results = cursor.fetchall()
    return results[0][0]

def total(cursor):
    cursor.execute("select count(trackid) from tracks")
    results = cursor.fetchall()
    return results[0][0]

def config():
    print 'graph_title NQr'
    print 'total.label Total tracks'
    print 'unscored.label Unscored'
    for n in range(5, 11):
        print 'score_' + str(n) + '.label ' + str(n)

def values(conn):
    cursor = conn.cursor()
    print 'total.value ' + str(total(cursor))
    print 'unscored.value ' + str(unscored(cursor))
    for n in range(5, 11):
        print 'score_' + str(n) + '.value ' + str(scored(cursor, n))
    

def main():
    path = os.environ['NQR_PATH']
    conn = sqlite3.connect(path + "/database")

    if len(sys.argv) == 1:
        values(conn)
    elif sys.argv[1] == 'config':
        config()

if __name__ == '__main__':
    main()
