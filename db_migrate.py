import sqlite3

def create_committees_table(db_path="members.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committees (
        committee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL UNIQUE,
        executive_committee TEXT,
        membership TEXT,
        trap TEXT,
        still_target TEXT,
        gun_bingo_social_events TEXT,
        rifle TEXT,
        pistol TEXT,
        archery TEXT,
        building_and_grounds TEXT,
        hunting TEXT,
        FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Committees table created (if it did not exist already).")

if __name__ == "__main__":
    create_committees_table()
