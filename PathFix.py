# Convert paths to realpaths, deal with duplicates...
# One-off, should not be needed in future.
# you may want to create index t3 on tracks(path); first

import os
import sqlite3

def main():
    conn = sqlite3.connect("database")
    cursor = conn.cursor()
    cursor.execute("select trackid, path from tracks")
    results = cursor.fetchall()
    for result in results:
        real = os.path.realpath(result[1])
        if real != result[1]:
            print result[1], "->", real
            cursor.execute("update tracks set path = ? where trackid = ?",
                           (real, result[0]))
    conn.commit()
    cursor.execute("""select trackid, tracks.path
                      from tracks,
                           (select path
                            from (select count(path) as c, path
                                  from tracks group by path)
                            where c > 1)
                       as s where tracks.path = s.path""")
    results = cursor.fetchall()
    dupes = dict()
    for result in results:
        if result[1] not in dupes:
            dupes[result[1]] = [result[0]]
        else:
            dupes[result[1]].append(result[0])
    for path in dupes:
        print path, dupes[path]
        trackid = dupes[path][0]
        cursor.execute("delete from enqueues where trackid = ?", (trackid, ))
        cursor.execute("delete from ignore where trackid = ?", (trackid, ))
        cursor.execute("delete from plays where trackid = ?", (trackid, ))
        cursor.execute("delete from tags where trackid = ?", (trackid, ))
        cursor.execute("delete from tracks where trackid = ?", (trackid, ))
    conn.commit()

if __name__ == '__main__':
    main()
