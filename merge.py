import sqlite3

conn = sqlite3.connect("members.db")
cur = conn.cursor()

cur.execute("PRAGMA table_info(members)")
for col in cur.fetchall():
    print(col)

conn.close()
