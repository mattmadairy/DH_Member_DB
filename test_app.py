import os
import database
import csv_utils
import tkinter as tk
from tkinter import messagebox
import gui
import member_form
import reporting_window
import settings_window

results = []  # store (test_name, status, message)


def record_result(name, success, message=""):
    status = "PASS" if success else "FAIL"
    results.append((name, status, message))
    print(f"[{status}] {name} {('- ' + message) if message else ''}")


def test_database():
    try:
        # Use test DB to protect real data
        database.DB_NAME = "test_members.db"
        database.init_db()

        # Settings
        database.set_setting("test_key", "123")
        record_result("Settings get/set", database.get_setting("test_key") == "123")

        # Members
        member_id = database.add_member((
            "123", "Active", "Test", "User", "1990-01-01",
            "test@example.com", "555-1234", "123 Main St", "Townsville", "TS", "12345",
            "2025-01-01", "alt@example.com", "Sponsor A", "111", "222"
        ))
        record_result("Add member", database.get_member_by_id(member_id) is not None)

        database.update_member(member_id, (
            "123", "Active", "Updated", "User", "1990-01-01",
            "new@example.com", "555-5678", "456 Side St", "New City", "NC", "67890",
            "2025-01-01", "alt2@example.com", "Sponsor B", "333", "444"
        ))
        updated = database.get_member_by_id(member_id)
        record_result("Update member", updated[3] == "Updated")

        # Dues
        database.add_dues_payment(member_id, 150, "2025-01-15", "Cash", "Paid", year=2025)
        dues = database.get_dues_by_member(member_id)
        record_result("Add dues payment", len(dues) > 0)

        first_due = dues[0]
        database.update_dues_payment(first_due[0], 200, "2025-02-01", "Card", "Updated note", year=2025)
        record_result("Update dues payment", database.get_dues_payment_by_id(first_due[0])[2] == 200)

        # Reports
        paid = database.get_payments_by_year(2025, ["Active"])
        outstanding = database.get_outstanding_dues(2025, ["Active"])
        all_dues = database.get_all_dues(2025, ["Active"])
        record_result("Reports", isinstance(paid, list) and isinstance(outstanding, list) and isinstance(all_dues, list))

        # Soft delete / restore / delete
        database.soft_delete_member_by_id(member_id)
        deleted = database.get_deleted_members()
        record_result("Soft delete member", any(m[0] == member_id for m in deleted))

        database.restore_member(member_id)
        record_result("Restore member", database.get_member_by_id(member_id) is not None)

        database.delete_member(member_id)
        record_result("Hard delete member", database.get_member_by_id(member_id) is None)

    except Exception as e:
        record_result("Database tests", False, str(e))


def test_csv():
    try:
        filename = "test_members.csv"
        csv_utils.export_members_to_csv(filename)
        ok = os.path.exists(filename)
        record_result("CSV export", ok)

        if ok:
            csv_utils.import_members_from_csv(filename)
            record_result("CSV import", True)

        os.remove(filename)
    except Exception as e:
        record_result("CSV tests", False, str(e))


def test_gui():
    try:
        # make sure GUI talks to the same test DB
        database.DB_NAME = "test_members.db"
        database.init_db()

        # create a dedicated GUI test member
        gui_member_id = database.add_member((
            "999", "Active", "Gui", "Tester", "1995-01-01",
            "gui@tester.com", "555-0000", "1 Gui Way", "UItown", "UI", "00000",
            "2025-01-01", "", "", "", ""
        ))

        root = tk.Tk()
        root.withdraw()

        app = gui.MemberApp(root)
        # open directly to dues tab if supported
        mf = member_form.MemberForm(root, member_id=gui_member_id, open_tab="dues")
        rw = reporting_window.ReportingWindow(root)
        sw = settings_window.SettingsWindow(root)

        # Switch to Dues History tab (if not already there)
        try:
            if hasattr(mf, "notebook"):
                mf.notebook.select(mf.tab_dues)
            record_result("GUI MemberForm Dues Tab", True)
        except Exception as e:
            record_result("GUI MemberForm Dues Tab", False, str(e))

        # Add a dues row via DB, refresh MemberForm, then delete it via GUI
        try:
            note_text = "GUI Test Due"
            database.add_dues_payment(gui_member_id, 99, "2025-03-01", "Cash", note_text, year=2025)
            mf.load_dues_history()

            # find the inserted row in the tree by notes
            target_iid = None
            for iid in mf.dues_tree.get_children():
                vals = mf.dues_tree.item(iid, "values")  # (year, amount, date, method, notes)
                if len(vals) >= 5 and vals[4] == note_text:
                    target_iid = iid
                    break
            record_result("GUI Add Due (via DB refresh)", target_iid is not None)

            # delete it via GUI method (auto-confirm the dialog)
            if target_iid is not None:
                mf.dues_tree.selection_set(target_iid)

                old_ask = messagebox.askyesno
                messagebox.askyesno = lambda *a, **k: True  # auto-confirm

                try:
                    mf.delete_dues_payment()
                finally:
                    messagebox.askyesno = old_ask

                mf.load_dues_history()
                still_exists = False
                for iid in mf.dues_tree.get_children():
                    vals = mf.dues_tree.item(iid, "values")
                    if len(vals) >= 5 and vals[4] == note_text:
                        still_exists = True
                        break
                record_result("GUI Delete Due", not still_exists)
            else:
                record_result("GUI Delete Due", False, "Inserted due not found in tree")
        except Exception as e:
            record_result("GUI Add/Delete Dues", False, str(e))

        # Close windows
        mf.top.destroy()   # MemberForm holds its Toplevel in .top
        rw.destroy()       # ReportingWindow is a Toplevel
        sw.destroy()       # SettingsWindow is a Toplevel
        root.destroy()

        record_result("GUI windows", True)

        # cleanup the GUI test member
        try:
            database.delete_member(gui_member_id)
        except Exception:
            pass

    except Exception as e:
        record_result("GUI tests", False, str(e))


if __name__ == "__main__":
    test_database()
    test_csv()
    test_gui()

    # Cleanup test DB
    if os.path.exists("test_members.db"):
        os.remove("test_members.db")

    print("\n=== TEST SUMMARY ===")
    for name, status, message in results:
        print(f"{status:5} | {name} {('- ' + message) if message else ''}")

    print("\n✅ Test run complete!")
