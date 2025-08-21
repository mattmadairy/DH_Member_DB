# work_hours_reporting_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import database
from report_base import BaseReportWindow
from member_form import MemberForm


class WorkHoursReportingWindow(BaseReportWindow):
    columns = ("badge", "name", "type", "total_hours", "last_shift")
    column_widths = (90, 220, 110, 100, 130)

    def __init__(self, parent):
        super().__init__(parent, "Work Hours Report", "work_hours_window_geometry")
        self.report_mode = "all"
        self.tree.bind("<Double-1>", self.on_row_double_click)

    # ---------- Setup top controls ----------
    def _setup_controls(self):
        # Top row frame for all controls
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        # Year label + spinbox
        tk.Label(top, text="Select Year:").pack(side="left", padx=(10,6))
        self.year_var = tk.StringVar(value=str(database.get_default_year()))
        tk.Spinbox(top, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left")

        # Group 1: Run Report buttons
        button_padx = 5
        tk.Button(top, text="Run All Work Hours", command=lambda: self.populate_report("all")).pack(side="left", padx=button_padx)
        tk.Button(top, text="Run Completed Shifts", command=lambda: self.populate_report("completed")).pack(side="left", padx=button_padx)
        tk.Button(top, text="Run Missing Shifts", command=lambda: self.populate_report("missing")).pack(side="left", padx=button_padx)

        # Spacer between Run Report buttons and Print/Export
        tk.Label(top, width=2).pack(side="left")  # small empty label as spacer

        # Group 2: Print / Export buttons
        tk.Button(top, text="Print Report", command=self.print_report).pack(side="left", padx=button_padx)
        tk.Button(top, text="Export CSV", command=self.export_csv).pack(side="left", padx=button_padx)

        # Membership type filters below
        filters = tk.Frame(self)
        filters.pack(fill="x", padx=10, pady=(0,8))
        tk.Label(filters, text="Include Types:").grid(row=0, column=0, sticky="w")

        self.membership_types = ["Probationary", "Associate", "Active", "Life", "Prospective", "Waitlist", "Former"]
        self.type_vars = {}
        defaults = {"Probationary", "Associate", "Active"}
        for col, mtype in enumerate(self.membership_types, start=1):
            var = tk.BooleanVar(value=(mtype in defaults))
            cb = tk.Checkbutton(filters, text=mtype, variable=var)
            cb.grid(row=0, column=col, sticky="w", padx=(8,0))
            self.type_vars[mtype] = var

    # ---------- Populate report ----------
    def populate_report(self, mode="all"):
        self.report_mode = mode
        year = str(self.year_var.get()).strip()
        selected = [t for t, var in self.type_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("No Types", "Select at least one membership type to include.")
            return

        try:
            if mode == "completed":
                rows = database.get_completed_work_hours(year, selected)
            elif mode == "missing":
                rows = database.get_missing_work_hours(year, selected)
            else:
                rows = database.get_work_hours(year, selected)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch work hours: {e}")
            return

        self.clear_tree()
        for first, last, mtype, total_hours, last_shift, badge in rows:
            self.tree.insert("", "end", values=(
                badge or "", f"{last}, {first}", mtype,
                f"{total_hours:.2f}" if total_hours else "0.00",
                last_shift or ""
            ))

    # ---------- Double-click to open MemberForm ----------
    def _member_id_by_badge(self, badge_text):
        try:
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM members WHERE badge_number=? AND deleted=0 LIMIT 1", (str(badge_text),))
            row = c.fetchone()
            conn.close()
            return row[0] if row else None
        except Exception:
            return None

    def on_row_double_click(self, event):
        item = self.tree.focus()
        if not item:
            return
        vals = self.tree.item(item, "values")
        badge = vals[0] if vals else None
        if not badge:
            messagebox.showwarning("Open Member", "No badge number on the selected row.")
            return
        member_id = self._member_id_by_badge(badge)
        if not member_id:
            messagebox.showerror("Open Member", f"No member found with badge '{badge}'.")
            return

        MemberForm(
            self,
            member_id=member_id,
            open_tab="work_hours"
        )
