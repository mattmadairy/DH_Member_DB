import tkinter as tk
from tkinter import ttk, messagebox
import database

class MemberForm:
    def __init__(self, parent, member_id=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        self.member_id = member_id
        # ✅ Bind Enter/Return to save
        self.top.bind("<Return>", lambda event: self.save_member())

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

        # Membership type options (expanded list)
        self.membership_types = [
            "Probationary",
            "Associate",
            "Active",
            "Life",
            "Prospective",
            "Wait List",
            "Former"
        ]

        # Labels + Entries
        fields = [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var),
            ("Email Address", self.email_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var),
            ("Join Date", self.join_date_var),
            ("Email Address 2", self.email2_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var),
        ]

        for idx, (label, var) in enumerate(fields):
            ttk.Label(self.top, text=label).grid(row=idx, column=0, sticky="e", padx=5, pady=2)

            if label == "Membership Type":
                # Dropdown for member type
                cb = ttk.Combobox(self.top, textvariable=var, values=self.membership_types, state="readonly")
                cb.grid(row=idx, column=1, sticky="w", padx=5, pady=2)
            else:
                ttk.Entry(self.top, textvariable=var).grid(row=idx, column=1, sticky="w", padx=5, pady=2)

        # Save button
        ttk.Button(self.top, text="Save", command=self.save_member).grid(row=len(fields), column=0, columnspan=2, pady=10)

        # If editing, load data
        if self.member_id:
            self.load_member()

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
        try:
            if self.member_id:
                database.update_member(
                    self.member_id,
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
            else:
                database.add_member(
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
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save member: {e}")
