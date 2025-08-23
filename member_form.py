# member_form.py
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

        # Treeview
        self.tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=120, anchor="w")
        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        self.tree.bind("<Double-1>", self.edit_record)

        # Entry frame
        self.entry_frame = ttk.Frame(parent)
        self.entry_frame.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        self._build_entries()

        # Buttons
        btns = ttk.Frame(parent)
        btns.grid(row=2, column=0, columnspan=4, sticky="w", padx=5, pady=5)
        ttk.Button(btns, text="Add Entry", command=self.add_entry).pack(side="left", padx=4)
        ttk.Button(btns, text="Delete Entry", command=self.delete_entry).pack(side="left", padx=4)

        self.member_id = None

    def _validate_float(self, value):
        if value == "" or value == ".":
            return True
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _build_entries(self):
        for i, field in enumerate(self.entry_fields):
            if len(field) == 2:
                label, var = field
                opts = {}
            else:
                label, var, opts = field

            ttk.Label(self.entry_frame, text=label).grid(row=i, column=0, sticky="e", padx=5, pady=2)

            if opts.get("widget") == "combobox":
                cb = ttk.Combobox(self.entry_frame, textvariable=var, values=opts.get("values", []), state="readonly")
                cb.grid(row=i, column=1, sticky="w", padx=5, pady=2)
            else:
                ent = ttk.Entry(self.entry_frame, textvariable=var)
                if label.lower() == "hours":
                    vcmd = (self.entry_frame.register(self._validate_float), "%P")
                    ent.configure(validate="key", validatecommand=vcmd)
                ent.grid(row=i, column=1, sticky="w", padx=5, pady=2)

    def load_records(self, member_id):
        self.member_id = member_id
        for row in self.tree.get_children():
            self.tree.delete(row)
        records = self.db_load_func(member_id)
        for r in records:
            values = self.row_adapter(r)
            self.tree.insert("", "end", iid=r[0], values=values)

    def _collect_values_from_entries(self):
        values = []
        for field in self.entry_fields:
            values.append(field[1].get())
        return values

    def _validate_required(self):
        for field in self.entry_fields:
            if len(field) == 3:
                label, var, opts = field
                if opts.get("required") and not str(var.get()).strip():
                    messagebox.showerror("Missing Required Field", f"'{label}' is required.")
                    return False
        return True

    def add_entry(self):
        if not self.member_id:
            return
        if not self._validate_required():
            return

        values = self._collect_values_from_entries()
        try:
            self.db_add_func(self.member_id, *values)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.load_records(self.member_id)
        self._reset_inputs()

    def _reset_inputs(self):
        today = datetime.today().strftime(DATE_FMT)
        default_year = str(database.get_default_year())

        for field in self.entry_fields:
            label, var = field[0], field[1]
            if label.lower() == "date":
                var.set(today)
            elif label.lower() == "year":
                var.set(default_year)
            else:
                if len(field) == 3 and field[2].get("widget") == "combobox":
                    var.set("")
                else:
                    var.set("")

    def delete_entry(self):
        selected = self.tree.selection()
        if not selected:
            return
        entry_id = selected[0]
        if not self.tree.exists(entry_id):
            return
        if messagebox.askyesno("Delete Entry", "Delete this entry?"):
            try:
                self.db_delete_func(int(entry_id))
                self.load_records(self.member_id)
            except Exception as e:
                messagebox.showerror("Error", str(e))

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
            if len(field) == 2:
                label, _var = field
                opts = {}
            else:
                label, _var, opts = field

            ttk.Label(popup, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="e")

            if opts.get("widget") == "combobox":
                new_var = tk.StringVar(value=current_values[i])
                w = ttk.Combobox(popup, textvariable=new_var, values=opts.get("values", []), state="readonly")
                w.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            else:
                new_var = tk.StringVar(value=current_values[i])
                w = ttk.Entry(popup, textvariable=new_var)
                if label.lower() == "hours":
                    vcmd = (popup.register(self._validate_float), "%P")
                    w.configure(validate="key", validatecommand=vcmd)
                w.grid(row=i, column=1, padx=5, pady=3, sticky="w")

            editors.append(new_var)

        def save():
            new_vals = [v.get() for v in editors]
            for j, field in enumerate(self.entry_fields):
                if len(field) == 3 and field[2].get("required") and not str(new_vals[j]).strip():
                    messagebox.showerror("Missing Required Field", f"'{field[0]}' is required.")
                    return
            try:
                self.db_update_func(row_id, *new_vals)
                self.load_records(self.member_id)
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(popup, text="Save", command=save).grid(row=len(self.entry_fields), column=0, columnspan=2, pady=8)


