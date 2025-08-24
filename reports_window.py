import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import database
import calendar
import datetime

class ReportsWindow(tk.Toplevel):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.title("Reports")
        self.geometry("900x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # ---------------- Individual Member Report Tab ---------------- #
        member_tab = ttk.Frame(notebook)
        notebook.add(member_tab, text="Member")
        MemberReport(member_tab, member_id).pack(fill="both", expand=True)

        # ---------------- Dues Tab ---------------- #
        dues_tab_frame = ttk.Frame(notebook)
        notebook.add(dues_tab_frame, text="Dues")
        DuesReport(dues_tab_frame, member_id).pack(fill="both", expand=True)

        # ---------------- Work Hours Tab ---------------- #
        work_tab_frame = ttk.Frame(notebook)
        notebook.add(work_tab_frame, text="Work Hours")
        WorkHoursReport(work_tab_frame, member_id).pack(fill="both", expand=True)

        # ---------------- Attendance Tab ---------------- #
        attendance_tab = ttk.Frame(notebook)
        notebook.add(attendance_tab, text="Attendance")
        AttendanceReport(attendance_tab, member_id).pack(fill="both", expand=True)


class MemberReport(tk.Frame):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        tk.Label(self, text="Individual Member report not yet implemented").pack(padx=20, pady=20)


class BaseReport(tk.Frame):
    """Base class with common controls for member/year/month filters and CSV export"""
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.member_id = member_id
        self.year_var = tk.IntVar()
        self.month_var = tk.StringVar(value="All")
        self.tree = None
        self.columns = ()
        self.column_widths = ()
        self._setup_controls()
        self._create_tree()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        # Year Spinbox
        try:
            default_year = int(database.get_setting("default_year"))
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
        month_cb.configure(background="white")

        # Buttons
        tk.Button(frame, text="Generate Report", command=self.populate_report).pack(side="left", padx=5)
        tk.Button(frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=5)
        tk.Button(frame, text="Print Report", command=self.print_report).pack(side="left", padx=5)

    def _create_tree(self):
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, pady=5)

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
                writer.writerow([c.title() for c in self.columns])
                for item in items:
                    writer.writerow(self.tree.item(item,"values"))
            messagebox.showinfo("Export CSV", f"CSV exported successfully to {path}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export CSV: {e}")

    def print_report(self):
        # Implement a simple text-based print preview if needed
        pass

    def populate_report(self):
        raise NotImplementedError("populate_report must be implemented in subclass")


class DuesReport(tk.Frame):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.member_id = member_id  # Optional filter by member
        self.year_var = tk.IntVar()
        self.month_var = tk.StringVar(value="All")
        self.columns = ("badge", "name", "amount_due", "year", "last_payment_date", "amount_paid", "method")
        self.column_widths = (90, 200, 100, 60, 100, 100, 80)

        self._setup_controls()
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w")  # Left-align text
        self.tree.pack(fill="both", expand=True, pady=5)

        self.populate_report()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        # Default year from settings
        try:
            default_year = int(database.get_setting("default_year"))
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
        month_cb.configure(background="white")

        # Generate Report button
        tk.Button(frame, text="Run Report", command=self.populate_report).pack(side="left", padx=(10,0))
    
    def populate_report(self):
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        month_name = self.month_var.get()

        try:
            members = database.get_all_members()
            for m in members:
                member_id = m[0]
                if self.member_id and member_id != self.member_id:
                    continue

                badge = m[1]
                name = f"{m[3]} {m[4]}"  # first + last name

                dues = database.get_dues_by_member(member_id)
                total_paid = 0
                last_payment_date = ""
                method = ""
                due_year = year

                for d in dues:
                    try:
                        amount = float(d[2])  # amount column
                    except (ValueError, TypeError):
                        amount = 0

                    payment_date = d[3] if len(d) > 3 else ""
                    try:
                        year_value = int(d[4]) if len(d) > 4 else year
                    except (ValueError, TypeError):
                        year_value = year
                    payment_method = d[5] if len(d) > 5 else ""

                    # Filter by year
                    if year_value != year:
                        continue

                    # Filter by month
                    if month_name != "All" and payment_date:
                        month_index = list(calendar.month_name).index(month_name)
                        if int(payment_date.split("-")[1]) != month_index:
                            continue

                    total_paid += amount
                    last_payment_date = payment_date
                    method = payment_method
                    due_year = year_value

                # Insert one row per member
                self.tree.insert("", "end", values=(badge, name, 0, due_year, last_payment_date, total_paid, method))
        except Exception as e:
            messagebox.showerror("Dues Report", f"Failed to fetch dues data:\n{e}")


