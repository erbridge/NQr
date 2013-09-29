import sqlite3


def rebase(oldBase, newBase):
    conn = sqlite3.connect("database.tmp")
    cursor = conn.cursor()
    cursor.execute("select trackid, path from tracks")
    results = cursor.fetchall()
    for result in results:
        id = result[0]
        path = result[1]
        print path + "      ->      ",
        parts = path.split(oldBase, 1)
        if len(parts) == 2:
            newPath = newBase + parts[1]
            cursor.execute("update tracks set path = ? where trackid = ?",
                           (newPath, id))
            conn.commit()
            print newPath
        else:
            print path


if __name__ == '__main__':
    rebase("C:\\Users\\Felix\\","C:\\Users\\Felix\\")