import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import database
from report_base import BaseReportWindow
import member_form

class WorkHoursReportingWindow(BaseReportWindow):
    columns = ("badge", "name", "hours")
    column_widths = (90, 260, 100)

    def __init__(self, parent):
        self.show_name_in_print = True
        super().__init__(parent, "Work Hours Report", "900x560")
        self.tree.bind("<Double-1>", self.on_row_double_click)
        self.populate_report()

    def _setup_controls(self):
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)
        tk.Label(top, text="Select Year:").pack(side="left", padx=(10, 6))
        self.year_var = tk.StringVar(value=str(database.get_default_year()))
        tk.Spinbox(top, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left")
        tk.Button(top, text="Run Report", command=self.populate_report).pack(side="left", padx=10)
        tk.Checkbutton(
            top,
            text="Exclude Name in Print",
            variable=tk.BooleanVar(value=self.show_name_in_print),
            command=lambda: setattr(self, 'show_name_in_print', not self.show_name_in_print)
        ).pack(side="left", padx=10)

    def populate_report(self):
        year = str(self.year_var.get()).strip()
        try:
            rows = database.get_work_hours_by_year(year)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch work hours: {e}")
            return

        self.clear_tree()
        for first, last, badge, total_hours in rows:
            name = f"{last}, {first}"
            self.tree.insert("", "end", values=(badge or "", name, total_hours or ""))

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
        badge = self.tree.item(item, "values")[0]
        if not badge:
            messagebox.showwarning("Open Member", "No badge number on the selected row.")
            return
        member_id = self._member_id_by_badge(badge)
        if not member_id:
            messagebox.showerror("Open Member", f"No member found with badge '{badge}'.")
            return
        member_form.MemberForm(self, member_id=member_id, open_tab="work_hours", on_hours_changed=self.populate_report)
