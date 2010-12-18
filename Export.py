import sqlite3

def main():
    conn = sqlite3.connect("database")
    cursor = conn.cursor()
    # I claim this gives the current score. Another formulation is
    # select trackid, score, max(scoreid) from scores group by trackid;
#    cursor.execute("""select trackid, score from scores
#                      group by trackid order by scoreid""")
#    cursor.execute("""select scores.trackid, score, path from scores, tracks
#                      where scores.trackid = tracks.trackid
#                      group by scores.trackid order by scoreid""")
    cursor.execute("""select score, path from tracks
                      where score is not null""")
    results = cursor.fetchall()
    for result in results:
        print str(result[0]) + "\t" + result[1]

if __name__ == '__main__':
    main()
