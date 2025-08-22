# member_form.py
import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

class MemberForm:
    def __init__(self, parent, member_id=None, on_save_callback=None,
                 open_tab=None, on_dues_changed=None, on_hours_changed=None):

        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        self.on_save_callback = on_save_callback
        self.on_dues_changed = on_dues_changed
        self.on_hours_changed = on_hours_changed

        self.top.bind("<Return>", lambda event: self.save_member())

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.top)
        self.notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Frames for each tab
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

        # Form variables
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

        self.membership_types = [
            "Probationary", "Associate", "Active",
            "Life", "Prospective", "Wait List", "Former"
        ]

        # --- Define fields per tab ---
        fields_basic = [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var),
        ]

        fields_contact = [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var),
        ]

        fields_membership = [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var),
        ]

        # --- Build fields per tab ---
        def build_fields(frame, fields):
            for idx, (label, var) in enumerate(fields):
                ttk.Label(frame, text=label).grid(row=idx, column=0, sticky="e", padx=5, pady=2)
                if label == "Membership Type":
                    cb = ttk.Combobox(frame, textvariable=var, values=self.membership_types, state="readonly")
                    cb.grid(row=idx, column=1, sticky="w", padx=5, pady=2)
                else:
                    ttk.Entry(frame, textvariable=var).grid(row=idx, column=1, sticky="w", padx=5, pady=2)

        build_fields(self.tab_basic, fields_basic)
        build_fields(self.tab_contact, fields_contact)
        build_fields(self.tab_membership, fields_membership)

        # --- Add Save buttons per tab ---
        ttk.Button(self.tab_basic, text="Save", command=self.save_basic_info).grid(row=5, column=0, pady=5)
        ttk.Button(self.tab_contact, text="Save", command=self.save_contact).grid(row=10, column=0, pady=5)
        ttk.Button(self.tab_membership, text="Save", command=self.save_membership_info).grid(row=10, column=0, pady=5)

        # --- Dues History Tab ---
        self.dues_tree = ttk.Treeview(
            self.tab_dues,
            columns=("year", "amount", "date", "method", "notes"),
            show="headings"
        )
        for col, width in [("year",60),("amount",80),("date",100),("method",90),("notes",200)]:
            self.dues_tree.heading(col, text=col.title())
            self.dues_tree.column(col, width=width, anchor="w")
        self.dues_tree.column("year", anchor="center")
        self.dues_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        try:
            default_year = str(database.get_default_year())
        except Exception:
            default_year = datetime.now().strftime("%Y")

        self.dues_year_var = tk.StringVar(value=default_year)
        self.dues_amount_var = tk.StringVar()
        self.dues_date_var = tk.StringVar(value=datetime.today().strftime("%m/%d/%Y"))
        self.dues_method_var = tk.StringVar()
        self.dues_notes_var = tk.StringVar()

        ttk.Label(self.tab_dues, text="Year").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_dues, textvariable=self.dues_year_var, width=6).grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(self.tab_dues, text="Date").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_dues, textvariable=self.dues_date_var, width=12).grid(row=1, column=3, padx=5, pady=2)
        ttk.Label(self.tab_dues, text="Amount").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_dues, textvariable=self.dues_amount_var, width=10).grid(row=2, column=1, padx=5, pady=2)
        ttk.Label(self.tab_dues, text="Method").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        method_cb = ttk.Combobox(self.tab_dues, textvariable=self.dues_method_var,
                                 values=["Cash", "Check", "Electronic"], state="readonly", width=12)
        method_cb.grid(row=2, column=3, padx=5, pady=2)
        ttk.Label(self.tab_dues, text="Notes").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_dues, textvariable=self.dues_notes_var, width=25).grid(row=3, column=1, columnspan=3, padx=5, pady=2)

        ttk.Button(self.tab_dues, text="Add Payment", command=self.add_dues_payment).grid(row=4, column=0, pady=5)
        ttk.Button(self.tab_dues, text="Edit Payment", command=self.edit_dues_payment).grid(row=4, column=1, pady=5)
        ttk.Button(self.tab_dues, text="Delete Payment", command=self.delete_dues_payment).grid(row=4, column=2, pady=5)

        # --- Work Hours Tab ---
        self.wh_tree = ttk.Treeview(
            self.tab_work_hours,
            columns=("date","work_type","hours","notes"),
            show="headings"
        )
        self.wh_tree.heading("date", text="Date")
        self.wh_tree.heading("work_type", text="Work Type")
        self.wh_tree.heading("hours", text="Hours")
        self.wh_tree.heading("notes", text="Notes")

        self.wh_tree.column("date", width=100, anchor="w")
        self.wh_tree.column("hours", width=60, anchor="center")
        self.wh_tree.column("work_type", width=100, anchor="w")
        self.wh_tree.column("notes", width=200, anchor="w")

        self.wh_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        self.wh_date_var = tk.StringVar(value=datetime.now().strftime("%m/%d/%Y"))
        self.wh_type_var = tk.StringVar()
        self.wh_hours_var = tk.StringVar()
        self.wh_notes_var = tk.StringVar()

        ttk.Label(self.tab_work_hours, text="Date").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_work_hours, textvariable=self.wh_date_var, width=12).grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(self.tab_work_hours, text="Work Type").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_work_hours, textvariable=self.wh_type_var, width=20).grid(row=1, column=3, padx=5, pady=2)
        ttk.Label(self.tab_work_hours, text="Hours").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_work_hours, textvariable=self.wh_hours_var, width=6).grid(row=2, column=1, padx=5, pady=2)
        ttk.Label(self.tab_work_hours, text="Notes").grid(row=2, column=2, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_work_hours, textvariable=self.wh_notes_var, width=25).grid(row=2, column=3, padx=5, pady=2)

        ttk.Button(self.tab_work_hours, text="Add Entry", command=self.add_work_hours).grid(row=3, column=0, pady=5)
        ttk.Button(self.tab_work_hours, text="Edit Entry", command=self.edit_work_hours).grid(row=3, column=1, pady=5)
        ttk.Button(self.tab_work_hours, text="Delete Entry", command=self.delete_work_hours).grid(row=3, column=2, pady=5)

        # --- Attendance Tab ---
        self.att_tree = ttk.Treeview(
            self.tab_attendance,
            columns=("date","attended","notes"),
            show="headings"
        )
        self.att_tree.heading("date", text="Meeting Date")
        self.att_tree.heading("attended", text="Attended")
        self.att_tree.heading("notes", text="Notes")

        self.att_tree.column("date", width=100, anchor="w")
        self.att_tree.column("attended", width=80, anchor="center")
        self.att_tree.column("notes", width=200, anchor="w")

        self.att_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        self.att_date_var = tk.StringVar(value=datetime.now().strftime("%m/%d/%Y"))
        self.att_attended_var = tk.IntVar(value=1)
        self.att_notes_var = tk.StringVar()

        ttk.Label(self.tab_attendance, text="Date").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_attendance, textvariable=self.att_date_var, width=12).grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(self.tab_attendance, text="Attended").grid(row=1, column=2, sticky="e", padx=5, pady=2)
        ttk.Checkbutton(self.tab_attendance, variable=self.att_attended_var).grid(row=1, column=3, sticky="w", padx=5, pady=2)
        ttk.Label(self.tab_attendance, text="Notes").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(self.tab_attendance, textvariable=self.att_notes_var, width=25).grid(row=2, column=1, columnspan=3, padx=5, pady=2)

        ttk.Button(self.tab_attendance, text="Add Entry", command=self.add_attendance).grid(row=3, column=0, pady=5)
        ttk.Button(self.tab_attendance, text="Edit Entry", command=self.edit_attendance).grid(row=3, column=1, pady=5)
        ttk.Button(self.tab_attendance, text="Delete Entry", command=self.delete_attendance).grid(row=3, column=2, pady=5)

        if self.member_id:
            self.load_member()
            self.load_dues_history()
            self.load_work_hours()
            self.load_attendance()

        if open_tab == "dues":
            self.notebook.select(self.tab_dues)
        elif open_tab == "work_hours":
            self.notebook.select(self.tab_work_hours)
        elif open_tab == "attendance":
            self.notebook.select(self.tab_attendance)

    # --- Member ---
    def load_member(self):
        member = database.get_member_by_id(self.member_id)
        if member:
            self.badge_number_var.set(member[1])
            self.membership_type_var.set(member[2] if member[2] in self.membership_types else "")
            self.first_name_var.set(member[3])
            self.last_name_var.set(member[4])
            self.dob_var.set(member[5])
            self.email_var.set(member[6])
            self.phone_var.set(member[7])
            self.address_var.set(member[8])
            self.city_var.set(member[9])
            self.state_var.set(member[10])
            self.zip_var.set(member[11])
            self.join_date_var.set(member[12])
            self.email2_var.set(member[13])
            self.sponsor_var.set(member[14])
            self.card_internal_var.set(member[15])
            self.card_external_var.set(member[16])

    def save_member(self):
        data = (
            self.badge_number_var.get(),
            self.membership_type_var.get(),
            self.first_name_var.get(),
            self.last_name_var.get(),
            self.dob_var.get(),
            self.email_var.get(),
            self.phone_var.get(),
            self.address_var.get(),
            self.city_var.get(),
            self.state_var.get(),
            self.zip_var.get(),
            self.join_date_var.get(),
            self.email2_var.get(),
            self.sponsor_var.get(),
            self.card_internal_var.get(),
            self.card_external_var.get()
        )
        if self.member_id:
            database.update_member(self.member_id, data)
        else:
            self.member_id = database.add_member(data)
        if self.on_save_callback:
            self.on_save_callback(self.member_id, self.membership_type_var.get())
        self.top.destroy()

    # --- Basic / Contact / Membership Save ---
    def save_basic_info(self):
        database.update_member_basic(self.member_id, self.first_name_var.get(),
                                     self.last_name_var.get(), self.dob_var.get())
    def save_contact(self):
        database.update_member_contact(self.member_id, self.email_var.get(),
                                       self.email2_var.get(), self.phone_var.get(),
                                       self.address_var.get(), self.city_var.get(),
                                       self.state_var.get(), self.zip_var.get())
    def save_membership_info(self):
        database.update_member_membership(self.member_id, self.badge_number_var.get(),
                                          self.membership_type_var.get(), self.join_date_var.get(),
                                          self.sponsor_var.get(), self.card_internal_var.get(),
                                          self.card_external_var.get())

    # --- Dues Tab ---
    def load_dues_history(self):
        if not self.member_id:
            return
        for row in self.dues_tree.get_children():
            self.dues_tree.delete(row)
        records = database.get_dues_by_member(self.member_id)
        for record in records:
            self.dues_tree.insert("", "end", iid=record[0], values=(
                record[4],
                f"{record[2]:.2f}",
                record[3],
                record[5] or "",
                record[6] or ""
            ))

    def add_dues_payment(self):
        if not self.member_id:
            messagebox.showerror("Error", "Save member first before adding dues.")
            return
        try:
            amount = float(self.dues_amount_var.get())
        except ValueError:
            messagebox.showerror("Invalid Amount", "Amount must be numeric.")
            return

        database.add_dues_payment(self.member_id, amount, self.dues_date_var.get(),
                                  self.dues_method_var.get() or None, self.dues_notes_var.get() or None,
                                  self.dues_year_var.get())
        self.load_dues_history()
        self.dues_amount_var.set("")
        self.dues_notes_var.set("")

    def edit_dues_payment(self):
        selected = self.dues_tree.selection()
        if not selected:
            return
        payment_id = int(selected[0])
        record = database.get_dues_by_id(payment_id)
        if not record:
            return
        popup = tk.Toplevel(self.top)
        popup.title("Edit Payment")
        popup.grab_set()
        year_var = tk.StringVar(value=record[4])
        amount_var = tk.StringVar(value=str(record[2]))
        date_var = tk.StringVar(value=record[3])
        method_var = tk.StringVar(value=record[5] or "")
        notes_var = tk.StringVar(value=record[6] or "")
        ttk.Label(popup, text="Year").grid(row=0, column=0)
        ttk.Entry(popup, textvariable=year_var, width=6).grid(row=0, column=1)
        ttk.Label(popup, text="Amount").grid(row=1, column=0)
        ttk.Entry(popup, textvariable=amount_var, width=10).grid(row=1, column=1)
        ttk.Label(popup, text="Date").grid(row=2, column=0)
        ttk.Entry(popup, textvariable=date_var, width=12).grid(row=2, column=1)
        ttk.Label(popup, text="Method").grid(row=3, column=0)
        ttk.Entry(popup, textvariable=method_var, width=12).grid(row=3, column=1)
        ttk.Label(popup, text="Notes").grid(row=4, column=0)
        ttk.Entry(popup, textvariable=notes_var, width=25).grid(row=4, column=1)
        def save_changes():
            database.update_dues_payment(payment_id, float(amount_var.get()), date_var.get(),
                                         method_var.get() or None, notes_var.get() or None,
                                         year_var.get())
            popup.destroy()
            self.load_dues_history()
        ttk.Button(popup, text="Save", command=save_changes).grid(row=5, column=0, columnspan=2)
        popup.bind("<Return>", lambda e: save_changes())

    def delete_dues_payment(self):
        selected = self.dues_tree.selection()
        if not selected:
            return
        payment_id = int(selected[0])
        if messagebox.askyesno("Confirm", "Delete selected payment?"):
            database.delete_dues_payment(payment_id)
            self.load_dues_history()

    # --- Work Hours Tab ---
    def load_work_hours(self):
        if not self.member_id:
            return
        for row in self.wh_tree.get_children():
            self.wh_tree.delete(row)
        records = database.get_work_hours_by_member(self.member_id)
        for record in records:
            self.wh_tree.insert("", "end", iid=record[0], values=(
                record[2],
                record[4] or "",
                record[3],
                record[5] or ""
            ))

    def add_work_hours(self):
        if not self.member_id:
            return
        database.add_work_hours(self.member_id, self.wh_date_var.get(),
                                float(self.wh_hours_var.get()), self.wh_type_var.get() or None,
                                self.wh_notes_var.get() or None)
        self.load_work_hours()
        self.wh_hours_var.set("")
        self.wh_type_var.set("")
        self.wh_notes_var.set("")
        
        if self.on_hours_changed:
            self.on_hours_changed()

    def edit_work_hours(self):
        selected = self.wh_tree.selection()
        if not selected:
            return
        wh_id = int(selected[0])
        record = database.get_work_hours_by_id(wh_id)
        if not record:
            return
        popup = tk.Toplevel(self.top)
        popup.title("Edit Work Hours")
        popup.grab_set()
        date_var = tk.StringVar(value=record[2])
        type_var = tk.StringVar(value=record[4] or "")
        hours_var = tk.StringVar(value=str(record[3]))
        notes_var = tk.StringVar(value=record[5] or "")
        ttk.Label(popup, text="Date").grid(row=0, column=0)
        ttk.Entry(popup, textvariable=date_var, width=12).grid(row=0, column=1)
        ttk.Label(popup, text="Work Type").grid(row=1, column=0)
        ttk.Entry(popup, textvariable=type_var, width=20).grid(row=1, column=1)
        ttk.Label(popup, text="Hours").grid(row=2, column=0)
        ttk.Entry(popup, textvariable=hours_var, width=6).grid(row=2, column=1)
        ttk.Label(popup, text="Notes").grid(row=3, column=0)
        ttk.Entry(popup, textvariable=notes_var, width=25).grid(row=3, column=1)
        def save_changes():
            database.update_work_hours(wh_id, date_var.get(), float(hours_var.get()),
                                       type_var.get() or None, notes_var.get() or None)
            popup.destroy()
            self.load_work_hours()
            
            if self.on_hours_changed:
                self.on_hours_changed()

        ttk.Button(popup, text="Save", command=save_changes).grid(row=4, column=0, columnspan=2)
        popup.bind("<Return>", lambda e: save_changes())

    def delete_work_hours(self):
        selected = self.wh_tree.selection()
        if not selected:
            return
        wh_id = int(selected[0])
        if messagebox.askyesno("Confirm", "Delete selected work hour entry?"):
            database.delete_work_hours(wh_id)
            self.load_work_hours()
            
        if self.on_hours_changed:
            self.on_hours_changed()

    # --- Attendance Methods ---
    def load_attendance(self):
        if not self.member_id:
            return
        for row in self.att_tree.get_children():
            self.att_tree.delete(row)
        records = database.get_meeting_attendance(self.member_id)
        for record in records:
            self.att_tree.insert("", "end", iid=record[0], values=(
                record[2],
                "Yes" if record[3] else "No",
                record[4] or ""
            ))

    def add_attendance(self):
        if not self.member_id:
            return
        database.add_meeting_attendance(
            self.member_id,
            self.att_date_var.get(),
            self.att_attended_var.get(),
            self.att_notes_var.get() or None
        )
        self.load_attendance()
        self.att_notes_var.set("")
        self.att_attended_var.set(1)

    def edit_attendance(self):
        selected = self.att_tree.selection()
        if not selected:
            return
        att_id = int(selected[0])
        records = database.get_meeting_attendance(self.member_id)
        record = [r for r in records if r[0]==att_id][0]

        popup = tk.Toplevel(self.top)
        popup.title("Edit Attendance")
        popup.grab_set()

        date_var = tk.StringVar(value=record[2])
        attended_var = tk.IntVar(value=record[3])
        notes_var = tk.StringVar(value=record[4] or "")

        ttk.Label(popup, text="Date").grid(row=0, column=0)
        ttk.Entry(popup, textvariable=date_var, width=12).grid(row=0, column=1)
        ttk.Label(popup, text="Attended").grid(row=1, column=0)
        ttk.Checkbutton(popup, variable=attended_var).grid(row=1, column=1)
        ttk.Label(popup, text="Notes").grid(row=2, column=0)
        ttk.Entry(popup, textvariable=notes_var, width=25).grid(row=2, column=1)

        def save_changes():
            database.update_meeting_attendance(att_id,
                                               meeting_date=date_var.get(),
                                               attended=attended_var.get(),
                                               notes=notes_var.get() or None)
            popup.destroy()
            self.load_attendance()

        ttk.Button(popup, text="Save", command=save_changes).grid(row=3, column=0, columnspan=2)
        popup.bind("<Return>", lambda e: save_changes())

    def delete_attendance(self):
        selected = self.att_tree.selection()
        if not selected:
            return
        att_id = int(selected[0])
        if messagebox.askyesno("Confirm", "Delete selected attendance?"):
            database.delete_meeting_attendance(att_id)
            self.load_attendance()
