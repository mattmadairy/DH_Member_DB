import sqlite3

# Path to your database file
DB_FILE = "members.db"

def drop_tables():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        # Drop the tables if they exist
        cursor.execute("DROP TABLE IF EXISTS work_hours_old;")
        cursor.execute("DROP TABLE IF EXISTS expected_dues;")

        conn.commit()
        print("Tables 'work_hours_old' and 'expected_dues' dropped (if they existed).")

    except sqlite3.Error as e:
        print("An error occurred:", e)

    finally:
        conn.close()

if __name__ == "__main__":
    drop_tables()
