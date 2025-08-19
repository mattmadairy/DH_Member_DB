import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import tempfile, os, platform, subprocess, csv

import database


class ReportingWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Dues Report")
        self.geometry("900x560")

        # --- Bind keyboard shortcuts ---
        self.bind_all("<Control-p>", lambda e: self.print_report())   # Windows/Linux
        self.bind_all("<Command-p>", lambda e: self.print_report())   # macOS

        # --- Top controls: Year + buttons ---
        top = tk.Frame(self)
        top.pack(fill="x", pady=8)

        tk.Label(top, text="Select Year:").pack(side=tk.LEFT, padx=(10, 6))

        default_year = str(database.get_default_year())
        self.year_var = tk.StringVar(value=default_year)

        tk.Spinbox(
            top, from_=2000, to=2100, textvariable=self.year_var, width=6
        ).pack(side=tk.LEFT)

        tk.Button(top, text="Payments", command=lambda: self.populate_report(False)).pack(
            side=tk.LEFT, padx=10
        )
        tk.Button(top, text="Outstanding", command=lambda: self.populate_report(True)).pack(
            side=tk.LEFT, padx=2
        )
        tk.Button(top, text="Print Report", command=self.print_report).pack(
            side=tk.LEFT, padx=10
        )
        tk.Button(top, text="Export CSV", command=self.export_csv).pack(
            side=tk.LEFT, padx=2
        )

        # --- Inclusive membership type filters ---
        filters = tk.Frame(self)
        filters.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(filters, text="Include Types:").grid(row=0, column=0, sticky="w")

        self.membership_types = [
            "Probationary", "Associate", "Active",
            "Life", "Prospective", "Waitlist", "Former"
        ]
        self.type_vars = {}
        defaults = {"Probationary", "Associate", "Active"}
        col = 1
        for mtype in self.membership_types:
            var = tk.BooleanVar(value=(mtype in defaults))
            cb = tk.Checkbutton(filters, text=mtype, variable=var)
            cb.grid(row=0, column=col, sticky="w", padx=(8, 0))
            self.type_vars[mtype] = var
            col += 1

        # --- Treeview with BOTH scrollbars ---
        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Badge first now
        cols = ("badge", "name", "type", "paid", "expected", "outstanding", "last_payment")
        self.tree = ttk.Treeview(
            table_frame,
            columns=cols,
            show="headings",
            selectmode="browse"
        )

        # Headings
        self.tree.heading("badge", text="Badge #", command=lambda c="badge": self.sort_by(c))
        self.tree.heading("name", text="Name", command=lambda c="name": self.sort_by(c))
        self.tree.heading("type", text="Type", command=lambda c="type": self.sort_by(c))
        self.tree.heading("paid", text="Paid", command=lambda c="paid": self.sort_by(c))
        self.tree.heading("expected", text="Expected", command=lambda c="expected": self.sort_by(c))
        self.tree.heading("outstanding", text="Outstanding", command=lambda c="outstanding": self.sort_by(c))
        self.tree.heading("last_payment", text="Last Payment", command=lambda c="last_payment": self.sort_by(c))

        # Column widths
        self.tree.column("badge", width=90, anchor="center")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("type", width=110, anchor="w")
        self.tree.column("paid", width=90, anchor="e")
        self.tree.column("expected", width=90, anchor="e")
        self.tree.column("outstanding", width=110, anchor="e")
        self.tree.column("last_payment", width=130, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self._sort_state = {}
        self.populate_report(False)

    # ---------- Data helpers ----------
    def _selected_types(self):
        return [t for t, var in self.type_vars.items() if var.get()]

    def clear_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def populate_report(self, outstanding_only: bool):
        year = str(self.year_var.get()).strip()
        selected = self._selected_types()
        if not selected:
            messagebox.showwarning("No Types", "Select at least one membership type to include.")
            return

        try:
            if outstanding_only:
                rows = database.get_outstanding_dues(year, selected)
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

            paid_s = f"${paid_f:,.2f}" if paid_f else "$0.00"
            expected_s = f"${expected_f:,.2f}" if expected_f else "$0.00"
            outstanding_s = f"${outstanding_f:,.2f}" if outstanding_f else "$0.00"
            last_payment_s = last_payment if last_payment else ""

            # Badge first now
            self.tree.insert(
                "",
                tk.END,
                values=(badge or "", name, mtype, paid_s, expected_s, outstanding_s, last_payment_s)
            )

    # ---------- Sorting ----------
    def sort_by(self, col_id):
        reverse = self._sort_state.get(col_id, False)
        self._sort_state[col_id] = not reverse

        def parse_value(col_id, text):
            if col_id in ("paid", "expected", "outstanding"):
                try:
                    return float(text.replace("$", "").replace(",", ""))
                except Exception:
                    return 0.0
            elif col_id == "last_payment":
                if not text:
                    return datetime.min
                try:
                    return datetime.strptime(text, "%Y-%m-%d")
                except Exception:
                    return text
            elif col_id == "badge":
                try:
                    return int(text)
                except Exception:
                    return text
            else:
                return text.lower() if isinstance(text, str) else text

        data = [(self.tree.set(k, col_id), k) for k in self.tree.get_children("")]
        data.sort(key=lambda t: parse_value(col_id, t[0]), reverse=reverse)

        for index, (_, k) in enumerate(data):
            self.tree.move(k, "", index)

    # ---------- Print Preview ----------
    def print_report(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Print", "No report data to print.")
            return

        headings = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        rows = [headings]
        for item in items:
            rows.append(self.tree.item(item, "values"))

        col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(headings))]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        width_sum = sum(col_widths) + 3 * (len(col_widths) - 1)

        lines = [
            "Dues Report".center(width_sum),
            f"Year: {self.year_var.get()}".center(width_sum),
            f"Generated: {timestamp}".center(width_sum),
            ""
        ]

        for idx, row in enumerate(rows):
            line = "   ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row)))
            if idx == 0:
                lines.append(line)
                lines.append("-" * len(line))
            else:
                lines.append(line)
        lines.append("")
        lines.append("End of Report".center(width_sum))

        report_text = "\n".join(lines)

        # --- Preview Window ---
        preview = tk.Toplevel(self)
        preview.title("Print Preview")
        preview.geometry("700x500")

        text = tk.Text(preview, wrap="none")
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

        ttk.Button(btn_frame, text="🖨 Print", command=do_print).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Close", command=preview.destroy).pack(side="right", padx=5)

    # ---------- Export ----------
    def export_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Export", "No report data to export.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([self.tree.heading(col)["text"] for col in self.tree["columns"]])
                for item in items:
                    writer.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Export", f"Report exported successfully:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export report: {e}")
