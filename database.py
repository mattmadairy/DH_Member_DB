import sqlite3
from datetime import datetime
from contextlib import closing

DB_NAME = "members.db"

conn = None


def get_connection():
    return sqlite3.connect(DB_NAME)

def connect_db():
    global conn
    if conn is None:
        conn = sqlite3.connect("members.db")  # Make sure to replace with your database path
    return conn 

def get_db_connection():
    conn = sqlite3.connect('members.db')  # or use your database connection settings
    return conn

# ------------------ Initialization ----------------- #
def init_members_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
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
            zip TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_internal TEXT,
            card_external TEXT,
            deleted INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def init_dues_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            amount REAL,
            payment_date TEXT,
            year TEXT DEFAULT (strftime('%Y','now')),
            method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def init_settings_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    defaults = {
        "dues_probationary": "150",
        "dues_associate": "300",
        "dues_active": "150",
        "dues_life": "0",
        "default_year": str(datetime.now().year),
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()

def init_work_hours_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS work_hours (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            hours REAL NOT NULL,
            work_type TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def init_meeting_attendance_table():
    conn = get_connection()
    c = conn.cursor()
    # Updated to use "status" instead of "attended"
    c.execute("""
        CREATE TABLE IF NOT EXISTS meeting_attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            meeting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Attended','Exemption Approved')),
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

def init_deleted_members_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS deleted_members (
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
            zip TEXT,
            join_date TEXT,
            email2 TEXT,
            sponsor TEXT,
            card_internal TEXT,
            card_external TEXT,
            deleted_at TEXT
        )
    """)
    conn.commit()
    conn.close()

# Initialize all tables
try:
    init_members_table()
    init_dues_table()
    init_settings_table()
    init_work_hours_table()
    init_meeting_attendance_table()
    init_deleted_members_table()
except Exception as e:
    print("⚠️ Failed to initialize tables:", e)

# ------------------ Settings ----------------- #
def get_setting(key):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else None



def set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_all_settings():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {k: v for k, v in rows}

# In database.py

def get_default_year():
    return int(get_setting("default_year") or datetime.now().year)


# ------------------ Members ----------------- #
def add_member(data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip,
            join_date, email2, sponsor, card_internal, card_external
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()
    member_id = c.lastrowid
    conn.close()
    return member_id

def update_member(member_id, data):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members SET
            badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?,
            email=?, phone=?, address=?, city=?, state=?, zip=?,
            join_date=?, email2=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, data + (member_id,))
    conn.commit()
    conn.close()

# --- Member updates used by member_form.py ---
def update_member_basic(member_id, first_name, last_name, dob):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members SET first_name=?, last_name=?, dob=? WHERE id=?
    """, (first_name, last_name, dob, member_id))
    conn.commit()
    conn.close()

def update_member_contact(member_id, email, email2, phone, address, city, state, zip_code):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members
        SET email=?, email2=?, phone=?, address=?, city=?, state=?, zip=?
        WHERE id=?
    """, (email, email2, phone, address, city, state, zip_code, member_id))
    conn.commit()
    conn.close()

def update_member_membership(member_id, badge_number, membership_type, join_date, sponsor, card_internal, card_external):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members
        SET badge_number=?, membership_type=?, join_date=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, (badge_number, membership_type, join_date, sponsor, card_internal, card_external, member_id))
    conn.commit()
    conn.close()

def delete_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def soft_delete_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted=1 WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def restore_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted=0 WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def get_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_all_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted=0")
    rows = c.fetchall()
    conn.close()
    return rows

def get_deleted_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted=1")
    rows = c.fetchall()
    conn.close()
    return rows

# ------------------ Dues ----------------- #
def add_dues_payment(member_id, amount, payment_date, method=None, notes=None, year=None):
    if not year:
        year = get_default_year()
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO dues (member_id, amount, payment_date, year, method, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (member_id, amount, payment_date, str(year), method, notes))
    conn.commit()
    conn.close()

