import sqlite3

conn = sqlite3.connect("members.db")
c = conn.cursor()
c.execute("PRAGMA table_info(members)")
for col in c.fetchall():
    print(col)
conn.close()

