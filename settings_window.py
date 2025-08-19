import tkinter as tk
from tkinter import messagebox
import database


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x320")
        self.resizable(False, False)

        # Load settings
        self.settings = database.get_all_settings()

        row = 0
        tk.Label(self, text="Dues Amounts", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, pady=5)

        row += 1
        tk.Label(self, text="Probationary:").grid(row=row, column=0, sticky="w", padx=10)
        self.prob_var = tk.StringVar(value=self.settings.get("dues_probationary", "150"))
        tk.Entry(self, textvariable=self.prob_var, justify="left").grid(row=row, column=1, padx=10)

        row += 1
        tk.Label(self, text="Associate:").grid(row=row, column=0, sticky="w", padx=10)
        self.assoc_var = tk.StringVar(value=self.settings.get("dues_associate", "300"))
        tk.Entry(self, textvariable=self.assoc_var, justify="left").grid(row=row, column=1, padx=10)

        row += 1
        tk.Label(self, text="Active:").grid(row=row, column=0, sticky="w", padx=10)
        self.active_var = tk.StringVar(value=self.settings.get("dues_active", "150"))
        tk.Entry(self, textvariable=self.active_var, justify="left").grid(row=row, column=1, padx=10)

        # NEW: Life Member dues
        row += 1
        tk.Label(self, text="Life:").grid(row=row, column=0, sticky="w", padx=10)
        self.life_var = tk.StringVar(value=self.settings.get("dues_life", "0"))
        tk.Entry(self, textvariable=self.life_var, justify="left", state="disabled").grid(row=row, column=1, padx=10)

        row += 2
        tk.Label(self, text="Default Year:", font=("Arial", 12, "bold")).grid(row=row, column=0, sticky="w", padx=10)
        self.year_var = tk.StringVar(value=self.settings.get("default_year"))
        tk.Entry(self, textvariable=self.year_var, justify="left").grid(row=row, column=1, padx=10)

        row += 2
        tk.Button(self, text="Save", command=self.save_settings).grid(row=row, column=0, columnspan=2, pady=15)

    def save_settings(self):
        try:
            database.set_setting("dues_probationary", int(self.prob_var.get()))
            database.set_setting("dues_associate", int(self.assoc_var.get()))
            database.set_setting("dues_active", int(self.active_var.get()))
            database.set_setting("dues_life", 0)   # NEW
            database.set_setting("default_year", int(self.year_var.get()))
            messagebox.showinfo("Saved", "Settings have been updated.")
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for dues and year.")