def get_dues_by_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM dues WHERE member_id=? ORDER BY payment_date DESC", (member_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def update_dues_payment(payment_id, amount=None, payment_date=None, method=None, notes=None, year=None):
    conn = get_connection()
    c = conn.cursor()
    updates = []
    params = []
    if amount is not None: updates.append("amount=?"); params.append(amount)
    if payment_date is not None: updates.append("payment_date=?"); params.append(payment_date)
    if method is not None: updates.append("method=?"); params.append(method)
    if notes is not None: updates.append("notes=?"); params.append(notes)
    if year is not None: updates.append("year=?"); params.append(year)
    params.append(payment_id)
    c.execute(f"UPDATE dues SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    conn.close()

def delete_dues_payment(payment_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM dues WHERE id=?", (payment_id,))
    conn.commit()
    conn.close()

# ------------------ Work Hours ----------------- #
def add_work_hours(member_id, date, hours, activity=None, notes=None):
    conn = get_connection()
    c = conn.cursor()
    # Ensure hours is float, even if text is passed
    c.execute("""
        INSERT INTO work_hours (member_id, date, hours, activity, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (member_id, date, float(hours), activity, notes))
    conn.commit()
    conn.close()


def get_work_hours_by_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM work_hours WHERE member_id=? ORDER BY date DESC", (member_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_work_hours_by_id(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM work_hours WHERE id=?", (entry_id,))
    row = c.fetchone()
    conn.close()
    return row

# Database function to fetch work types

def get_work_types():
    conn = get_db_connection()
    query = "SELECT DISTINCT work_type FROM work_hours"  # Assuming work_type is the field name
    cursor = conn.cursor()
    cursor.execute(query)
    work_types = [row[0] for row in cursor.fetchall()]
    conn.close()
    return work_types

def update_work_hours(entry_id, date=None, activity=None, hours=None, notes=None):
    conn = get_connection()
    c = conn.cursor()
    updates = []
    params = []
    if date is not None: updates.append("date=?"); params.append(date)
    if activity is not None: updates.append("activity=?"); params.append(activity)
    if hours is not None: updates.append("hours=?"); params.append(float(hours))
    if notes is not None: updates.append("notes=?"); params.append(notes)
    params.append(entry_id)
    c.execute(f"UPDATE work_hours SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    conn.close()


def delete_work_hours(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM work_hours WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

# ------------------ Meeting Attendance ----------------- #
def add_meeting_attendance(member_id, meeting_date, status, notes=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO meeting_attendance (member_id, meeting_date, status, notes)
        VALUES (?, ?, ?, ?)
    """, (member_id, meeting_date, status, notes))
    conn.commit()
    conn.close()

def get_meeting_attendance(member_id=None):
    conn = get_connection()
    c = conn.cursor()
    if member_id:
        c.execute("SELECT * FROM meeting_attendance WHERE member_id=? ORDER BY meeting_date DESC", (member_id,))
    else:
        c.execute("SELECT * FROM meeting_attendance ORDER BY meeting_date DESC")
    rows = c.fetchall()
    conn.close()
    return rows

# in database.py
def get_attendance_summary(year=None, month=None):
    import sqlite3
    conn = sqlite3.connect("members.db")
    c = conn.cursor()

    query = """
        SELECT m.badge_number, m.first_name, m.last_name,
               COUNT(a.meeting_id) as total_attended
        FROM members m
        LEFT JOIN meeting_attendance a ON m.id = a.member_id
        LEFT JOIN meetings mt ON a.meeting_id = mt.id
        WHERE 1=1
    """
    params = []

    if year:
        query += " AND strftime('%Y', mt.date) = ?"
        params.append(str(year))
    if month:
        query += " AND strftime('%m', mt.date) = ?"
        params.append(f"{int(month):02d}")

    query += " GROUP BY m.id ORDER BY m.last_name, m.first_name"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return [(badge, first, last, attended, attended) for badge, first, last, attended in rows]

    """
    Returns: (badge, first, last, attended_count, total_meetings)
    """
    conn = get_connection()
    c = conn.cursor()

    # Build dynamic filtering for year/month
    filters = []
    params = []

    if year:
        filters.append("strftime('%Y', meetings.date) = ?")
        params.append(str(year))
    if month:
        filters.append("strftime('%m', meetings.date) = ?")
        params.append(str(month).zfill(2))

    filter_sql = " AND " + " AND ".join(filters) if filters else ""

    query = f"""
        SELECT m.badge_number, m.first_name, m.last_name,
               COUNT(a.id) as attended,
               (SELECT COUNT(*) FROM meetings
                WHERE 1=1 {filter_sql}
               ) as total_meetings
        FROM members m
        LEFT JOIN attendance a ON a.member_id = m.id
        LEFT JOIN meetings ON a.meeting_id = meetings.id
        WHERE m.deleted = 0
        GROUP BY m.id
        ORDER BY m.last_name, m.first_name
    """
    c.execute(query, params*2)  # used for both COUNT and subquery
    rows = c.fetchall()
    conn.close()
    return rows
def get_member_attendance_status_all_months(member_id, year):
    """
    Returns a list of all status entries for the given member in the specified year.
    """
    query = """
        SELECT status 
        FROM meeting_attendance
        WHERE member_id = ?
          AND strftime('%Y', meeting_date) = ?
        ORDER BY meeting_date
    """
    with closing(get_connection()) as conn, conn:
        cur = conn.cursor()
        cur.execute(query, (member_id, str(year)))
        rows = cur.fetchall()
        return [row[0] for row in rows] if rows else ["No records"]


def get_member_attendance_status_by_month(member_id, year, month_name):
    """
    Returns a list of status entries for a given member in the specified month and year.
    month_name should be full English month name, e.g., 'January'.
    """
    month_number = {
        "January": "01", "February": "02", "March": "03", "April": "04",
        "May": "05", "June": "06", "July": "07", "August": "08",
        "September": "09", "October": "10", "November": "11", "December": "12"
    }.get(month_name, "01")  # default to Jan if not found

    query = """
        SELECT status
        FROM meeting_attendance
        WHERE member_id = ?
          AND strftime('%Y', meeting_date) = ?
          AND strftime('%m', meeting_date) = ?
        ORDER BY meeting_date
    """
    with closing(get_connection()) as conn, conn:
        cur = conn.cursor()
        cur.execute(query, (member_id, str(year), month_number))
        rows = cur.fetchall()
        return [row[0] for row in rows] if rows else ["No records"]
    
def count_member_attendance(member_id, year):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*)
            FROM meeting_attendance
            WHERE member_id = ?
              AND strftime('%Y', meeting_date) = ?
              AND status IN ('Attended','Exempted')
        """, (member_id, str(year)))
        result = cursor.fetchone()
        return result[0] if result else 0
    finally:
        conn.close()

# ------------------------------
# Count total meetings attended or exempted for a member in a given year
# ------------------------------
def count_member_attendance_year(member_id, year):
    """
    Return total number of meetings a member attended or was exempted for in a given year.
    """
    query = """
    SELECT COUNT(*) 
    FROM meeting_attendance
    WHERE member_id = ?
      AND strftime('%Y', meeting_date) = ?
      AND status IN ('attended', 'exempted')
    """
    with closing(get_connection()) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute(query, (member_id, str(year)))
        result = cur.fetchone()
        return result[0] if result else 0

# ------------------------------
# Get attendance status for a member in a specific year and month
# ------------------------------
def get_member_attendance_status(member_id, year, month):
    """
    Return the status for a member for a specific month/year.
    If multiple entries exist, returns a comma-separated string of statuses.
    Returns None if no records exist for that month.
    """
    query = """
    SELECT status
    FROM meeting_attendance
    WHERE member_id = ?
      AND strftime('%Y', meeting_date) = ?
      AND strftime('%m', meeting_date) = ?
    """
    with closing(get_connection()) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute(query, (member_id, str(year), f"{int(month):02d}"))
        rows = cur.fetchall()
        if not rows:
            return None
        # Combine multiple statuses in one string if needed
        statuses = [r[0] for r in rows]
        return ", ".join(statuses)

def get_member_status_for_month(member_id, year, month):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT status
            FROM meeting_attendance
            WHERE member_id = ?
              AND strftime('%Y', meeting_date) = ?
              AND strftime('%m', meeting_date) = ?
            LIMIT 1
        """, (member_id, str(year), f"{month:02d}"))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()


def update_meeting_attendance(entry_id, meeting_date=None, status=None, notes=None):
    conn = get_connection()
    c = conn.cursor()
    updates = []
    params = []
    if meeting_date is not None: updates.append("meeting_date=?"); params.append(meeting_date)
    if status is not None: updates.append("status=?"); params.append(status)
    if notes is not None: updates.append("notes=?"); params.append(notes)
    params.append(entry_id)
    c.execute(f"UPDATE meeting_attendance SET {', '.join(updates)} WHERE id=?", params)
    conn.commit()
    conn.close()

def delete_meeting_attendance(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM meeting_attendance WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()
