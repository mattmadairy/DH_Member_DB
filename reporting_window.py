# reporting_window.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import tempfile, os, platform, subprocess, csv

import database
import member_form  # for opening the MemberForm
from report_base import BaseReportWindow


class ReportingWindow(BaseReportWindow):
    columns = ("badge", "name", "type", "paid", "expected", "outstanding", "last_payment")
    column_widths = (90, 220, 110, 90, 90, 110, 130)

    def __init__(self, parent):
        super().__init__(parent, "Dues Report", "reporting_window_geometry")
        self.report_mode = "paid"

        # ✅ Bind double-click after BaseReportWindow has created self.tree
        self.tree.bind("<Double-1>", self.on_row_double_click)

    # ---------- Setup top controls ----------
    def _setup_controls(self):
        # Top row: year selector + buttons
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        tk.Label(top, text="Select Year:").pack(side="left", padx=(10,6))
        self.year_var = tk.StringVar(value=str(database.get_default_year()))
        tk.Spinbox(top, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left")

        tk.Button(top, text="Run All Dues Report", command=lambda: self.populate_report("all")).pack(side="left", padx=10)
        tk.Button(top, text="Run Paid Report", command=lambda: self.populate_report("paid")).pack(side="left", padx=2)
        tk.Button(top, text="Run Outstanding Report", command=lambda: self.populate_report("outstanding")).pack(side="left", padx=2)
        tk.Button(top, text="Print Report", command=self.print_report).pack(side="left", padx=10)
        tk.Button(top, text="Export CSV", command=self.export_csv).pack(side="left", padx=2)

        # Membership type filters
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
    def populate_report(self, mode="paid"):
        self.report_mode = mode
        year = str(self.year_var.get()).strip()
        selected = [t for t, var in self.type_vars.items() if var.get()]
        if not selected:
            messagebox.showwarning("No Types", "Select at least one membership type to include.")
            return

        try:
            if mode == "outstanding":
                rows = database.get_outstanding_dues(year, selected)
            elif mode == "all":
                rows = database.get_all_dues(year, selected)
            else:
                rows = database.get_payments_by_year(year, selected)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch report: {e}")
            return

        self.clear_tree()

        for first, last, mtype, paid, expected, outstanding, badge, last_payment in rows:
            name = f"{last}, {first}"
            paid_f = float(paid or 0)
            expected_f = float(expected or 0)
            outstanding_f = float(outstanding) if outstanding is not None else (expected_f - paid_f)

            if mtype == "Life":
                try:
                    life_dues = float(database.get_setting("dues_life") or 0)
                    expected_f = life_dues
                    outstanding_f = expected_f - paid_f
                except Exception:
                    expected_f = 0.0
                    outstanding_f = 0.0

            paid_s = f"${paid_f:,.2f}"
            expected_s = f"${expected_f:,.2f}"
            outstanding_s = f"${outstanding_f:,.2f}"
            last_payment_s = last_payment or ""

            self.tree.insert("", "end", values=(badge or "", name, mtype, paid_s, expected_s, outstanding_s, last_payment_s))

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

    def _on_member_dues_changed(self):
        self.populate_report(self.report_mode)

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
            open_tab="dues",
            on_dues_changed=self._on_member_dues_changed
        )
