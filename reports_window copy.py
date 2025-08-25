import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import database
import calendar
from datetime import datetime

class ReportsWindow(tk.Toplevel):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.title("Reports")
        self.geometry("900x600")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

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

# ---------------- Base Report ---------------- #
class BaseReport(tk.Frame):
    """Base class with common controls for member/year/month filters and CSV export"""
    def __init__(self, parent, member_id=None, include_month=True):
        super().__init__(parent)
        self.member_id = member_id
        self.year_var = tk.IntVar()
        self.month_var = tk.StringVar(value="All")
        self.include_month = include_month
        self.tree = None
        self._setup_controls()
        self._create_tree()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        try:
            default_year = int(database.get_setting("default_year"))
        except Exception:
            default_year = datetime.now().year
        self.year_var.set(default_year)

        tk.Label(frame, text="Year:").pack(side="left", padx=(10,0))
        year_spin = tk.Spinbox(frame, from_=2000, to=2100, textvariable=self.year_var, width=6)
        year_spin.pack(side="left", padx=(0,10))
        self.year_var.trace_add("write", lambda *args: self.populate_report())  # auto-refresh on year change

        if self.include_month:
            tk.Label(frame, text="Month:").pack(side="left")
            months = ["All"] + list(calendar.month_name[1:])
            month_cb = ttk.Combobox(frame, values=months, textvariable=self.month_var, state="readonly", width=10)
            month_cb.pack(side="left", padx=(0,10))
            month_cb.configure(background="white")
            self.month_var.trace_add("write", lambda *args: self.populate_report())  # auto-refresh on month change

        tk.Button(frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=5)
        tk.Button(frame, text="Print Report", command=self.print_report).pack(side="left", padx=5)

    def _create_tree(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.replace("_"," ").title())
            self.tree.column(col, width=width, anchor="w")

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
                writer.writerow([c.replace("_"," ").title() for c in self.columns])
                for item in items:
                    writer.writerow(self.tree.item(item,"values"))
            messagebox.showinfo("Export CSV", f"CSV exported successfully to {path}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export CSV: {e}")

    def print_report(self):
        """Formatted print preview with headers, footers, page numbers, and aligned columns."""
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = self.__class__.__name__.replace("Report", " Report")
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        year = self.year_var.get()
        month_name = self.month_var.get()
        timeframe = f"{month_name} {year}" if month_name != "All" else f"Year {year}"

        headers = [c.replace("_", " ").title() for c in self.columns]
        col_widths = [max(len(h), 12) for h in headers]
        for idx, col in enumerate(self.columns):
            for item in items:
                value = str(self.tree.item(item, "values")[idx])
                if len(value) > col_widths[idx]:
                    col_widths[idx] = len(value)

        # Pagination
        lines_per_page = 40  # including header/footer
        pages = []
        current_lines = []

        def add_header():
            current_lines.append(org_name.center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append(report_name.center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append(f"Generated: {generation_dt}".center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append(f"Timeframe: {timeframe}".center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append("=" * (sum(col_widths) + len(col_widths) * 3))
            header_line = ""
            for h, w in zip(headers, col_widths):
                header_line += h.ljust(w + 3)
            current_lines.append(header_line)
            current_lines.append("-" * (sum(col_widths) + len(col_widths) * 3))

        add_header()
        row_count = 0

        for item in items:
            row = self.tree.item(item, "values")
            line = ""
            for val, w in zip(row, col_widths):
                line += str(val).ljust(w + 3)
            current_lines.append(line)
            row_count += 1

            # Start new page if needed
            if row_count >= lines_per_page - 6:  # reserve lines for footer
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()

        # Add remaining lines as last page
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)

        # Append footer to each page with Page X of Y
        for i, page_lines in enumerate(pages, start=1):
            footer_width = sum(col_widths) + len(col_widths) * 3
            page_lines.append("=" * footer_width)
            page_lines.append(f"Page {i} of {total_pages}".center(footer_width))
            page_lines.append("End of Report".center(footer_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        # Display in Tkinter Text widget
        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        text = tk.Text(print_window, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.pack(fill="both", expand=True)

        # Scrollbars
        vsb = ttk.Scrollbar(print_window, orient="vertical", command=text.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(print_window, orient="horizontal", command=text.xview)
        hsb.pack(side="bottom", fill="x")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)



    def populate_report(self):
        raise NotImplementedError("populate_report must be implemented in subclass")
    
# ---------------- Dues Report ---------------- #

class DuesReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "membership_type", "amount_due", "balance_due",
                        "year", "last_payment_date", "amount_paid", "method")
        self.column_widths = (60, 150, 110, 80, 80, 60, 120, 80, 80)
        super().__init__(parent, member_id, include_month=False)  # no month filter
        self.populate_report()

    # populate_report stays the same
    def populate_report(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        try:
            members = database.get_all_members()
            for m in members:
                member_id = m[0]
                if self.member_id and member_id != self.member_id:
                    continue
                badge = m[1]
                name = f"{m[3]} {m[4]}"
                membership_type = m[2]
                amount_due = 0
                if membership_type:
                    setting_key = f"dues_{membership_type.lower()}"
                    try:
                        amount_due = float(database.get_setting(setting_key) or 0)
                    except (ValueError, TypeError):
                        amount_due = 0

                dues = database.get_dues_by_member(member_id)
                total_paid = 0
                last_payment_date = ""
                method = ""

                for d in dues:
                    try:
                        payment_amount = float(d[4])
                    except (ValueError, TypeError, IndexError):
                        payment_amount = 0

                    payment_date = d[2] if len(d) > 2 else ""
                    try:
                        payment_year = int(d[3]) if len(d) > 3 else year
                    except (ValueError, TypeError, IndexError):
                        payment_year = year

                    payment_method = d[5] if len(d) > 5 else ""
                    if payment_year != year:
                        continue

                    total_paid += payment_amount
                    if payment_date and (not last_payment_date or payment_date > last_payment_date):
                        last_payment_date = payment_date
                        method = payment_method

                if last_payment_date:
                    try:
                        dt = datetime.strptime(last_payment_date, "%Y-%m-%d")
                        last_payment_date = dt.strftime("%m-%d-%Y")
                    except ValueError:
                        pass

                balance_due = max(amount_due - total_paid, 0)
                self.tree.insert("", "end", values=(
                    badge, name, membership_type,
                    f"{amount_due:.2f}", f"{balance_due:.2f}",
                    year, last_payment_date,
                    f"{total_paid:.2f}", method
                ))
        except Exception as e:
                messagebox.showerror("Dues Report", f"Failed to fetch dues data:\n{e}")



class WorkHoursReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "work_hours")
        self.column_widths = (10, 260, 120)
        super().__init__(parent, member_id)
        self.populate_report()

    def populate_report(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        month_name = self.month_var.get()
        if month_name == "All":
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
        else:
            month_index = list(calendar.month_name).index(month_name)
            start_date = f"{year}-{month_index:02d}-01"
            last_day = calendar.monthrange(year, month_index)[1]
            end_date = f"{year}-{month_index:02d}-{last_day}"

        try:
            rows = database.get_work_hours_report(self.member_id, start_date, end_date)
            for badge, first, last, total_hours in rows:
                name = f"{last}, {first}"
                self.tree.insert("", "end", values=(badge or "", name, total_hours or 0))
        except Exception as e:
            messagebox.showerror("Work Hours Report", f"Failed to fetch work hours data:\n{e}")

class AttendanceReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "status")
        self.column_widths = (90, 260, 120)
        super().__init__(parent, member_id)
        self.populate_report()

    def populate_report(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        year = self.year_var.get()
        month_name = self.month_var.get()

        status_col = "status"
        if status_col in self.tree["columns"]:
            if month_name == "All":
                self.tree.heading(status_col, text="Number of Meetings Attended")
            else:
                self.tree.heading(status_col, text="Status")

        try:
            members = database.get_all_members()
            for m in members:
                member_id = m[0]
                if self.member_id and member_id != self.member_id:
                    continue
                badge = m[1]
                name = f"{m[3]} {m[4]}"
                if month_name == "All":
                    total = database.count_member_attendance(member_id, year)
                    self.tree.insert("", "end", values=(badge, name, total))
                else:
                    month_index = list(calendar.month_name).index(month_name)
                    status = database.get_member_status_for_month(member_id, year, month_index)
                    if status:
                        self.tree.insert("", "end", values=(badge, name, status))
        except Exception as e:
            messagebox.showerror("Attendance Report", f"Failed to fetch attendance data:\n{e}")
