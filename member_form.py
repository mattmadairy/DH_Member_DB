import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime

class MemberForm:
    def __init__(self, parent, member_id=None, on_save_callback=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        self.on_save_callback = on_save_callback  # ✅ callback for GUI updates

        # ✅ Bind Enter/Return to save member
        self.top.bind("<Return>", lambda event: self.save_member())

        # Notebook (tabs)
        notebook = ttk.Notebook(self.top)
        notebook.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Frames for each tab
        self.tab_basic = ttk.Frame(notebook)
        self.tab_contact = ttk.Frame(notebook)
        self.tab_membership = ttk.Frame(notebook)
        self.tab_dues = ttk.Frame(notebook)

        notebook.add(self.tab_basic, text="Basic Info")
        notebook.add(self.tab_contact, text="Contact")
        notebook.add(self.tab_membership, text="Membership")
        notebook.add(self.tab_dues, text="Dues History")

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
        self.dues_tree = ttk.Treeview(self.tab_dues, columns=("amount", "date", "method", "notes"), show="headings")
        self.dues_tree.heading("amount", text="Amount")
        self.dues_tree.heading("date", text="Date")
        self.dues_tree.heading("method", text="Method")
        self.dues_tree.heading("notes", text="Notes")
        self.dues_tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)

        # Entry fields for adding new payment
        self.dues_amount_var = tk.StringVar()
        self.dues_date_var = tk.StringVar(value=datetime.today().strftime("%Y-%m-%d"))
        self.dues_method_var = tk.StringVar()
        self.dues_notes_var = tk.StringVar()

        ttk.Label(self.tab_dues, text="Amount").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_amount_var).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Date").grid(row=1, column=2, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_date_var).grid(row=1, column=3, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Method").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_method_var).grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(self.tab_dues, text="Notes").grid(row=2, column=2, padx=5, pady=2, sticky="e")
        ttk.Entry(self.tab_dues, textvariable=self.dues_notes_var).grid(row=2, column=3, padx=5, pady=2)

        ttk.Button(self.tab_dues, text="Add Payment", command=self.add_dues_payment).grid(row=3, column=0, columnspan=4, pady=5)

        # Save button at bottom
        ttk.Button(self.top, text="Save Member", command=self.save_member).grid(row=1, column=0, pady=10)

        # If editing, load existing member
        if self.member_id:
            self.load_member()
            self.load_dues_history()

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

            # ✅ Call GUI callback with id + type
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
            # record = (id, member_id, amount, payment_date, method, notes)
            self.dues_tree.insert("", "end", values=(record[2], record[3], record[4], record[5]))

    # --- Add new payment ---
    def add_dues_payment(self):
        if not self.member_id:
            messagebox.showerror("Error", "Save member first before adding dues.")
            return
        try:
            amount = float(self.dues_amount_var.get())
            date = self.dues_date_var.get()
            method = self.dues_method_var.get()
            notes = self.dues_notes_var.get()
            database.add_dues_payment(self.member_id, amount, date, method, notes)
            self.load_dues_history()
            self.dues_amount_var.set("")
            self.dues_notes_var.set("")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add payment: {e}")
