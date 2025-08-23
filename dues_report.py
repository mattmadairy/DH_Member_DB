# dues_report.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import database

class DuesReport(tk.Frame):
    columns = ("badge", "name", "amount_due")
    column_widths = (90, 260, 120)

    def __init__(self, parent):
        super().__init__(parent)

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, pady=(5,0))

        self._setup_controls()
        self.populate_report()

    def _setup_controls(self):
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        tk.Button(top, text="Generate Report", command=self.populate_report).pack(side="left", padx=10)
        tk.Button(top, text="Print Report", command=self.print_report).pack(side="left", padx=10)
        tk.Button(top, text="Export CSV", command=self.export_csv).pack(side="left", padx=2)

    def populate_report(self):
        try:
            rows = database.get_dues_report()  # implement in your database module
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch dues data: {e}")
            return

        self.tree.delete(*self.tree.get_children())
        for badge, first, last, amount in rows:
            name = f"{last}, {first}"
            self.tree.insert("", "end", values=(badge or "", name, amount or 0))

    def export_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Export CSV", "No data to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files","*.csv")])
        if not path:
            return
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Badge","Name","Amount Due"])
                for item in items:
                    writer.writerow(self.tree.item(item,"values"))
            messagebox.showinfo("Export CSV", f"CSV exported successfully to {path}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export CSV: {e}")

    def print_report(self):
        # implement a text-based print preview like AttendanceReport
        pass
