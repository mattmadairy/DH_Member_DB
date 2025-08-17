# reset_db.py
import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "members.db")

def reset_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Drop existing tables
    cur.execute("DROP TABLE IF EXISTS members")
    cur.execute("DROP TABLE IF EXISTS deleted_members")

    # Recreate schema
    cur.execute("""
        CREATE TABLE members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            badge_number TEXT,
            membership_type TEXT,
            first_name TEXT,
            last_name TEXT,
            dob TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_internal TEXT,
            card_external TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE deleted_members (
            id INTEGER PRIMARY KEY,
            badge_number TEXT,
            membership_type TEXT,
            first_name TEXT,
            last_name TEXT,
            dob TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip_code TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_internal TEXT,
            card_external TEXT,
            deleted_at TEXT
        )
    """)

    # Insert test data
    test_members = [
        ("1001", "Probationary", "John", "Doe", "1990-01-01", "john@example.com", "555-1234", "123 Main St", "Huntsville", "AL", "35801", "2023-01-15", "", "Sponsor A", "1111", "2222"),
        ("1002", "Associate", "Jane", "Smith", "1985-05-20", "jane@example.com", "555-5678", "456 Oak St", "Madison", "AL", "35758", "2022-06-10", "", "Sponsor B", "3333", "4444"),
        ("1003", "Active", "Mike", "Johnson", "1978-09-12", "mike@example.com", "555-8765", "789 Pine St", "Decatur", "AL", "35601", "2021-03-05", "", "Sponsor C", "5555", "6666"),
    ]

    cur.executemany("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip_code, join_date,
            email2, sponsor, card_internal, card_external
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, test_members)

    # Add one test deleted member
    deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO deleted_members (
            id, badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip_code, join_date,
            email2, sponsor, card_internal, card_external, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        9999, "9999", "Active", "Deleted", "Member", "1980-12-12", "del@example.com",
        "555-0000", "999 Nowhere", "Athens", "AL", "35611", "2020-02-02",
        "", "Sponsor X", "7777", "8888", deleted_at
    ))

    conn.commit()
    conn.close()
    print("✅ Database reset and test data inserted.")


if __name__ == "__main__":
    reset_db()
