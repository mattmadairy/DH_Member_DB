# work_hours_reporting_window.py
import tkinter as tk
from tkinter import messagebox

import database
import member_form
from report_base import BaseReportWindow


class WorkHoursReportingWindow(BaseReportWindow):
    columns = ("badge", "name", "hours")
    column_widths = (90, 260, 100)

    def __init__(self, parent):
        super().__init__(parent, "Work Hours Report", "work_hours_report_geometry")

        # Default to same size as dues window if no saved geometry
        try:
            if not self.get_geometry_setting():
                self.geometry("900x560")
        except Exception:
            self.geometry("900x560")

        self.tree.bind("<Double-1>", self.on_row_double_click)

    # ---------- Setup top controls ----------
    def _setup_controls(self):
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        tk.Label(top, text="Select Year:").pack(side="left", padx=(10, 6))
        self.year_var = tk.StringVar(value=str(database.get_default_year()))
        tk.Spinbox(top, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left")

        tk.Button(top, text="Run Report", command=self.populate_report).pack(side="left", padx=10)
        tk.Button(top, text="Print Report", command=self.print_report).pack(side="left", padx=10)
        tk.Button(top, text="Export CSV", command=self.export_csv).pack(side="left", padx=2)

    # ---------- Populate report ----------
    def populate_report(self):
        year = str(self.year_var.get()).strip()
        try:
            # Should now return rows like:
            # (first, last, badge, total_hours)
            rows = database.get_work_hours_by_year(year)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch work hours: {e}")
            return

        self.clear_tree()

        for first, last, badge, total_hours in rows:
            name = f"{last}, {first}"
            self.tree.insert(
                "", "end",
                values=(badge or "", name, total_hours or "")
            )

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

    def _on_member_hours_changed(self):
        self.populate_report()

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

        member_form.MemberForm(
            self,
            member_id=member_id,
            open_tab="work_hours",
            on_dues_changed=self._on_member_hours_changed
        )
