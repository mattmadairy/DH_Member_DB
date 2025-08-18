import sqlite3 
import os
import shutil
import datetime

DB_NAME = "members.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn


# ------------------ Init DB ------------------ #
def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Members table
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

    # Single dues/payments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS dues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            amount REAL,
            payment_date TEXT,
            method TEXT,
            notes TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# ------------------ Migration ------------------ #
def rebuild_table(conn, table_name, schema_sql, required_columns):
    """Rebuild a table to include missing columns while preserving data."""
    c = conn.cursor()

    # Backup original
    backup_table = f"{table_name}_backup_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    c.execute(f"ALTER TABLE {table_name} RENAME TO {backup_table}")

    # Create new table with proper schema
    c.execute(schema_sql)

    # Copy common columns
    existing_cols = [col[1] for col in c.execute(f"PRAGMA table_info({backup_table})")]
    common_cols = [col for col in required_columns if col in existing_cols]

    if common_cols:
        cols_str = ", ".join(common_cols)
        c.execute(f"INSERT INTO {table_name} ({cols_str}) SELECT {cols_str} FROM {backup_table}")

    # Drop backup
    c.execute(f"DROP TABLE {backup_table}")


def migrate_all():
    conn = get_connection()
    c = conn.cursor()

    # Members migration
    c.execute("PRAGMA table_info(members)")
    existing_cols = [col[1] for col in c.fetchall()]
    required_members = [
        "id", "badge_number", "membership_type", "first_name", "last_name", "dob",
        "email", "phone", "address", "city", "state", "zip", "join_date",
        "email2", "sponsor", "card_internal", "card_external", "deleted"
    ]

    if set(required_members) != set(existing_cols):
        print("⚠️ Rebuilding members table with correct schema")
        rebuild_table(conn, "members", """
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
                zip TEXT,
                join_date TEXT,
                email2 TEXT,
                sponsor TEXT,
                card_internal TEXT,
                card_external TEXT,
                deleted INTEGER DEFAULT 0
            )
        """, required_members)

    # Dues migration
    c.execute("PRAGMA table_info(dues)")
    existing_cols = [col[1] for col in c.fetchall()]
    required_dues = ["id", "member_id", "amount", "payment_date", "method", "notes"]

    if set(required_dues) != set(existing_cols):
        print("⚠️ Rebuilding dues table with correct schema")
        rebuild_table(conn, "dues", """
            CREATE TABLE dues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER,
                amount REAL,
                payment_date TEXT,
                method TEXT,
                notes TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """, required_dues)

    conn.commit()
    conn.close()


# ------------------ Member Functions ------------------ #
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


# ------------------ Dues Functions ------------------ #
def add_dues_payment(member_id, amount, payment_date, method, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO dues (member_id, amount, payment_date, method, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (member_id, amount, payment_date, method, notes))
    conn.commit()
    conn.close()


def get_dues_by_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, member_id, amount, payment_date, method, notes
        FROM dues
        WHERE member_id=?
        ORDER BY payment_date DESC
    """, (member_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_dues_payment_by_id(dues_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, member_id, amount, payment_date, method, notes
        FROM dues
        WHERE id=?
    """, (dues_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_dues_payment(dues_id, amount, payment_date, method, notes):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE dues
        SET amount=?, payment_date=?, method=?, notes=?
        WHERE id=?
    """, (amount, payment_date, method, notes, dues_id))
    conn.commit()
    conn.close()


def delete_dues_payment(dues_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM dues WHERE id=?", (dues_id,))
    conn.commit()
    conn.close()


# ------------------ Reporting Functions ------------------ #
def get_expected_dues(membership_type):
    """Return the expected yearly dues for a given membership type."""
    mapping = {
        "Probationary": 150,
        "Associate": 300,
        "Active": 150,
    }
    return mapping.get(membership_type, 0)


def get_payments_by_year(year):
    """Return total payments for each member in a given calendar year."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT 
            m.id,
            m.first_name,
            m.last_name,
            m.membership_type,
            COALESCE(SUM(d.amount), 0) AS total_paid
        FROM members m
        LEFT JOIN dues d 
          ON m.id = d.member_id 
         AND strftime('%Y', d.payment_date) = ?
        WHERE m.deleted=0
        GROUP BY m.id
        ORDER BY m.last_name, m.first_name
    """, (str(year),))
    rows = c.fetchall()
    conn.close()

    # add expected dues
    results = []
    for row in rows:
        member_id, first, last, mtype, total_paid = row
        expected = get_expected_dues(mtype)
        results.append((member_id, first, last, mtype, total_paid, expected))
    return results


def get_outstanding_dues(year):
    """Return members who have outstanding dues in a given calendar year."""
    payments = get_payments_by_year(year)
    results = []
    for member_id, first, last, mtype, total_paid, expected in payments:
        outstanding = expected - total_paid
        if outstanding > 0:
            results.append((member_id, first, last, mtype, total_paid, expected, outstanding))
    return results


# ------------------ Auto Init & Migrate ------------------ #
if not os.path.exists(DB_NAME):
    init_db()
else:
    init_db()
    migrate_all()
