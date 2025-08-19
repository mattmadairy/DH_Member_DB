import os
import sqlite3
import database
import tempfile
import shutil
import datetime


def run_tests():
    print("=== Running Membership Database Tests ===")

    # --- Setup temporary DB ---
    tmpdir = tempfile.mkdtemp()
    test_db = os.path.join(tmpdir, "test_members.db")
    database.DB_NAME = test_db  # override DB_NAME
    database.init_db()

    # --- Test member insert ---
    member_data = (
        "123", "Active", "John", "Doe", "1990-01-01",
        "john@example.com", "555-1234", "123 Main St", "Townsville",
        "NY", "12345", "2020-01-01", "john2@example.com",
        "Sponsor Guy", "INT123", "EXT456"
    )
    member_id = database.add_member(member_data)
    print(f"Added member with ID: {member_id}")

    # --- Test get member ---
    member = database.get_member_by_id(member_id)
    assert member[3] == "John" and member[4] == "Doe"
    print("✔ get_member_by_id works")

    # --- Test update member ---
    updated_data = list(member_data)
    updated_data[2] = "Jane"  # first_name
    database.update_member(member_id, tuple(updated_data))
    member = database.get_member_by_id(member_id)
    assert member[3] == "Jane"
    print("✔ update_member works")

    # --- Test dues payment ---
    today = datetime.date.today().isoformat()
    database.add_dues_payment(member_id, 100.0, today, "Cash", "Initial payment")
    dues = database.get_dues_by_member(member_id)
    assert len(dues) == 1 and dues[0][2] == 100.0
    print("✔ add_dues_payment and get_dues_by_member work")

    # --- Test update dues ---
    dues_id = dues[0][0]
    database.update_dues_payment(dues_id, 120.0, today, "Check", "Updated payment")
    updated = database.get_dues_payment_by_id(dues_id)
    assert updated[2] == 120.0
    print("✔ update_dues_payment works")

    # --- Test reporting ---
    year = str(datetime.date.today().year)
    rows = database.get_payments_by_year(year, ["Active"])
    assert rows, "No rows returned in get_payments_by_year"
    print("✔ get_payments_by_year works")

    rows_outstanding = database.get_outstanding_dues(year, ["Active"])
    print("Outstanding dues:", rows_outstanding)

    # --- Test delete ---
    database.soft_delete_member_by_id(member_id)
    deleted = database.get_deleted_members()
    assert any(m[0] == member_id for m in deleted)
    print("✔ soft_delete_member_by_id works")

    database.restore_member(member_id)
    restored = database.get_member_by_id(member_id)
    assert restored[17] == 0  # deleted flag
    print("✔ restore_member works")

    database.delete_member(member_id)
    assert database.get_member_by_id(member_id) is None
    print("✔ delete_member works")

    print("\n🎉 All tests passed successfully!")

    # cleanup
    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    run_tests()
