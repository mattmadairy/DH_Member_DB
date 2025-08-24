import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database

DATE_FMT = "%m/%d/%Y"
STATUS_OPTIONS = ["Attended", "Exemption Approved"]
METHOD_OPTIONS = ["Cash", "Check", "Electronic"]


class DataTab:
    def __init__(self, parent, columns, db_load_func, db_add_func, db_update_func, db_delete_func,
                 entry_fields, row_adapter=None):
        self.parent = parent
        self.columns = columns
        self.db_load_func = db_load_func
        self.db_add_func = db_add_func
        self.db_update_func = db_update_func
        self.db_delete_func = db_delete_func
        self.entry_fields = entry_fields
        self.row_adapter = row_adapter or (lambda r: list(r[2:]))

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        self.tree.bind("<Double-1>", self.edit_record)

        self.member_id = None

    def load_records(self, member_id):
        self.member_id = member_id
        for row in self.tree.get_children():
            self.tree.delete(row)
        records = self.db_load_func(member_id)
        for r in records:
            values = self.row_adapter(r)
            self.tree.insert("", "end", iid=r[0], values=values)

    def edit_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))

        popup = tk.Toplevel(self.parent)
        popup.title("Edit Entry")
        editors = []
        for i, field in enumerate(self.entry_fields):
            label = field[0]
            opts = field[2] if len(field) == 3 else {}
            ttk.Label(popup, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="e")

            new_var = tk.StringVar(value=current_values[i])
            if opts.get("widget") == "combobox":
                w = ttk.Combobox(popup, textvariable=new_var, values=opts.get("values", []), state="readonly")
            else:
                w = ttk.Entry(popup, textvariable=new_var)
            w.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            editors.append(new_var)

        def save():
            new_vals = [v.get() for v in editors]
            try:
                self.db_update_func(row_id, *new_vals)
                self.load_records(self.member_id)
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(popup, text="Save", command=save).grid(row=len(self.entry_fields), column=0, pady=8)
        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(row=len(self.entry_fields), column=1, pady=8)


