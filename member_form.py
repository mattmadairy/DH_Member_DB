import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

class MemberForm:
    def __init__(self, parent, member_id=None, on_save_callback=None, open_tab=None, on_dues_changed=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        self.on_save_callback = on_save_callback  # existing callback (unchanged)
        self.on_dues_changed = on_dues_changed    # ✅ new: notify parent when dues change

        # ✅ Bind Enter/Return to save member (when not editing dues)
        self.top.bind("<Return>", lambda event: self.save_member())

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.top)
        self.notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Frames for each tab
        self.tab_basic = ttk.Frame(self.notebook)
        self.tab_contact = ttk.Frame(self.notebook)
        self.tab_membership = ttk.Frame(self.notebook)
        self.tab_dues = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_basic, text="Basic Info")
        self.notebook.add(self.tab_contact, text="Contact")
        self.notebook.add(self.tab_membership, text="Membership")
        self.notebook.add(self.tab_dues, text="Dues History")

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

        # Membership type options
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

        # Helper to build labeled fields
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

        # --- Dues History Tab ---
        self.dues_tree = ttk.Treeview(
            self.tab_dues,
            columns=("year", "amount", "date", "method", "notes"),
            show="headings"
        )
        self.dues_tree.heading("year", text="Year")
        self.dues_tree.heading("amount", text="Amount")
        self.dues_tree.heading("date", text="Date")
        self.dues_tree.heading("method", text="Method")
        self.dues_tree.heading("notes", text="Notes")

        # Column widths
        self.dues_tree.column("year", width=60, anchor="center")
        self.dues_tree.column("amount", width=80, anchor="w")
        self.dues_tree.column("date", width=100, anchor="w")
        self.dues_tree.column("method", width=90, anchor="w")
        self.dues_tree.column("notes", width=200, anchor="w")

        self.dues_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        # Double-click or Enter to edit
        self.dues_tree.bind("<Double-1>", self.on_payment_double_click)
        self.dues_tree.bind("<Return>", self.on_payment_enter)

        # Entry fields for adding new payment
        try:
            default_year = str(database.get_default_year())
        except Exception:
            default_year = datetime.today().strftime("%Y")

        self.dues_year_var = tk.StringVar(value=default_year)
        self.dues_amount_var = tk.StringVar()
        self.dues_date_var = tk.StringVar(value=datetime.today().strftime("%Y-%m-%d"))
        self.dues_method_var = tk.StringVar()
        self.dues_notes_var = tk.StringVar()

        ttk.Label(self.tab_dues, text="Year").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_year_var, width=6).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Date").grid(row=1, column=2, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_date_var, width=12).grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Amount").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_amount_var, width=10).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Method").grid(row=2, column=2, padx=5, pady=2, sticky="e")
        method_cb = ttk.Combobox(self.tab_dues, textvariable=self.dues_method_var,
                                 values=["Cash", "Check", "Electronic"], state="readonly", width=12)
        method_cb.grid(row=2, column=3, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Notes").grid(row=3, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_notes_var, width=25).grid(row=3, column=1, columnspan=3, padx=5, pady=2)

        ttk.Button(self.tab_dues, text="Add Payment", command=self.add_dues_payment).grid(row=4, column=0, pady=5)
        ttk.Button(self.tab_dues, text="Edit Payment", command=self.edit_dues_payment).grid(row=4, column=1, pady=5)
        ttk.Button(self.tab_dues, text="Delete Payment", command=self.delete_dues_payment).grid(row=4, column=2, pady=5)

        # Save button at bottom
        ttk.Button(self.top, text="Save Member", command=self.save_member).grid(row=1, column=0, pady=10)

        # If editing, load existing member
        if self.member_id:
            self.load_member()
            self.load_dues_history()

        # ✅ Open directly on the requested tab
        if open_tab == "dues":
            self.notebook.select(self.tab_dues)

    # --- Load member info ---
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

    # --- Save member info ---
    def save_member(self):
        try:
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

            member_name = f"{self.first_name_var.get()} {self.last_name_var.get()}"
            messagebox.showinfo("Success", f"Member '{member_name}' saved successfully!")

            # existing callback retained
            if self.on_save_callback:
                self.on_save_callback(self.member_id, self.membership_type_var.get())

            self.top.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save member: {e}")

    # --- Load dues history ---
    def load_dues_history(self):
        if not self.member_id:
            return
        for row in self.dues_tree.get_children():
            self.dues_tree.delete(row)
        dues_records = database.get_dues_by_member(self.member_id)
        for record in dues_records:
            # record = (id, member_id, amount, payment_date, year, method, notes)
            amount = f"{float(record[2]):.2f}" if record[2] not in (None, "") else ""
            payment_date = record[3]
            year = record[4]
            method = record[5]
            notes = record[6] if len(record) > 6 else ""
            self.dues_tree.insert("", "end", iid=record[0], values=(year, amount, payment_date, method, notes))

    # --- Add new payment ---
    def add_dues_payment(self):
        if not self.member_id:
            messagebox.showerror("Error", "Save member first before adding dues.")
            return
        try:
            amount = float(self.dues_amount_var.get())
            date = self.dues_date_var.get()
            year = self.dues_year_var.get()
            method = self.dues_method_var.get()
            notes = self.dues_notes_var.get()

            database.add_dues_payment(self.member_id, amount, date, method, notes, year)
            self.load_dues_history()
            self.dues_amount_var.set("")
            self.dues_notes_var.set("")

            # ✅ notify parent window to refresh report
            if self.on_dues_changed:
                self.on_dues_changed()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add payment: {e}")

    # --- Popup to edit selected payment ---
    def open_edit_payment_popup(self, dues_id):
        record = database.get_dues_payment_by_id(dues_id)
        if not record:
            messagebox.showerror("Error", "Payment record not found.")
            return

        popup = tk.Toplevel(self.top)
        popup.title("Edit Payment")
        popup.grab_set()  # modal

        amount_var = tk.StringVar(value=f"{float(record[2]):.2f}")

        date_var = tk.StringVar(value=record[3])
        year_var = tk.StringVar(value=record[4])
        method_var = tk.StringVar(value=record[5])
        notes_var = tk.StringVar(value=record[6] if len(record) > 6 else "")

        ttk.Label(popup, text="Year").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(popup, textvariable=year_var, width=6).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(popup, text="Date").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(popup, textvariable=date_var).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(popup, text="Amount").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(popup, textvariable=amount_var).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(popup, text="Method").grid(row=3, column=0, padx=5, pady=2, sticky="e")
        method_cb = ttk.Combobox(popup, textvariable=method_var,
                                 values=["Cash", "Check", "Electronic"], state="readonly")
        method_cb.grid(row=3, column=1, padx=5, pady=2)

        ttk.Label(popup, text="Notes").grid(row=4, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(popup, textvariable=notes_var).grid(row=4, column=1, padx=5, pady=2)

        def save_changes(event=None):
            try:
                database.update_dues_payment(
                    dues_id,
                    float(amount_var.get()),
                    date_var.get(),
                    method_var.get(),
                    notes_var.get(),
                    year_var.get()
                )
                self.load_dues_history()
                popup.destroy()

                # ✅ notify parent window to refresh report
                if self.on_dues_changed:
                    self.on_dues_changed()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to update payment: {e}")

        ttk.Button(popup, text="Save", command=save_changes).grid(row=5, column=0, columnspan=2, pady=5)
        popup.bind("<Return>", save_changes)

    # --- Edit selected payment (button) ---
    def edit_dues_payment(self):
        selected = self.dues_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a payment to edit.")
            return
        dues_id = int(selected[0])
        self.open_edit_payment_popup(dues_id)

    # --- Double-click on row ---
    def on_payment_double_click(self, event):
        selected = self.dues_tree.selection()
        if not selected:
            return
        dues_id = int(selected[0])
        self.open_edit_payment_popup(dues_id)

    # --- Enter key on row ---
    def on_payment_enter(self, event):
        selected = self.dues_tree.selection()
        if not selected:
            return
        dues_id = int(selected[0])
        self.open_edit_payment_popup(dues_id)

    # --- Delete selected payment ---
    def delete_dues_payment(self):
        selected = self.dues_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Select a payment to delete.")
            return
        dues_id = int(selected[0])
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this payment?"):
            try:
                database.delete_dues_payment(dues_id)
                self.load_dues_history()

                # ✅ notify parent window to refresh report
                if self.on_dues_changed:
                    self.on_dues_changed()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete payment: {e}")