class MemberForm:
    def __init__(self, parent, member_id=None, on_save_callback=None, open_tab=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        self.on_save_callback = on_save_callback
        self.top.bind("<Return>", lambda e: self.save_member())

        self.notebook = ttk.Notebook(self.top)
        self.notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

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

        # --- Form Variables ---
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

        self._build_fields()

        ttk.Button(self.tab_basic, text="Save", command=self.save_basic_info).grid(row=5, column=0, pady=5)
        ttk.Button(self.tab_contact, text="Save", command=self.save_contact).grid(row=10, column=0, pady=5)
        ttk.Button(self.tab_membership, text="Save", command=self.save_membership_info).grid(row=10, column=0, pady=5)

        # --- Dues Tab (UI order: Date, Year, Amount, Method, Notes) ---
        # --- Dues Tab (UI order: Date, Year, Amount, Method, Notes) ---
        self.dues_date_var = tk.StringVar(value=datetime.today().strftime(DATE_FMT))
        self.dues_year_var = tk.StringVar(value=str(database.get_default_year()))
        self.dues_amount_var = tk.StringVar()
        self.dues_method_var = tk.StringVar()
        self.dues_notes_var = tk.StringVar()

        self.dues_tab = DataTab(
            self.tab_dues,
            columns=["date", "year", "amount", "method", "notes"],  # Treeview columns
            db_load_func=database.get_dues_by_member,
            db_add_func=lambda member_id, date, year, amount, method, notes:
                database.add_dues_payment(member_id, float(amount), date, method or None, notes or None, year),
            db_update_func=lambda row_id, date, year, amount, method, notes:
                database.update_dues_payment(
                    row_id,
                    amount=float(amount),
                    payment_date=date,
                    method=(method or None),
                    notes=(notes or None),
                    year=year
                ),
            db_delete_func=database.delete_dues_payment,
            entry_fields=[
                ("Date", self.dues_date_var),
                ("Year", self.dues_year_var),
                ("Amount", self.dues_amount_var),
                ("Method", self.dues_method_var, {"widget": "combobox", "values": METHOD_OPTIONS}),
                ("Notes", self.dues_notes_var)
            ],
            row_adapter=lambda r: [
                r[3],                 # Date
                r[4],                 # Year
                f"{(r[2] or 0):.2f}", # Amount
                r[5] or "",           # Method
                r[6] or ""            # Notes
            ]
        )


        # --- Work Hours Tab ---
        self.wh_date_var = tk.StringVar(value=datetime.today().strftime(DATE_FMT))
        self.wh_type_var = tk.StringVar()
        self.wh_hours_var = tk.StringVar()
        self.wh_notes_var = tk.StringVar()

        self.work_hours_tab = DataTab(
            self.tab_work_hours,
            columns=["date", "type", "hours", "notes"],
            db_load_func=database.get_work_hours_by_member,
            db_add_func=lambda member_id, date, type_, hours, notes:
                database.add_work_hours(member_id, date, float(hours), type_ or None, notes or None),
            db_update_func=lambda row_id, date, type_, hours, notes:
                database.update_work_hours(row_id, date=date, work_type=type_ or None,
                                           hours=float(hours), notes=notes or None),
            db_delete_func=database.delete_work_hours,
            entry_fields=[
                ("Date", self.wh_date_var),
                ("Type", self.wh_type_var),
                ("Hours", self.wh_hours_var),
                ("Notes", self.wh_notes_var)
            ],
            row_adapter=lambda r: (r[2], r[4] or "", f"{float(r[3] or 0):.2f}", r[5] or "")
        )

        # --- Attendance Tab ---
        self.att_date_var = tk.StringVar(value=datetime.today().strftime(DATE_FMT))
        self.att_status_var = tk.StringVar(value="")
        self.att_notes_var = tk.StringVar()

        self.attendance_tab = DataTab(
            self.tab_attendance,
            columns=["date", "status", "notes"],
            db_load_func=database.get_meeting_attendance,
            db_add_func=lambda member_id, date, status, notes:
                database.add_meeting_attendance(member_id, date, status, notes or None),
            db_update_func=lambda row_id, date, status, notes:
                database.update_meeting_attendance(row_id, meeting_date=date, status=status, notes=notes or None),
            db_delete_func=database.delete_meeting_attendance,
            entry_fields=[
                ("Date", self.att_date_var),
                ("Status", self.att_status_var, {"widget": "combobox", "values": STATUS_OPTIONS, "required": True}),
                ("Notes", self.att_notes_var)
            ],
            row_adapter=lambda r: [r[2], r[3], r[4] or ""]
        )

        # Load data
        if self.member_id:
            self.load_member()
            self.dues_tab.load_records(self.member_id)
            self.work_hours_tab.load_records(self.member_id)
            self.attendance_tab.load_records(self.member_id)

        if open_tab == "dues":
            self.notebook.select(self.tab_dues)
        elif open_tab == "work_hours":
            self.notebook.select(self.tab_work_hours)
        elif open_tab == "attendance":
            self.notebook.select(self.tab_attendance)

    def _build_fields(self):
        fields_basic = [("First Name", self.first_name_var),
                        ("Last Name", self.last_name_var),
                        ("Date of Birth", self.dob_var)]
        fields_contact = [("Email Address", self.email_var),
                          ("Email Address 2", self.email2_var),
                          ("Phone Number", self.phone_var),
                          ("Address", self.address_var),
                          ("City", self.city_var),
                          ("State", self.state_var),
                          ("Zip Code", self.zip_var)]
        fields_membership = [("Badge Number", self.badge_number_var),
                             ("Membership Type", self.membership_type_var),
                             ("Join Date", self.join_date_var),
                             ("Sponsor", self.sponsor_var),
                             ("Card/Fob Internal Number", self.card_internal_var),
                             ("Card/Fob External Number", self.card_external_var)]

        def build_fields(frame, fields):
            for idx, (label, var) in enumerate(fields):
                ttk.Label(frame, text=label).grid(row=idx, column=0, sticky="e", padx=5, pady=2)
                if label == "Membership Type":
                    ttk.Combobox(frame, textvariable=var, values=self.membership_types, state="readonly")\
                        .grid(row=idx, column=1, sticky="w", padx=5, pady=2)
                else:
                    ttk.Entry(frame, textvariable=var).grid(row=idx, column=1, sticky="w", padx=5, pady=2)

        build_fields(self.tab_basic, fields_basic)
        build_fields(self.tab_contact, fields_contact)
        build_fields(self.tab_membership, fields_membership)

    def load_member(self):
        m = database.get_member_by_id(self.member_id)
        if not m:
            return
        (id_, badge, memtype, first, last, dob, email, phone, address, city, state,
         zipc, join, email2, sponsor, int_card, ext_card) = m[:17]
        self.badge_number_var.set(badge or "")
        self.membership_type_var.set(memtype or "")
        self.first_name_var.set(first or "")
        self.last_name_var.set(last or "")
        self.dob_var.set(dob or "")
        self.email_var.set(email or "")
        self.phone_var.set(phone or "")
        self.address_var.set(address or "")
        self.city_var.set(city or "")
        self.state_var.set(state or "")
        self.zip_var.set(zipc or "")
        self.join_date_var.set(join or "")
        self.email2_var.set(email2 or "")
        self.sponsor_var.set(sponsor or "")
        self.card_internal_var.set(int_card or "")
        self.card_external_var.set(ext_card or "")

    def save_member(self):
        data = (self.badge_number_var.get(), self.membership_type_var.get(),
                self.first_name_var.get(), self.last_name_var.get(), self.dob_var.get(),
                self.email_var.get(), self.phone_var.get(), self.address_var.get(), self.city_var.get(),
                self.state_var.get(), self.zip_var.get(), self.join_date_var.get(),
                self.email2_var.get(), self.sponsor_var.get(), self.card_internal_var.get(), self.card_external_var.get())
        if self.member_id:
            database.update_member(self.member_id, data)
        else:
            self.member_id = database.add_member(data)
        if self.on_save_callback:
            self.on_save_callback(self.member_id, self.membership_type_var.get())
        self.top.destroy()

    def save_basic_info(self): self.save_member()
    def save_contact(self): self.save_member()
    def save_membership_info(self): self.save_member()