class MemberForm:
    def __init__(self, parent, member_id=None, on_save_callback=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        self.on_save_callback = on_save_callback

        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill="both", expand=True)

        # Tabs
        self.tab_basic = ttk.Frame(self.notebook)
        self.tab_contact = ttk.Frame(self.notebook)
        self.tab_membership = ttk.Frame(self.notebook)
        self.tab_dues = ttk.Frame(self.notebook)
        self.tab_work_hours = ttk.Frame(self.notebook)
        self.tab_attendance = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_basic, text="Basic Info")
        self.notebook.add(self.tab_contact, text="Contact")
        self.notebook.add(self.tab_membership, text="Membership")
        self.notebook.add(self.tab_dues, text="Dues History")
        self.notebook.add(self.tab_work_hours, text="Work Hours")
        self.notebook.add(self.tab_attendance, text="Meeting Attendance")

        # Variables
        self.badge_number_var = tk.StringVar()
        self.membership_type_var = tk.StringVar()
        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.dob_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.state_var = tk.StringVar()
        self.zip_var = tk.StringVar()
        self.join_date_var = tk.StringVar()
        self.email2_var = tk.StringVar()
        self.sponsor_var = tk.StringVar()
        self.card_internal_var = tk.StringVar()
        self.card_external_var = tk.StringVar()

        self.membership_types = ["Probationary", "Associate", "Active", "Life", "Prospective", "Wait List", "Former"]

        # Display label storage
        self._display_labels = {}

        # Build read-only tabs
        self._build_read_only_tab(self.tab_basic, [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._edit_basic, "basic")

        self._build_read_only_tab(self.tab_contact, [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._edit_contact, "contact")

        self._build_read_only_tab(self.tab_membership, [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var)
        ], self._edit_membership, "membership")

        # DataTabs
        self.dues_tab = DataTab(
            self.tab_dues,
            columns=["Date", "Amount", "Method", "Notes", "Year"],
            db_load_func=database.get_dues_by_member,
            db_add_func=database.add_dues_payment,
            db_update_func=database.update_dues_payment,
            db_delete_func=database.delete_dues_payment,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Amount", tk.StringVar()),
                ("Method", tk.StringVar(), {"widget": "combobox", "values": METHOD_OPTIONS}),
                ("Notes", tk.StringVar()),
                ("Year", tk.StringVar())
            ],
            row_adapter=lambda r: [r[3], f"{r[2]:.2f}", r[5] or "", r[6] or "", r[4]]
        )

        self.work_tab = DataTab(
            self.tab_work_hours,
            columns=["Date", "Hours", "Type", "Notes"],
            db_load_func=database.get_work_hours_by_member,
            db_add_func=database.add_work_hours,
            db_update_func=database.update_work_hours,
            db_delete_func=database.delete_work_hours,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Hours", tk.StringVar()),
                ("Type", tk.StringVar()),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [r[2], f"{r[3]:.2f}", r[4] or "", r[5] or ""]
        )

        self.attendance_tab = DataTab(
            self.tab_attendance,
            columns=["Date", "Status", "Notes"],
            db_load_func=database.get_meeting_attendance,
            db_add_func=database.add_meeting_attendance,
            db_update_func=database.update_meeting_attendance,
            db_delete_func=database.delete_meeting_attendance,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Status", tk.StringVar(), {"widget": "combobox", "values": STATUS_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [r[2], r[3], r[4] or ""]
        )

        # Load member data
        if self.member_id:
            self._load_member_data()

    def _build_read_only_tab(self, tab, fields, edit_callback, tab_key):
        self._display_labels[tab_key] = {}
        for idx, (label_text, var) in enumerate(fields):
            ttk.Label(tab, text=label_text + ":").grid(row=idx, column=0, sticky="e", padx=5, pady=2)
            lbl = ttk.Label(tab, text=var.get())
            lbl.grid(row=idx, column=1, sticky="w", padx=5, pady=2)
            self._display_labels[tab_key][label_text] = (lbl, var)
        ttk.Button(tab, text="Edit", command=edit_callback).grid(row=len(fields), column=0, columnspan=2, pady=10)

    def _load_member_data(self):
        if not self.member_id:
            return
        m = database.get_member_by_id(self.member_id)
        if not m:
            return

        mapping = {
            "badge_number": m[1],
            "membership_type": m[2],
            "first_name": m[3],
            "last_name": m[4],
            "dob": m[5],
            "email": m[6],
            "phone": m[7],
            "address": m[8],
            "city": m[9],
            "state": m[10],
            "zip": m[11],
            "join_date": m[12],
            "email2": m[13],
            "sponsor": m[14],
            "card_internal": m[15],
            "card_external": m[16]
        }

        for var_name, value in mapping.items():
            var = getattr(self, f"{var_name}_var", None)
            if var:
                # Format dates
                if var_name in ("dob", "join_date") and value:
                    try:
                        dt = datetime.strptime(value, "%Y-%m-%d")
                        var.set(dt.strftime("%m-%d-%Y"))
                    except ValueError:
                        var.set(value)
                else:
                    var.set(value or "")

        # Update read-only labels
        for tab_labels in self._display_labels.values():
            for lbl, var in tab_labels.values():
                lbl.config(text=var.get())

        # Load DataTabs
        self.dues_tab.load_records(self.member_id)
        self.work_tab.load_records(self.member_id)
        self.attendance_tab.load_records(self.member_id)


    # Edit callbacks
    def _edit_basic(self):
        self._open_edit_popup("Basic Info", [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._save_basic)

    def _edit_contact(self):
        self._open_edit_popup("Contact", [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._save_contact)

    def _edit_membership(self):
        self._open_edit_popup("Membership", [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var)
        ], self._save_membership)

    def _open_edit_popup(self, title, fields, save_callback):
        popup = tk.Toplevel(self.top)
        popup.title(f"Edit {title}")
        editors = []
        for i, (label_text, var) in enumerate(fields):
            ttk.Label(popup, text=label_text).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            new_var = tk.StringVar(value=var.get())
            if label_text == "Membership Type":
                w = ttk.Combobox(popup, textvariable=new_var, values=self.membership_types, state="readonly")
            else:
                w = ttk.Entry(popup, textvariable=new_var)
            w.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            editors.append((var, new_var))

        def save():
            for orig_var, new_var in editors:
                orig_var.set(new_var.get())
            save_callback()
            popup.destroy()

        ttk.Button(popup, text="Save", command=save).grid(row=len(fields), column=0, pady=8)
        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(row=len(fields), column=1, pady=8)

    def _save_basic(self):
        database.update_member_basic(self.member_id,
                                     self.first_name_var.get(),
                                     self.last_name_var.get(),
                                     self.dob_var.get())
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)

    def _save_contact(self):
        database.update_member_contact(self.member_id,
                                       self.email_var.get(),
                                       self.email2_var.get(),
                                       self.phone_var.get(),
                                       self.address_var.get(),
                                       self.city_var.get(),
                                       self.state_var.get(),
                                       self.zip_var.get())
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)

    def _save_membership(self):
        database.update_member_membership(self.member_id,
                                          self.badge_number_var.get(),
                                          self.membership_type_var.get(),
                                          self.join_date_var.get(),
                                          self.sponsor_var.get(),
                                          self.card_internal_var.get(),
                                          self.card_external_var.get())
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)
