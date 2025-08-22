# attendance_report.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import tempfile, os, platform, subprocess
import database
import member_form
from report_base import BaseReportWindow
import csv


class AttendanceReport(BaseReportWindow):
    columns = ("badge", "name", "total_meetings")
    column_widths = (90, 260, 120)

    def __init__(self, parent):
        self.show_name_in_print = True
        super().__init__(parent, "Attendance Report", "attendance_report_geometry")
        self.tree.bind("<Double-1>", self.on_row_double_click)

    # ---------- Setup top controls ----------
    def _setup_controls(self):
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        # Year selector
        tk.Label(top, text="Select Year:").pack(side="left", padx=(10, 6))
        self.year_var = tk.StringVar(value=str(database.get_default_year()))
        tk.Spinbox(top, from_=2000, to=2100, textvariable=self.year_var, width=6).pack(side="left")

        # Month selector with "All" option
        tk.Label(top, text="Select Month:").pack(side="left", padx=(10, 6))
        self.months = ["All", "January", "February", "March", "April", "May", "June",
                       "July", "August", "September", "October", "November", "December"]
        self.month_var = tk.StringVar(value="All")
        month_dropdown = ttk.Combobox(top, values=self.months, textvariable=self.month_var, width=6, state="readonly")
        month_dropdown.pack(side="left")

        # Buttons
        tk.Button(top, text="Generate Report", command=self.populate_report).pack(side="left", padx=10)
        tk.Button(top, text="Print Report", command=self.print_report).pack(side="left", padx=10)
        tk.Button(top, text="Export CSV", command=self.export_csv).pack(side="left", padx=2)

        # Add Name toggle
        tk.Checkbutton(
            top,
            text="Exclude Name in Print",
            variable=tk.BooleanVar(value=self.show_name_in_print),
            command=lambda: setattr(self, 'show_name_in_print', not self.show_name_in_print)
        ).pack(side="left", padx=10)

    # ---------- Populate report ----------
    def populate_report(self):
        year = self.year_var.get().strip()
        month = self.month_var.get()
        month_num = None if month == "All" else f"{self.months.index(month):02d}"

        try:
            # Returns rows like: (badge, first_name, last_name, meetings_attended, total_meetings)
            rows = database.get_attendance_summary(year=year or None, month=month_num)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch attendance data: {e}")
            return

        self.clear_tree()
        for badge, first, last, attended, total in rows:
            name = f"{last}, {first}"
            self.tree.insert("", "end", values=(badge or "", name, total or 0))

    # ---------- CSV export ----------
    def export_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Export CSV", "No data to export.")
            return
        path = tk.filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = ["Badge", "Name", "Total Meetings"]
                writer.writerow(headers)
                for item in items:
                    writer.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Export CSV", f"CSV exported successfully to {path}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export CSV: {e}")

    # ---------- Member lookup ----------
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

    def _on_member_data_changed(self):
        self.populate_report()

    # ---------- Double-click to open member form ----------
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
            open_tab="attendance",
            on_hours_changed=self._on_member_data_changed
        )

    # ---------- Print report ----------
    def print_report(self):
        import tkinter.font as tkfont

        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Print", "No data to print.")
            return

        title_lines = ["Dug Hill Rod & Gun Club", "Meeting Attendance Report"]
        headings = ["Badge", "Name", "Total Meetings"]
        rows = [self.tree.item(item, "values") for item in items]

        # Maximum column widths
        MAX_BADGE_WIDTH = 10
        MAX_NAME_WIDTH = 25
        MAX_TOTAL_WIDTH = 8

        def truncate(text, width):
            text = str(text)
            return text if len(text) <= width else text[:width-3] + "..."

        col_widths = [MAX_BADGE_WIDTH, MAX_NAME_WIDTH, MAX_TOTAL_WIDTH]
        gap = " " * 10

        # Estimate rows per column dynamically
        preview_height = 560
        temp_preview = tk.Toplevel(self)
        temp_preview.withdraw()
        text_widget = tk.Text(temp_preview, wrap="none", font=("Courier New", 10))
        text_widget.pack()
        font = tkfont.Font(font=text_widget.cget("font"))
        line_height = font.metrics("linespace")
        header_footer_lines = 6
        ROWS_PER_COLUMN = max(1, preview_height // line_height - header_footer_lines)
        temp_preview.destroy()

        pages = []
        idx = 0
        while idx < len(rows):
            left_rows = rows[idx: idx + ROWS_PER_COLUMN]
            idx += ROWS_PER_COLUMN
            right_rows = rows[idx: idx + ROWS_PER_COLUMN]
            idx += ROWS_PER_COLUMN

            if self.show_name_in_print:
                header_line = (" " * 5).join([
                    headings[0].ljust(col_widths[0]),
                    headings[1].ljust(col_widths[1]),
                    headings[2].rjust(col_widths[2])
                ])
            else:
                header_line = (" " * 5).join([
                    headings[0].ljust(col_widths[0]),
                    headings[2].rjust(col_widths[2])
                ])
            separator_line = "-" * len(header_line)
            full_width = len(header_line + gap + header_line)

            page_lines = [
                *[line.center(full_width) for line in title_lines],
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(full_width),
                "",
                header_line + gap + header_line,
                separator_line + gap + separator_line
            ]

            max_rows = max(len(left_rows), len(right_rows))
            for i in range(max_rows):
                # Left column
                if i < len(left_rows):
                    left = left_rows[i]
                    if self.show_name_in_print:
                        left_line = (" " * 5).join([
                            str(truncate(left[0], col_widths[0])).ljust(col_widths[0]),
                            str(truncate(left[1], col_widths[1])).ljust(col_widths[1]),
                            str(truncate(left[2], col_widths[2])).rjust(col_widths[2])
                        ])
                    else:
                        left_line = (" " * 5).join([
                            str(truncate(left[0], col_widths[0])).ljust(col_widths[0]),
                            str(truncate(left[2], col_widths[2])).rjust(col_widths[2])
                        ])
                else:
                    left_line = " " * len(header_line)

                # Right column
                if i < len(right_rows):
                    right = right_rows[i]
                    if self.show_name_in_print:
                        right_line = (" " * 5).join([
                            str(truncate(right[0], col_widths[0])).ljust(col_widths[0]),
                            str(truncate(right[1], col_widths[1])).ljust(col_widths[1]),
                            str(truncate(right[2], col_widths[2])).rjust(col_widths[2])
                        ])
                    else:
                        right_line = (" " * 5).join([
                            str(truncate(right[0], col_widths[0])).ljust(col_widths[0]),
                            str(truncate(right[2], col_widths[2])).rjust(col_widths[2])
                        ])
                else:
                    right_line = " " * len(header_line)

                page_lines.append(left_line + gap + right_line)

            pages.append(page_lines)

        total_pages = len(pages)
        report_text = ""
        for i, page_lines in enumerate(pages):
            page_lines.append("")
            page_lines.append(f"Page {i + 1} of {total_pages}".center(full_width))
            page_lines.append("End of Report".center(full_width))
            report_text += "\n".join(page_lines) + "\n\n"

        preview = tk.Toplevel(self)
        preview.title("Print Preview")
        text = tk.Text(preview, wrap="none", font=("Courier New", 10))
        text.insert("1.0", report_text)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, padx=5, pady=5)

        yscroll = ttk.Scrollbar(preview, orient="vertical", command=text.yview)
        xscroll = ttk.Scrollbar(preview, orient="horizontal", command=text.xview)
        text.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")

        btn_frame = tk.Frame(preview)
        btn_frame.pack(fill="x", pady=5)

        def do_print():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
            tmp.write(report_text.encode("utf-8"))
            tmp.close()
            try:
                system = platform.system()
                if system == "Windows":
                    os.startfile(tmp.name, "print")
                elif system == "Darwin":
                    subprocess.run(["lp", tmp.name], check=False)
                else:
                    subprocess.run(["lpr", tmp.name], check=False)
            except Exception as e:
                messagebox.showerror("Print Error", f"Failed to print: {e}")

        tk.Button(btn_frame, text="🖨 Print", command=do_print).pack(side="right", padx=5)
        tk.Button(btn_frame, text="Close", command=preview.destroy).pack(side="right", padx=5)
