import sqlite3
import os

DB_FILE = "members.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def get_all_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted_at IS NULL")
    result = c.fetchall()
    conn.close()
    return result

def get_deleted_members():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE deleted_at IS NOT NULL")
    result = c.fetchall()
    conn.close()
    return result

def get_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    result = c.fetchone()
    conn.close()
    return result

def add_member(badge_number, membership_type, first_name, last_name, dob,
               email, phone, address, city, state, zip_code, join_date,
               email2, sponsor, card_internal, card_external):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO members (
            badge_number, membership_type, first_name, last_name, dob,
            email, phone, address, city, state, zip_code, join_date,
            email2, sponsor, card_internal, card_external
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        badge_number, membership_type, first_name, last_name, dob,
        email, phone, address, city, state, zip_code, join_date,
        email2, sponsor, card_internal, card_external
    ))
    conn.commit()
    conn.close()

def update_member(member_id, badge_number, membership_type, first_name, last_name, dob,
                  email, phone, address, city, state, zip_code, join_date,
                  email2, sponsor, card_internal, card_external):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE members
        SET badge_number=?, membership_type=?, first_name=?, last_name=?, dob=?,
            email=?, phone=?, address=?, city=?, state=?, zip_code=?, join_date=?,
            email2=?, sponsor=?, card_internal=?, card_external=?
        WHERE id=?
    """, (
        badge_number, membership_type, first_name, last_name, dob,
        email, phone, address, city, state, zip_code, join_date,
        email2, sponsor, card_internal, card_external, member_id
    ))
    conn.commit()
    conn.close()

def soft_delete_member_by_id(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted_at=datetime('now') WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def restore_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE members SET deleted_at=NULL WHERE id=?", (member_id,))
    conn.commit()
    conn.close()

def permanent_delete_member(member_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()
