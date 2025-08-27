import sqlite3

def dump_schema(db_path="members.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print("=== Database Schema ===")
    c.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
    for name, sql in c.fetchall():
        print(f"\n-- {name} --")
        print(sql)

    conn.close()

if __name__ == "__main__":
    dump_schema()
