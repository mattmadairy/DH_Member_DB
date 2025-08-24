import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import database
import calendar


class ReportsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reports")
        self.geometry("800x500")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # ---------------- Individual Member Report Tab ---------------- #
        member_report_tab = ttk.Frame(notebook)
        notebook.add(member_report_tab, text="Member")
        tk.Label(member_report_tab, text="Individual Member report not yet implemented")

        # ---------------- Dues Tab ---------------- #
        dues_tab = ttk.Frame(notebook)
        notebook.add(dues_tab, text="Dues")
        tk.Label(dues_tab, text="Dues report not yet implemented").pack(padx=20, pady=20)
        # Replace above with your actual DuesReportFrame:
        # DuesReportFrame(dues_tab).pack(fill="both", expand=True)

        # ---------------- Work Hours Tab ---------------- #
        work_tab = ttk.Frame(notebook)
        notebook.add(work_tab, text="Work Hours")
        tk.Label(work_tab, text="Work Hours report not yet implemented").pack(padx=20, pady=20)
        # Replace above with your actual WorkHoursReportFrame:
        # WorkHoursReportFrame(work_tab).pack(fill="both", expand=True)

        # ---------------- Attendance Tab ---------------- #
        attendance_tab = ttk.Frame(notebook)
        notebook.add(attendance_tab, text="Attendance")
        AttendanceReport(attendance_tab).pack(fill="both", expand=True)


class MemberReport(tk.Frame):
    pass


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


class WorkHoursReport(tk.Frame):
    columns = ("badge","name","work_hours")
    column_widths = (90,260,120)

    def __init__(self,parent):
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

        tk.Button(top,text="Generate Report",command=self.populate_report).pack(side="left", padx=10)
        tk.Button(top,text="Print Report",command=self.print_report).pack(side="left", padx=10)
        tk.Button(top,text="Export CSV",command=self.export_csv).pack(side="left", padx=2)

    def populate_report(self):
        try:
            rows = database.get_work_hours_report()  # implement in database module
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch work hours: {e}")
            return

        self.tree.delete(*self.tree.get_children())
        for badge, first, last, hours in rows:
            name = f"{last}, {first}"
            self.tree.insert("", "end", values=(badge or "", name, hours or 0))

    def export_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Export CSV","No data to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files","*.csv")])
        if not path:
            return
        try:
            with open(path,"w",newline="",encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Badge","Name","Work Hours"])
                for item in items:
                    writer.writerow(self.tree.item(item,"values"))
            messagebox.showinfo("Export CSV", f"CSV exported successfully to {path}")
        except Exception as e:
            messagebox.showerror("Export CSV",f"Failed to export CSV: {e}")

    def print_report(self):
        # implement a text-based print preview like AttendanceReport
        pass


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
