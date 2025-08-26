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
        #self.tree.bind("<Double-1>", self.edit_record)
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


# ----------------------- Member Form -----------------------
class MemberForm:
    def __init__(self, parent, member_id=None, on_save_callback=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        self.on_save_callback = on_save_callback

        # ----- Notebook -----
        style = ttk.Style(self.top)
        style.configure(
            "CustomNotebook.TNotebook.Tab",
            padding=[12, 5],  # slightly larger than text
            anchor="center"
        )

        self.notebook = ttk.Notebook(self.top, style="CustomNotebook.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # ----- Tabs -----
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

        # ----- Resize Tabs -----
        def resize_tabs(event=None):
            total_tabs = len(self.notebook.tabs())
            if total_tabs == 0:
                return
            notebook_width = self.notebook.winfo_width()
            # Stretch tabs to fill width but limit max tab width
            tab_width = min(150, notebook_width // total_tabs)
            style.configure("CustomNotebook.TNotebook.Tab", width=tab_width)

        resize_tabs()
        self.notebook.bind("<Configure>", resize_tabs)

        # ----- Variables -----
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

        self._display_labels = {}

        # ----- Read-only tabs -----
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

        # ----- Data tabs -----
        self.dues_tab = DuesTab(self.tab_dues, self.member_id)
        self.work_tab = WorkHoursTab(self.tab_work_hours, self.member_id)
        self.attendance_tab = AttendanceTab(self.tab_attendance, self.member_id)

        # ----- Load member data -----
        if self.member_id:
            self._load_member_data()

        # ----- Set reasonable default window size -----
        self.top.update_idletasks()  # calculate natural size
        natural_width = self.top.winfo_width()
        natural_height = self.top.winfo_height()
        width = max(850, min(natural_width, 1000))  # limit max width
        height = max(300, natural_height)
        self.top.geometry(f"{width}x{height}")



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

        # Load data tabs
        self.work_tab.load_records(self.member_id)
        self.attendance_tab.load_records(self.member_id)

    # --- Edit callbacks ---
    def _edit_basic(self):
        self._open_edit_popup_generic("Basic Info", [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._save_basic)

    def _edit_contact(self):
        self._open_edit_popup_generic("Contact", [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._save_contact)

    def _edit_membership(self):
        self._open_edit_popup_generic("Membership", [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var)
        ], self._save_membership)

    def _open_edit_popup_generic(self, title, field_names, save_callback):
        popup = tk.Toplevel()
        popup.title(title)
        editors = []
        for i, (label, var) in enumerate(field_names):
            ttk.Label(popup, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            entry_var = tk.StringVar(value=var.get())

            # Use a Combobox for Membership Type
            if label == "Membership Type":
                w = ttk.Combobox(popup, textvariable=entry_var, 
                                values=self.membership_types, state="readonly")
            else:
                w = ttk.Entry(popup, textvariable=entry_var)

            w.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            editors.append((var, entry_var))

        def save():
            for var, entry_var in editors:
                var.set(entry_var.get())
            save_callback()
            popup.destroy()

        ttk.Button(popup, text="Save", command=save).grid(row=len(field_names), column=0, pady=8)
        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(row=len(field_names), column=1, pady=8)


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


# ----------------------- Specialized Tabs -----------------------
class DuesTab(DataTab):
    def __init__(self, parent, member_id):
        super().__init__(
            parent,
            columns=["Date", "Year", "Amount", "Method", "Notes"],
            db_load_func=database.get_dues_by_member,
            db_add_func=self._add_dues,
            db_update_func=self._update_dues,
            db_delete_func=database.delete_dues_payment,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Year", tk.StringVar()),
                ("Amount", tk.StringVar()),
                ("Method", tk.StringVar(), {"widget": "combobox", "values": METHOD_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",
                r[3],
                f"{float(r[4]):.2f}" if r[4] else "0.00",
                r[5] or "",
                r[6] or ""
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind double-click event on the tree (or data table) to the handler
        self.tree.bind("<Double-1>", self.on_dues_double_click)

    def _transform_entries(self, entries):
        date_str, year, amount_str, method, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            payment_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            payment_date = date_str
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0
        year = str(year) if year else str(datetime.now().year)
        return payment_date, amount, method or "", notes or "", year

    def _add_dues(self, *entries):
        payment_date, amount, method, notes, year = self._transform_entries(entries)
        database.add_dues_payment(self.member_id, amount, payment_date, method, notes, year)
        self.load_records(self.member_id)

    def _update_dues(self, payment_id, *entries):
        payment_date, amount, method, notes, year = self._transform_entries(entries)
        database.update_dues_payment(payment_id, amount=amount, payment_date=payment_date,
                                     method=method, notes=notes, year=year)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")
        default_year = database.get_default_year()
        self._open_edit_popup("Add Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              self._add_dues, [today_str, str(default_year), "", "", ""])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              lambda *vals: self._update_dues(row_id, *vals), current_values)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_dues_payment(row_id)
            self.load_records(self.member_id)

    # Double-click handler for dues table
    def on_dues_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              lambda *vals: self._update_dues(row_id, *vals), current_values)
    def _open_edit_popup(self, title, labels, save_func, default_values):
        # Create the popup window
        popup = tk.Toplevel(self.parent)
        popup.title(title)

        # Create form entries
        form_entries = []
        row = 0
        for label, default_value in zip(labels, default_values):
            ttk.Label(popup, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            
            if label == "Method":
                # Create a combobox for "Method"
                entry_var = tk.StringVar(value=default_value)
                combobox = ttk.Combobox(popup, textvariable=entry_var, values=METHOD_OPTIONS)
                combobox.grid(row=row, column=1, padx=5, pady=5)
                form_entries.append(entry_var)
            else:
                # Create a regular entry for other fields
                entry_var = tk.StringVar(value=default_value)
                entry = ttk.Entry(popup, textvariable=entry_var)
                entry.grid(row=row, column=1, padx=5, pady=5)
                form_entries.append(entry_var)
            
            row += 1

        # Save button to save the data
        def save():
            entries = [entry.get() for entry in form_entries]
            save_func(*entries)  # Call the provided save function with the entries
            popup.destroy()

        ttk.Button(popup, text="Save", command=save).grid(row=row, column=0, columnspan=2, pady=5)

        # Make the popup modal
        popup.grab_set()
        popup.mainloop()


class WorkHoursTab(DataTab):
    def __init__(self, parent, member_id):
        super().__init__(
            parent,
            columns=["Date", "Activity", "Hours", "Notes"],  # Changed order: Activity and Hours
            db_load_func=database.get_work_hours_by_member,
            db_add_func=self._add_work,
            db_update_func=self._update_work,
            db_delete_func=database.delete_work_hours,
            entry_fields=[ 
                ("Date", tk.StringVar()),
                ("Hours", tk.StringVar()),
                ("Activity", tk.StringVar()),  # Changed field name to match updated order
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",  # Date is still in the second column
                r[3] or "",  # Activity is now the second column (was third before)
                f"{float(r[4]):.1f}" if r[4] else "0.0",  # Hours is now the third column (was second before)
                r[5] or ""   # Notes remains the same
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind double-click event on the tree (or data table) to the handler
        self.tree.bind("<Double-1>", self.on_work_hours_double_click)

    def _transform_entries(self, entries):
        date_str, hours_str, activity_str, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            date = date_str
        try:
            hours = float(hours_str)
        except ValueError:
            hours = 0.0
        return date, hours, activity_str or "", notes or ""

    def _add_work(self, *entries):
        date, hours, activity_str, notes = self._transform_entries(entries)
        database.add_work_hours(self.member_id, date, hours, activity_str, notes)
        self.load_records(self.member_id)

    def _update_work(self, work_id, *entries):
        date, hours, activity_str, notes = self._transform_entries(entries)
        database.update_work_hours(work_id, date=date, hours=hours, activity=activity_str, notes=notes)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")  # Get today's date
        # Open the edit popup, passing default values
        self._open_edit_popup("Add Work Hours", ["Date", "Hours", "Activity", "Notes"], 
                              self._add_work, [today_str, "", "", ""])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        
        # Ensure the values are in the correct order: Date, Activity, Hours, Notes
        current_values = [
            current_values[0],  # Date
            current_values[1],  # Activity
            current_values[2],  # Hours
            current_values[3]   # Notes
        ]
        
        self._open_edit_popup("Edit Work Hours", ["Date", "Activity", "Hours", "Notes"], 
                            lambda *vals: self._update_work(row_id, *vals), current_values)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_work_hours(row_id)
            self.load_records(self.member_id)

    # Double-click handler for work hours table
    def on_work_hours_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Work Hours", ["Date", "Activity", "Hours", "Notes"],
                              lambda *vals: self._update_work(row_id, *vals), current_values)

    def _open_edit_popup(self, title, labels, save_function, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)

        entry_vars = {}
        entries = []

        # Correct label order: Date, Activity, Hours, Notes
        correct_labels = ["Date", "Activity", "Hours", "Notes"]

        # Create label and entry widgets for each field
        for idx, label in enumerate(correct_labels):  # Use correct_labels order
            frame = tk.Frame(popup)
            tk.Label(frame, text=label).pack(side=tk.LEFT)

            var = tk.StringVar()
            # Set default value if any
            if default_values and idx < len(default_values):
                var.set(default_values[idx])

            # Create entry field for each label
            entry = tk.Entry(frame, textvariable=var)
            entry.pack(side=tk.RIGHT)
            entry_vars[label] = var
            entries.append(entry)
            frame.pack(fill="x", padx=10, pady=5)

        def save_record():
            # Get the values from the form
            date = entry_vars["Date"].get()
            hours = entry_vars["Hours"].get()
            activity = entry_vars["Activity"].get()
            notes = entry_vars["Notes"].get()

            # Call the save_function, e.g., _add_work or another
            save_function(date, hours, activity, notes)
            popup.destroy()

        save_button = tk.Button(popup, text="Save", command=save_record)
        save_button.pack(pady=10)

        popup.mainloop()


class AttendanceTab(DataTab):
    def __init__(self, parent, member_id):
        # Initialize the DataTab with correct parameters for the AttendanceTab
        super().__init__(
            parent,
            columns=["Date", "Status", "Notes"],
            db_load_func=database.get_meeting_attendance,
            db_add_func=self._add_attendance,
            db_update_func=self._update_attendance,
            db_delete_func=database.delete_meeting_attendance,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Status", tk.StringVar(), {"widget": "combobox", "values": STATUS_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",
                r[3] or "",
                r[4] or ""
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind the double-click event on the tree (or data table)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def edit_selected(self):
        """Triggered when 'Edit' button is clicked"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))

        # Ensure values are in correct order: Date, Status, Notes
        current_values = [
            current_values[0],  # Date
            current_values[1],  # Status
            current_values[2]   # Notes
        ]

        # Open the edit popup
        self._open_edit_popup("Edit Attendance", ["Date", "Status", "Notes"],
                              lambda *vals: self._update_attendance(row_id, *vals), current_values)

    def _on_tree_double_click(self, event):
        """Triggered when a row in the tree is double-clicked"""
        self.edit_selected()

    def _transform_entries(self, entries):
        date_str, status, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            date = date_str
        return date, status or "", notes or ""

    def _add_attendance(self, *entries):
        date, status, notes = self._transform_entries(entries)
        database.add_meeting_attendance(self.member_id, date, status, notes)
        self.load_records(self.member_id)

    def _update_attendance(self, attendance_id, *entries):
        date, status, notes = self._transform_entries(entries)
        database.update_meeting_attendance(attendance_id, date=date, status=status, notes=notes)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")
        self._open_edit_popup("Add Attendance", ["Date", "Status", "Notes"],
                              self._add_attendance, [today_str, STATUS_OPTIONS[0], ""])

    def _open_edit_popup(self, title, labels, save_function, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)

        entry_vars = {}
        entries = []

        for idx, label in enumerate(labels):
            frame = tk.Frame(popup)
            tk.Label(frame, text=label).pack(side=tk.LEFT)

            var = tk.StringVar()
            if default_values and idx < len(default_values):
                var.set(default_values[idx])

            if label == "Status":
                entry = ttk.Combobox(frame, textvariable=var, values=STATUS_OPTIONS)
            else:
                entry = tk.Entry(frame, textvariable=var)

            entry.pack(side=tk.RIGHT)
            entry_vars[label] = var
            entries.append(entry)
            frame.pack(fill="x", padx=10, pady=5)

        def save_record():
            date = entry_vars["Date"].get()
            status = entry_vars["Status"].get()
            notes = entry_vars["Notes"].get()
            save_function(date, status, notes)
            popup.destroy()

        save_button = tk.Button(popup, text="Save", command=save_record)
        save_button.pack(pady=10)

        popup.mainloop()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_meeting_attendance(row_id)
            self.load_records(self.member_id)