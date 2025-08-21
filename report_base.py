# report_base.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import tempfile, os, platform, subprocess, csv

class BaseReportWindow(tk.Toplevel):
    """Generic reporting window for tabular reports."""

    def __init__(self, parent, title, geometry_setting_key):
        super().__init__(parent)
        self.title(title)
        self.geometry_setting_key = geometry_setting_key

        # Restore geometry
        try:
            geom = self.get_geometry_setting()
            if geom:
                self.geometry(geom)
            else:
                self.geometry("900x560")
        except Exception:
            self.geometry("900x560")

        self.report_mode = "default"
        self._sort_state = {}

        self._setup_controls()
        self._setup_tree()
        self.clear_tree()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind_all("<Control-p>", lambda e: self.print_report())
        self.bind_all("<Command-p>", lambda e: self.print_report())

    # ---------- Geometry ----------
    def get_geometry_setting(self):
        import database
        return database.get_setting(self.geometry_setting_key)

    def save_geometry_setting(self):
        import database
        try:
            database.set_setting(self.geometry_setting_key, self.geometry())
        except Exception:
            pass

    def on_close(self):
        self.save_geometry_setting()
        self.destroy()

    # ---------- Treeview ----------
    def _setup_tree(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings", selectmode="browse")
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.replace("_", " ").title(), command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.on_row_double_click)

    def clear_tree(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    # ---------- Sorting ----------
    def sort_by(self, col_id):
        reverse = self._sort_state.get(col_id, False)
        self._sort_state[col_id] = not reverse

        def parse_value(col, text):
            return text  # default implementation
        data = [(self.tree.set(k, col_id), k) for k in self.tree.get_children("")]
        data.sort(key=lambda t: parse_value(col_id, t[0]), reverse=reverse)
        for index, (_, k) in enumerate(data):
            self.tree.move(k, "", index)

    # ---------- Printing ----------
    def print_report(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Print", "No data to print.")
            return
        title = self.title()
        headings = [self.tree.heading(col)["text"] for col in self.tree["columns"]]
        rows = [headings] + [self.tree.item(item, "values") for item in items]

        col_widths = [max(len(str(row[i])) for row in rows) for i in range(len(headings))]
        width_sum = sum(col_widths) + 3 * (len(col_widths) - 1)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            title.center(width_sum),
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

        # Preview window
        preview = tk.Toplevel(self)
        preview.title("Print Preview")
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

    # ---------- CSV Export ----------
    def export_csv(self):
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Export", "No data to export.")
            return

        default_name = f"{self.title().lower().replace(' ', '_')}.csv"
        file_path = filedialog.asksaveasfilename(
            initialfile=default_name,
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

    # ---------- Row double-click placeholder ----------
    def on_row_double_click(self, event):
        pass  # To be implemented by subclasses

    # ---------- Populate report placeholder ----------
    def populate_report(self):
        raise NotImplementedError("Subclasses must implement populate_report()")
