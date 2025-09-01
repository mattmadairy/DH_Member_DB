import sqlite3
from datetime import datetime
from contextlib import closing
import calendar

DB_NAME = "members.db"

conn = None

def get_connection():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row  # ← allows access by column name
        return conn
    except sqlite3.Error as e:
        print(f"Connection error: {e}")
        return None

    
# ------------------ Initialization ----------------- #
def init_members_table():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS members (
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
            phone2 TEXT,
            waiver TEXT DEFAULT 'No',
            deleted_at TEXT
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
            phone2 TEXT,
            waiver TEXT DEFAULT 'No',
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
    conn = get_connection()
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

def update_member_membership(member_id, badge_number, membership_type, join_date,
                             sponsor, card_internal, card_external, phone2="", waiver="No"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members
        SET badge_number=?,
            membership_type=?,
            join_date=?,
            sponsor=?,
            card_internal=?,
            card_external=?,
            phone2=?,
            waiver=?
        WHERE id=?
    """, (badge_number, membership_type, join_date, sponsor, card_internal,
          card_external, phone2, waiver, member_id))
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
    
def delete_member_permanently(member_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()


def permanently_delete_member_by_id(member_id):
    conn = sqlite3.connect("members.db")
    c = conn.cursor()
    try:
        # Get member data from recycle_bin
        c.execute("SELECT * FROM recycle_bin WHERE id=?", (member_id,))
        member = c.fetchone()
        if not member:
            return  # nothing to delete

        # Insert into deleted_members table for logging
        c.execute("""
            INSERT INTO deleted_members (
                id, badge, membership_type, first_name, last_name,
                date_of_birth, email_address, email_address_2, phone_number,
                address, city, state, zip_code, join_date, sponsor,
                card_fob_internal, card_fob_external, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, member + (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

        # Delete from recycle_bin
        c.execute("DELETE FROM recycle_bin WHERE id=?", (member_id,))
        conn.commit()
    finally:
        conn.close()


def log_and_delete_member(recycle_id, db_path="members.db"):
    """
    Logs a permanently deleted member into deleted_members,
    then removes them from recycle_bin.
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        # 1. Look up recycle_bin row by recycle_id
        c.execute("SELECT badge FROM recycle_bin WHERE id=?", (recycle_id,))
        row = c.fetchone()
        if not row:
            print(f"Recycle bin entry {recycle_id} not found")
            return
        badge_number = row[0]

        # 2. Fetch full member details from members by badge_number
        c.execute("""
            SELECT id, badge_number, membership_type, first_name, last_name,
                   dob, email, phone, address, city, state, zip, join_date,
                   email2, sponsor, card_internal, card_external
            FROM members WHERE badge_number=?
        """, (badge_number,))
        member = c.fetchone()
        if not member:
            print(f"No full record found in members for badge {badge_number}")
            return

        # 3. Insert into deleted_members with deleted_at timestamp
        c.execute("""
            INSERT INTO deleted_members (
                id, badge_number, membership_type, first_name, last_name,
                dob, email, phone, address, city, state, zip_code, join_date,
                email2, sponsor, card_internal, card_external, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, member + (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

        # 4. Delete the recycle_bin row itself
        c.execute("DELETE FROM recycle_bin WHERE id=?", (recycle_id,))
        conn.commit()
        print(f"Member with badge {badge_number} permanently deleted and logged.")
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_recycle_bin_members(db_path="members.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT id, first, last, membership_type, badge FROM recycle_bin")
    rows = c.fetchall()
    conn.close()
    return rows

def restore_member_from_recycle_bin(recycle_id, db_path="members.db"):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # First, check recycle_bin for basic info
    c.execute("SELECT badge, membership_type, first, last FROM recycle_bin WHERE id=?", (recycle_id,))
    recycle_row = c.fetchone()
    if not recycle_row:
        conn.close()
        raise ValueError(f"Recycle bin entry {recycle_id} not found")
    badge, membership_type, first, last = recycle_row

    # Next, try to get full info from deleted_members (if available)
    c.execute("SELECT * FROM deleted_members WHERE badge_number=?", (badge,))
    deleted_row = c.fetchone()

    if deleted_row:
        # Deleted_members schema:
        # (id, badge_number, membership_type, first_name, last_name, dob, email, phone, address,
        #  city, state, zip_code, join_date, email2, sponsor, card_internal, card_external, deleted_at)

        (_, badge_number, mtype, fname, lname, dob, email, phone, address,
         city, state, zip_code, join_date, email2, sponsor,
         card_internal, card_external, _) = deleted_row

        # Restore full member
        c.execute("""
            INSERT INTO members (
                badge_number, membership_type, first_name, last_name,
                dob, email, phone, address, city, state, zip, join_date,
                email2, sponsor, card_internal, card_external, deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            badge_number, mtype, fname, lname, dob, email, phone, address,
            city, state, zip_code, join_date, email2, sponsor, card_internal, card_external
        ))

    else:
        # Fallback: restore minimal data
        c.execute("""
            INSERT INTO members (badge_number, membership_type, first_name, last_name, deleted)
            VALUES (?, ?, ?, ?, 0)
        """, (badge, membership_type, first, last))

    # Remove from recycle_bin
    c.execute("DELETE FROM recycle_bin WHERE id=?", (recycle_id,))
    conn.commit()
    conn.close()



def restore_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted=0 WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def restore_member_by_id(member_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE members SET deleted=0 WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def get_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (member_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_member_by_badge(badge):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE badge_number=?", (badge,))
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
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM members WHERE deleted=1")  # assumes a 'deleted' flag
    rows = cursor.fetchall()
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


def get_dues_by_member(member_id, year=None):
    """
    Fetch dues for a specific member.
    If year is provided, only return dues for that year.
    """
    
    conn = get_connection()
    cur = conn.cursor()
    
    if year:
        cur.execute("""
            SELECT * FROM dues 
            WHERE member_id = ? AND year = ?
            ORDER BY payment_date ASC
        """, (member_id, str(year)))
    else:
        cur.execute("""
            SELECT * FROM dues 
            WHERE member_id = ?
            ORDER BY payment_date ASC
        """, (member_id,))
    
    results = cur.fetchall()
    conn.close()
    return results

def get_dues_report(member_id=None, year=None, month=None):
    """
    Return a list of dues summary per member with individual payments.
    Each row is: (member_id, badge_number, membership_type, first_name, last_name,
                   total_due, payment_date, amount_paid, method)
    Filters by optional member_id, year, and month.
    """
    conn = get_connection()
    c = conn.cursor()

    query = """
        SELECT m.id, m.badge_number, m.membership_type, m.first_name, m.last_name,
               d.amount as amount_due, d.payment_date, d.amount as amount_paid, d.method
        FROM members m
        LEFT JOIN dues d ON m.id = d.member_id
        WHERE m.deleted = 0
    """
    params = []

    if member_id:
        query += " AND m.id = ?"
        params.append(member_id)

    if year:
        query += " AND strftime('%Y', d.payment_date) = ?"
        params.append(str(year))

    if month and month != "All":
        month_index = list(calendar.month_name).index(month)
        query += " AND strftime('%m', d.payment_date) = ?"
        params.append(f"{month_index:02d}")

    query += " ORDER BY m.last_name, m.first_name, d.payment_date DESC"

    try:
        c.execute(query, params)
        rows = c.fetchall()
    except sqlite3.Error as e:
        print(f"Query execution error: {e}")
        rows = []

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


def get_work_hours_by_member(member_id, year=None):
    """
    Fetch work hours for a specific member.
    If year is provided, only return work hours for that year.
    """
    
    conn = get_connection()
    cur = conn.cursor()

    if year:
        cur.execute("""
            SELECT * FROM work_hours
            WHERE member_id = ? AND strftime('%Y', date) = ?
            ORDER BY date ASC
        """, (member_id, str(year)))
    else:
        cur.execute("""
            SELECT * FROM work_hours
            WHERE member_id = ?
            ORDER BY date ASC
        """, (member_id,))
    
    results = cur.fetchall()
    conn.close()
    return results


def get_work_hours_by_id(entry_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM work_hours WHERE id=?", (entry_id,))
    row = c.fetchone()
    conn.close()
    return row

# Database function to fetch work types

def get_work_types():
    conn = get_connection()
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

def get_meeting_attendance(member_id, year=None):
    """
    Fetch meeting attendance for a specific member.
    If year is provided, only return attendance records for that year.
    """
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        if year:
            cur.execute("""
                SELECT * FROM meeting_attendance
                WHERE member_id = ? AND strftime('%Y', meeting_date) = ?
                ORDER BY meeting_date ASC
            """, (member_id, str(year)))
        else:
            cur.execute("""
                SELECT * FROM meeting_attendance
                WHERE member_id = ?
                ORDER BY meeting_date ASC
            """, (member_id,))
        
        results = cur.fetchall()
        return results
    finally:
        conn.close()

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


# Using the standardized get_connection() in your report function
def get_work_hours_report(member_id=None, start_date=None, end_date=None, work_type=None):
    """
    Return a list of (badge_number, first_name, last_name, total_hours)
    for all members, optionally filtered by member_id, date range, and work type.
    """
    conn = get_connection()
    c = conn.cursor()

    query = """
        SELECT m.badge_number, m.first_name, m.last_name,
               IFNULL(SUM(w.hours), 0) as total_hours
        FROM members m
        LEFT JOIN work_hours w 
               ON m.id = w.member_id
    """

    # Collect join filters separately (so they apply to w, but don't kill the LEFT JOIN)
    join_filters = []
    params = []

    if start_date:
        join_filters.append("w.date >= ?")
        params.append(start_date)
    if end_date:
        join_filters.append("w.date <= ?")
        params.append(end_date)
    if work_type:
        join_filters.append("w.work_type = ?")
        params.append(work_type)

    if join_filters:
        query += " AND " + " AND ".join(join_filters)

    query += " WHERE m.deleted = 0"

    if member_id:
        query += " AND m.id = ?"
        params.append(member_id)

    query += " GROUP BY m.id ORDER BY m.last_name, m.first_name"

    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows
def get_member_work_hours_for_year(member_id, year):
    """
    Return the total hours a member has logged in the given year.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(hours), 0)
        FROM work_hours
        WHERE member_id = ?
          AND strftime('%Y', date) = ?
    """, (member_id, str(year)))
    total = cur.fetchone()[0]
    conn.close()
    return total


def get_member_work_hours_for_month(member_id, year, month):
    """
    Return the total hours a member has logged in the given year/month.
    `month` should be 1–12
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(hours), 0)
        FROM work_hours
        WHERE member_id = ?
          AND strftime('%Y', date) = ?
          AND strftime('%m', date) = ?
    """, (member_id, str(year), f"{month:02d}"))
    total = cur.fetchone()[0]
    conn.close()
    return total




def get_conn():
    return sqlite3.connect(DB_NAME)

# --- Helper: fetch a single member row (must be in recycle bin = deleted=1) ---
def _fetch_deleted_member(member_id, conn):
    c = conn.cursor()
    c.execute("""
        SELECT id, badge_number, membership_type, first_name, last_name,
               dob, email, phone, address, city, state, zip, join_date,
               email2, sponsor, card_internal, card_external, deleted
        FROM members
        WHERE id=? AND deleted=1
    """, (member_id,))
    return c.fetchone()

# --- Show in Recycle Bin UI (your TreeView uses this) ---
def get_deleted_members():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, badge_number, membership_type, first_name, last_name,
               dob, email, phone, address, city, state, zip, join_date,
               email2, sponsor, card_internal, card_external, deleted
        FROM members
        WHERE deleted=1
        ORDER BY last_name, first_name
    """)
    rows = c.fetchall()
    conn.close()
    return rows

# --- Soft delete: mark deleted=1 and (optionally) drop a simple crumb in recycle_bin ---
def soft_delete_member_by_id(member_id):
    with get_conn() as conn:
        c = conn.cursor()
        # Grab minimal info to mirror into recycle_bin (optional but helpful)
        c.execute("SELECT first_name, last_name, membership_type, badge_number FROM members WHERE id=?", (member_id,))
        row = c.fetchone()
        if not row:
            raise ValueError(f"Member {member_id} not found.")
        first, last, membership_type, badge = row

        # Mark as deleted
        c.execute("UPDATE members SET deleted=1 WHERE id=?", (member_id,))

        # Keep a light entry in recycle_bin (schema: id, first, last, membership_type, badge)
        try:
            c.execute("""
                INSERT INTO recycle_bin (first, last, membership_type, badge)
                VALUES (?, ?, ?, ?)
            """, (first or "", last or "", membership_type or "", int(badge) if str(badge).isdigit() else None))
        except Exception:
            # If recycle_bin insert fails due to badge type, ignore (UI reads from members.deleted anyway)
            pass

        # Optional audit
        try:
            c.execute("INSERT INTO deletion_log (member_id, action) VALUES (?, 'soft_delete')", (member_id,))
        except Exception:
            pass

# --- Restore from Recycle Bin (members.id) ---
def restore_member_by_id(member_id):
    with get_conn() as conn:
        c = conn.cursor()

        # Member must exist and be soft-deleted
        c.execute("SELECT badge_number FROM members WHERE id=? AND deleted=1", (member_id,))
        r = c.fetchone()
        if not r:
            raise ValueError(f"Member {member_id} is not in the recycle bin (or not found).")
        badge = r[0]

        # Flip the flag
        c.execute("UPDATE members SET deleted=0 WHERE id=?", (member_id,))

        # Clean up any recycle_bin rows that match this badge (best-effort)
        try:
            if badge is not None and str(badge).strip() != "":
                c.execute("DELETE FROM recycle_bin WHERE badge=?", (int(badge),))
        except Exception:
            # Badge might be non-numeric in your data; try textual match
            try:
                c.execute("DELETE FROM recycle_bin WHERE CAST(badge AS TEXT)=?", (str(badge),))
            except Exception:
                pass

        # Optional audit
        try:
            c.execute("INSERT INTO deletion_log (member_id, action) VALUES (?, 'restore')", (member_id,))
        except Exception:
            pass

# --- Permanently delete (members.id) and LOG FULL ROW into deleted_members ---
def permanently_delete_member_by_id(member_id):
    with get_conn() as conn:
        c = conn.cursor()

        # Must be in recycle bin (deleted=1)
        m = _fetch_deleted_member(member_id, conn)
        if not m:
            raise ValueError(f"Member {member_id} is not in the recycle bin or does not exist.")

        (mid, badge_number, membership_type, first_name, last_name,
         dob, email, phone, address, city, state, zip_code, join_date,
         email2, sponsor, card_internal, card_external, _deleted_flag) = m

        # 1) Write to deleted_members (note: schema uses zip_code)
        c.execute("""
            INSERT OR REPLACE INTO deleted_members (
                id, badge_number, membership_type, first_name, last_name,
                dob, email, phone, address, city, state, zip_code, join_date,
                email2, sponsor, card_internal, card_external, deleted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mid, badge_number, membership_type, first_name, last_name,
            dob, email, phone, address, city, state, zip_code, join_date,
            email2, sponsor, card_internal, card_external,
            datetime.now().isoformat(timespec="seconds")
        ))

        # 2) Remove from members
        c.execute("DELETE FROM members WHERE id=?", (member_id,))

        # 3) Clean up recycle_bin entries with same badge (best-effort)
        try:
            if badge_number is not None and str(badge_number).strip() != "":
                # Try numeric first
                c.execute("DELETE FROM recycle_bin WHERE badge=?", (int(badge_number),))
        except Exception:
            # Fallback textual compare
            try:
                c.execute("DELETE FROM recycle_bin WHERE CAST(badge AS TEXT)=?", (str(badge_number),))
            except Exception:
                pass

        # 4) Optional audit
        try:
            c.execute("INSERT INTO deletion_log (member_id, action) VALUES (?, 'permanent_delete')", (member_id,))
        except Exception:
            pass


def get_waiver_report():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = """
        SELECT badge_number, first_name || ' ' || last_name AS name, waiver
        FROM members
        ORDER BY badge_number
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

    
    # convert sqlite3.Row objects to dictionaries
    return [dict(row) for row in rows]


def update_member_role(member_id, position, term_start, term_end):
    """Insert or update the role for a member."""
    conn = get_connection()
    cursor = conn.cursor()

    # Check if a role already exists for this member
    cursor.execute("SELECT member_id FROM roles WHERE member_id = ?", (member_id,))
    existing = cursor.fetchone()

    if existing:
        # Update existing record
        cursor.execute("""
            UPDATE roles
            SET position = ?, term_start = ?, term_end = ?
            WHERE member_id = ?
        """, (position, term_start, term_end, member_id))
    else:
        # Insert new record
        cursor.execute("""
            INSERT INTO roles (member_id, position, term_start, term_end)
            VALUES (?, ?, ?, ?)
        """, (member_id, position, term_start, term_end))

    conn.commit()
    conn.close()


def get_member_role(member_id):
    """Return the role record for a member as a dictionary."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM roles WHERE member_id = ?", (member_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return dict(row)
    else:
        return None
    
    # Fetch the committees for a member
def get_member_committees(member_id):
    """
    Fetch a member's committee memberships as a dict.
    Returns a dict with column names as keys and values as stored (e.g., 'X' or '').
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get all committee column names from the table, excluding member_id
    cursor.execute("PRAGMA table_info(committees)")
    columns_info = cursor.fetchall()
    committee_columns = [col[1] for col in columns_info if col[1] != "member_id"]

    # Build query
    cols_quoted = ', '.join(f'"{col}"' for col in committee_columns)
    query = f'SELECT {cols_quoted} FROM committees WHERE member_id=?'
    cursor.execute(query, (member_id,))
    row = cursor.fetchone()

    if row:
        return dict(zip(committee_columns, row))
    else:
        # Return empty dict with all columns if member has no record
        return {col: "" for col in committee_columns}


def update_member_basic(member_id, first_name, last_name, dob):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET first_name = ?, last_name = ?, dob = ?
        WHERE id = ?
    """, (first_name, last_name, dob, member_id))
    conn.commit()
    conn.close()


def update_member_contact(member_id, email, email2, phone, phone2, address, city, state, zip):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE members
        SET email = ?, email2 = ?, phone = ?, phone2 = ?, address = ?, city = ?, state = ?, zip = ?
        WHERE id = ?
    """, (email, email2, phone, phone2, address, city, state, zip, member_id))
    conn.commit()
    conn.close()


# ------------------ Committees DB Functions ------------------

def update_member_committees(member_id, committees_dict):
    """Insert or update a member's committees and notes in the committees table."""
    conn = get_connection()
    cursor = conn.cursor()

    # Ensure row exists
    cursor.execute("SELECT 1 FROM committees WHERE member_id = ?", (member_id,))
    if cursor.fetchone() is None:
        # Insert default row
        cursor.execute("INSERT INTO committees (member_id) VALUES (?)", (member_id,))

    # Update committees + notes
    set_clause = ", ".join([f"{col} = ?" for col in committees_dict.keys()])
    values = list(committees_dict.values())
    values.append(member_id)
    query = f"UPDATE committees SET {set_clause} WHERE member_id = ?"
    cursor.execute(query, values)

    conn.commit()
    cursor.close()


def get_all_committees():
    """Return all committee column names from committees table (excluding id/member_id/notes)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(committees)")
    columns = [row[1] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return [c for c in columns if c not in ("id", "member_id", "notes")]


def get_committee_names():
    """Return cleaned-up committee names for display (excluding id/member_id/notes)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(committees)")
    columns = [row[1] for row in cur.fetchall()]
    cur.close()
    conn.close()
    exclude = {"id", "member_id", "notes"}
    return [c.replace("_", " ").title() for c in columns if c not in exclude]


def get_members_by_committee(committee_name):
    """
    Return all members in a given committee, including the 'notes' field.
    Returns a list of dicts with keys: id, badge_number, first_name, last_name, notes.
    """
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    committee_column = committee_name.lower().replace(" ", "_")

    query = f"""
        SELECT m.id, m.badge_number, m.first_name, m.last_name, c.notes
        FROM members m
        JOIN committees c ON m.id = c.member_id
        WHERE c.{committee_column} = 1
        ORDER BY m.last_name, m.first_name
    """
    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]

    cur.close()
    conn.close()
    return rows


def get_member_committees(member_id):
    """Return a dictionary of all committee flags + notes for a member."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM committees WHERE member_id = ?", (member_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else {}

# in database.py
def get_executive_committee_members():
    # Example: return a list of dicts
    return [
        {"badge_number": 101, "first_name": "Alice", "last_name": "Smith",
         "roles": "President", "terms": "2023-2025", "notes": "N/A"},
        {"badge_number": 102, "first_name": "Bob", "last_name": "Jones",
         "roles": "Vice President", "terms": "2023-2025", "notes": "N/A"},
        # etc.
    ]