class WorkHoursReport(tk.Frame):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.member_id = member_id
        self.year_var = tk.IntVar()
        self.month_var = tk.StringVar(value="All")
        self.columns = ("badge", "name", "work_hours")
        self.column_widths = (90, 260, 120)

        self._setup_controls()

        # Create Treeview
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=width, anchor="w")  # left-align text
        self.tree.pack(fill="both", expand=True, pady=5)

        # Automatically populate report for the default year and "All" months
        self.populate_report()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        # Default year from settings
        try:
            default_year = int(database.get_setting("default_year"))
        except Exception:
            default_year = datetime.now().year
        self.year_var.set(default_year)

        tk.Label(frame, text="Year:").pack(side="left", padx=(10,0))
        tk.Spinbox(frame, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left", padx=(0,10))

        # Month dropdown
        tk.Label(frame, text="Month:").pack(side="left")
        months = ["All"] + list(calendar.month_name[1:])
        month_cb = ttk.Combobox(frame, values=months, textvariable=self.month_var, state="readonly", width=10)
        month_cb.pack(side="left", padx=(0,10))
        month_cb.configure(background="white")

        # Run Report button
        tk.Button(frame, text="Run Report", command=self.populate_report).pack(side="left", padx=(10,0))

    def populate_report(self):
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        month_name = self.month_var.get()

        # Determine start and end dates for the filter
        if month_name == "All":
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
        else:
            month_index = list(calendar.month_name).index(month_name)
            start_date = f"{year}-{month_index:02d}-01"
            # Compute last day of month
            last_day = calendar.monthrange(year, month_index)[1]
            end_date = f"{year}-{month_index:02d}-{last_day}"

        try:
            rows = database.get_work_hours_report(
                member_id=self.member_id,
                start_date=start_date,
                end_date=end_date
            )

            for badge, first, last, total_hours in rows:
                name = f"{last}, {first}"
                self.tree.insert("", "end", values=(badge or "", name, total_hours or 0))

        except Exception as e:
            messagebox.showerror("Work Hours Report", f"Failed to fetch work hours data:\n{e}")


class AttendanceReport(tk.Frame):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.member_id = member_id
        self.year_var = tk.IntVar()
        self.month_var = tk.StringVar(value="All")
        self.columns = ("badge", "name", "status")
        self.column_widths = (90, 260, 120)

        self._setup_controls()

        # Create Treeview
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.title())
            self.tree.column(col, width=width, anchor="w")  # left-align
        self.tree.pack(fill="both", expand=True, pady=5)

        # Populate report automatically
        self.populate_report()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        # Default year from settings
        try:
            default_year = int(database.get_setting("default_year"))
        except Exception:
            default_year = datetime.now().year
        self.year_var.set(default_year)

        tk.Label(frame, text="Year:").pack(side="left", padx=(10,0))
        tk.Spinbox(frame, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left", padx=(0,10))

        # Month dropdown
        tk.Label(frame, text="Month:").pack(side="left")
        months = ["All"] + list(calendar.month_name[1:])
        month_cb = ttk.Combobox(frame, values=months, textvariable=self.month_var, state="readonly", width=10)
        month_cb.pack(side="left", padx=(0,10))
        month_cb.configure(background="white")

        # Run Report button
        tk.Button(frame, text="Run Report", command=self.populate_report).pack(side="left", padx=(10,0))

    def populate_report(self):
        # Clear existing rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        month_name = self.month_var.get()

        try:
            members = database.get_all_members()

            for m in members:
                member_id = m[0]

                if self.member_id and member_id != self.member_id:
                    continue

                badge = m[1]
                name = f"{m[3]} {m[4]}"

                if month_name == "All":
                    # Total meetings attended/exempted for the year
                    total = database.count_member_attendance(member_id, year)
                    self.tree.insert("", "end", values=(badge, name, total))
                else:
                    month_index = list(calendar.month_name).index(month_name)
                    status = database.get_member_status_for_month(member_id, year, month_index)
                    if status:
                        self.tree.insert("", "end", values=(badge, name, status))

        except Exception as e:
            messagebox.showerror("Attendance Report", f"Failed to fetch attendance data:\n{e}")
