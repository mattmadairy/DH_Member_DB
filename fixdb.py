import sqlite3

DB_PATH = "members.db"  # <-- change this to your actual DB path

def convert_waiver_column():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Update all 0s to "No"
    c.execute("""
        UPDATE members
        SET waiver = 'No'
        WHERE waiver = 0
    """)
    
    # Optional: Update all 1s to "Yes" to normalize
    c.execute("""
        UPDATE members
        SET waiver = 'Yes'
        WHERE waiver = 1
    """)
    
    conn.commit()
    conn.close()
    print("Waiver column conversion complete.")

if __name__ == "__main__":
    convert_waiver_column()
