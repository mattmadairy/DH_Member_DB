import tkinter as tk
from tkinter import ttk, messagebox
import database
import calendar

class AttendanceReport(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.year_var = tk.IntVar()
        self.month_var = tk.StringVar(value="All")
        self.columns = ("badge", "name", "status")  # will update dynamically for "All"
        self.column_widths = (90, 260, 120)

        self._setup_controls()
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, pady=5)

        self.populate_report()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        # Year scrollbox: default from settings table
        try:
            default_year = database.get_setting("default_year")
            default_year = int(default_year)
        except Exception:
            default_year = 2025

        self.year_var.set(default_year)
        tk.Label(frame, text="Year:").pack(side="left", padx=(10,0))
        tk.Spinbox(frame, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left", padx=(0,10))

        # Month dropdown
        tk.Label(frame, text="Month:").pack(side="left")
        months = ["All"] + list(calendar.month_name[1:])
        month_cb = ttk.Combobox(frame, values=months, textvariable=self.month_var, state="readonly", width=10)
        month_cb.pack(side="left", padx=(0,10))
        month_cb.configure(background="white")  # white background

        # Run Report button
        tk.Button(frame, text="Run Report", command=self.populate_report).pack(side="left", padx=(10,0))

    def populate_report(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        month_name = self.month_var.get()

        try:
            members = database.get_all_members()
            for m in members:
                member_id = m[0]
                badge = m[1]
                name = f"{m[3]} {m[4]}"

                if month_name == "All":
                    # Total meetings attended/exempted for the year
                    total = database.count_member_attendance(member_id, year)
                    self.tree.insert("", "end", values=(badge, name, total))
                else:
                    month_index = list(calendar.month_name).index(month_name)
                    # Only show members with entries for that month
                    status = database.get_member_status_for_month(member_id, year, month_index)
                    if status:
                        self.tree.insert("", "end", values=(badge, name, status))
        except Exception as e:
            messagebox.showerror("Attendance Report", f"Failed to fetch attendance data:\n{e}")
