import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import os
import database
from datetime import datetime
import csv
import calendar


# Add this utility function near the top of your code
def center_window(window, width=None, height=None, parent=None):
    """Center a Tkinter window on the screen or relative to parent."""
    window.update_idletasks()
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()

    if parent:
        parent.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw // 2) - (width // 2)
        y = py + (ph // 2) - (height // 2)
    else:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")


class MemberApp:
    TREE_COLUMNS = (
        "Badge", "Last Name", "First Name", "Membership Type",
        "Email Address", "Email Address 2", "Phone Number"
    )

    FULL_COLUMNS = (
        "Badge", "Membership Type", "First Name", "Last Name",
        "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
        "Address", "City", "State", "Zip Code", "Join Date", "Sponsor",
        "Card/Fob Internal Number", "Card/Fob External Number"
    )

    def __init__(self, root):
        self.root = root
        self.root.title("Dug Hill Rod & Gun Club Membership Database")
        window_width = 1100
        window_height = 600

        # Get screen dimensions
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        # Calculate x and y coordinates to center the window
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)

        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        center_window(self.root, 1100, 600)  # <-- Center main window
        
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.recycle_bin_refresh_fn = None
        self.member_types = ["All", "Probationary", "Associate", "Active", "Life",
                             "Prospective", "Wait List", "Former"]
        self.trees = {}

        # ----- Menubar -----
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="⬆️ Import ", command=self._show_import_dialog)
        file_menu.add_command(label="⬇️ Export Current Tab", command=self._show_export_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="🖨  Print Current Tab", command=self._print_members)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        members_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Members", menu=members_menu)
        members_menu.add_command(label="➕  Add Member", command=self.add_member)
        members_menu.add_command(label="✏️  Edit Selected", command=self.edit_selected)
        members_menu.add_command(label="📝  Generate Member Report ", command=self._full_member_report_from_menu)
        members_menu.add_separator()
        members_menu.add_command(label="🗑️ Move to Recycle Bin", command=self.delete_selected)

        menubar.add_command(label="Reports", command=lambda: ReportsWindow(self.root))
        menubar.add_command(label="Recycle Bin", command=self._show_recycle_bin)
        menubar.add_command(label="Settings", command=self.open_settings)

        # ----- Search Bar -----
        search_frame = ttk.Frame(self.root)
        search_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", self._on_search)
        ttk.Button(search_frame, text="Clear", command=lambda: [self.search_var.set(""), self.load_data()]).pack(side="left", padx=5)

        # ----- Notebook -----
        style = ttk.Style()
        style.configure("CustomNotebook.TNotebook.Tab", padding=[10, 5], anchor="center")
        self.notebook = ttk.Notebook(self.root, style="CustomNotebook.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self._build_member_tabs()
        self.load_data()

        # Right-click menu
        self.row_menu = tk.Menu(self.root, tearoff=0)
        self.row_menu.add_command(label="Edit Member", command=self._edit_selected_row)
        self.row_menu.add_command(label="Generate Member Report", command=self._full_member_report_from_menu)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="Move to Recycle Bin", command=self._delete_selected_row)

        # Bind right-click
        for tree in self.trees.values():
            tree.bind("<Button-3>", self._show_row_menu)

        # Resize tabs
        def resize_tabs(event=None):
            total_tabs = len(self.notebook.tabs())
            if total_tabs == 0:
                return
            notebook_width = self.notebook.winfo_width()
            tab_width = notebook_width // total_tabs
            style.configure("CustomNotebook.TNotebook.Tab", width=tab_width)

        resize_tabs()
        self.notebook.bind("<Configure>", resize_tabs)

    # ---------- Tabs ----------
    def _build_member_tabs(self):
        for mtype in self.member_types:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=mtype)
            tree = self._make_tree_with_scrollbars(frame, self.TREE_COLUMNS)
            tree.bind("<Double-1>", self._on_tree_double_click)
            self.trees[mtype] = tree

    def _make_tree_with_scrollbars(self, parent, columns):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        self._sort_column_states = {}  # Keep track of sort order per column

        for col in columns:
            tree.heading(col, text=col, command=lambda c=col, t=tree: self._sort_tree_column(t, c, False))
            tree.column(col, width=120, anchor="w")
            if col == "Badge":
                tree.column(col, width=80, anchor="center")

        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        xscroll.pack(side="bottom", fill="x")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        return tree

    def _sort_tree_column(self, tree, col, reverse):
        """Sort tree contents by column and update header arrows."""
        try:
            # Get all rows and the values in the given column
            data = [(tree.set(k, col), k) for k in tree.get_children("")]
            
            # Try converting values to numbers if possible, otherwise lowercase string
            def try_convert(val):
                try:
                    return float(val)
                except ValueError:
                    return val.lower()
            data.sort(key=lambda t: try_convert(t[0]), reverse=reverse)

            # Rearrange items in sorted order
            for index, (val, k) in enumerate(data):
                tree.move(k, "", index)

            # Reset all headings to plain text
            for c in tree["columns"]:
                tree.heading(c, text=c, command=lambda c=c, t=tree: self._sort_tree_column(t, c, False))

            # Add arrow to the sorted column
            arrow = " ▲" if not reverse else " ▼"
            tree.heading(col, text=col + arrow,
                         command=lambda: self._sort_tree_column(tree, col, not reverse))

        except Exception as e:
            pass
            #messagebox.showerror("Sort Error", f"Failed to sort column {col}: {e}")


    # ---------- Member Management ----------
    def add_member(self):
        form = NewMemberForm(self.root, on_save_callback=self.load_data)
        self.root.wait_window(form.top)

    def edit_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to edit.")
            return
        member_id = selected[0]
        form = self._open_member_form(member_id)
        self.root.wait_window(form.top)

    def delete_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select members to move to the Recycle Bin.")
            return

        confirm = messagebox.askyesno("Confirm move to Recycle Bin", f"Are you sure you want to move {len(selected)} member(s) to the Recycle Bin?")
        if confirm:
            for sel in selected:
                member_id = sel
                database.soft_delete_member_by_id(member_id)
            self.load_data()
            if self.recycle_bin_refresh_fn:
                self.recycle_bin_refresh_fn()


    def _delete_selected_row(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select member(s) to move to the Recycle Bin.")
            return

        confirm = messagebox.askyesno("Confirm Recycle Bin", f"Are you sure you want to move {len(selected)} member(s) to the Recycle Bin?")
        if confirm:
            for member_id in selected:
                database.soft_delete_member_by_id(member_id)
            self.load_data()
            if self.recycle_bin_refresh_fn:
                self.recycle_bin_refresh_fn()


    def _open_member_form(self, member_id=None):
        return MemberForm(self.root, member_id, on_save_callback=lambda mid, mtype=None: self.load_data())

    # ---------- Right-click ----------
    def _show_row_menu(self, event):
        tree = event.widget
        row_id = tree.identify_row(event.y)
        if row_id:
            # If the clicked row is not already selected, select it
            if row_id not in tree.selection():
                tree.selection_set(row_id)
            # Otherwise, keep current selection (supports multi-select)
            self.row_menu.post(event.x_root, event.y_root)
        else:
            self.row_menu.unpost()


    def _edit_selected_row(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to edit.")
            return
        member_id = selected[0]
        form = self._open_member_form(member_id)
        self.root.wait_window(form.top)
    

    def _full_member_report_from_menu(self):
        """Wrapper to get selected member from the current tab and call the full report."""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a member first.")
            return
        member_id = selected[0]  # assuming iid = member_id
        self._full_member_report(member_id)

    

    def _full_member_report(self, member_id, year=None):

        # Ask for year if not provided
        if year is None:
                # Generate a list of years (e.g., last 30 years up to current)
                current_year = datetime.now().year
                years = [str(y) for y in range(current_year, current_year - 30, -1)]

                year_popup = tk.Toplevel(self.root)
                year_popup.title("Select Year")
                center_window(year_popup, 250, 100, self.root)

                tk.Label(year_popup, text="Select Year for Report:").pack(pady=(10,5))
                year_var = tk.StringVar(value=str(current_year))
                year_combobox = ttk.Combobox(year_popup, values=years, textvariable=year_var, state="readonly", width=10)
                year_combobox.pack(pady=5)
                year_combobox.focus_set()

                selected_year = []

                def confirm_year():
                    val = year_var.get()
                    if val.isdigit():
                        selected_year.append(int(val))
                        year_popup.destroy()
                    else:
                        messagebox.showwarning("Invalid Year", "Please select a valid year.")

                ttk.Button(year_popup, text="OK", command=confirm_year).pack(pady=(5,10))

                self.root.wait_window(year_popup)

                if not selected_year:
                    return
                year = selected_year[0]

        # Fetch member info
        member = database.get_member_by_id(member_id)
        if not member:
            messagebox.showwarning("Member Not Found", "Could not find member data.")
            return

        # Report header
        org_name = "Dug Hill Rod & Gun Club"
        report_name = f"Full Member Report for {member[3]} {member[4]} ({year})"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        report_text = f"{org_name.center(80)}\n{report_name.center(80)}\nGenerated: {generation_dt}\n{'='*80}\n\n"

        # Personal & contact info
        sections = [
            ("Personal", [("First Name", member[3]), ("Last Name", member[4]), ("DOB", member[5])]),
            ("Contact", [("Email", member[6]), ("Email 2", member[13]), ("Phone", member[7])]),
            ("Access", [("Card Internal #", member[15]), ("Card External #", member[16])]),
            ("Membership", [("Badge", member[1]), ("Type", member[2]), ("Join Date", member[12]), ("Sponsor", member[14])]),
            ("Address", [("Address", member[8]), ("City", member[9]), ("State", member[10]), ("Zip", member[11])])
        ]
        for section, fields in sections:
            report_text += f"  {section}\n"
            for name, value in fields:
                report_text += f"    {name}: {value}\n"
            report_text += "\n"

        # ---- Dues ----
        report_text += "="*80 + "\n  Dues History\n"
        dues = database.get_dues_by_member(member_id, year=year)
        if dues:
            report_text += f"{'Payment Date':12}{'Year':6}{'Amount':8}{'Method':10}{'Notes':40}\n"
            report_text += "-"*80 + "\n"
            total_dues = 0.0
            for d in dues:
                payment_date = d[2] or "N/A"
                amt = float(d[4] or 0.0)
                total_dues += amt
                report_text += f"{payment_date:12}{d[3]:6}{amt:<8.2f}{(d[5] or ''):10}{(d[6] or ''):40}\n"
            report_text += "-"*80 + f"\nTotal Dues: ${total_dues:.2f}\n"
        else:
            report_text += "No dues recorded\n"

        # ---- Work Hours ----
        report_text += "="*80 + "\n  Work Hours\n"
        work_hours = database.get_work_hours_by_member(member_id, year=year)
        if work_hours:
            report_text += f"{'Date':12}{'Hours':6}{'Activity':20}{'Notes':40}\n"
            report_text += "-"*80 + "\n"
            total_hours = 0.0
            for w in work_hours:
                date = w[2] or "N/A"
                hours = float(w[4] or 0.0)
                total_hours += hours
                report_text += f"{date:12}{hours:<6}{(w[3] or ''):20}{(w[5] or ''):40}\n"
            report_text += "-"*80 + f"\nTotal Work Hours: {total_hours}\n"
        else:
            report_text += "No work hours recorded\n"

        # ---- Attendance ----
        report_text += "="*80 + "\n  Meeting Attendance\n"
        attendance = database.get_meeting_attendance(member_id, year=year)
        if attendance:
            report_text += f"{'Date':12}{'Status':20}{'Notes':40}\n"
            report_text += "-"*80 + "\n"
            total_meetings = 0
            for a in attendance:
                date = a[2] or "N/A"
                report_text += f"{date:12}{(a[3] or ''):20}{(a[4] or ''):40}\n"
                total_meetings += 1
            report_text += "-"*80 + f"\nTotal Meetings Attended: {total_meetings}\n"
        else:
            report_text += "No attendance recorded\n"

        # ---- Display in preview window ----
        preview = tk.Toplevel(self.root)
        preview.title(f"Full Member Report - {member[3]} {member[4]} ({year})")
        center_window(preview, 800, 600, parent=self.root)  # <-- Center report window
        text_frame = ttk.Frame(preview)
        text_frame.pack(fill="both", expand=True)
        text_widget = tk.Text(text_frame, wrap="none", font=("Courier New", 10))
        text_widget.insert("1.0", report_text)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True, side="left")
        yscroll = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        yscroll.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(preview, orient="horizontal", command=text_widget.xview)
        xscroll.pack(side="bottom", fill="x")
        text_widget.configure(xscrollcommand=xscroll.set)

        # ---- Buttons ----
        btn_frame = ttk.Frame(preview)
        btn_frame.pack(fill="x", pady=5)
        def save_report_txt():
            path = filedialog.asksaveasfilename(
                initialfile=f"MemberReport_{member[3]}_{member[4]}_{year}.txt",
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt")]
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(report_text)
        def save_report_csv():
            path = filedialog.asksaveasfilename(
                initialfile=f"MemberReport_{member[3]}_{member[4]}_{year}.csv",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")]
            )
            if path:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # Write member info
                    for section, fields in sections:
                        for field, value in fields:
                            writer.writerow([section, field, value])
                    writer.writerow([])
                    # Write dues
                    writer.writerow(["Dues History"])
                    if dues:
                        writer.writerow(["Payment Date", "Year", "Amount", "Method", "Notes"])
                        for d in dues:
                            writer.writerow([d[2], d[3], f"{float(d[4]):.2f}", d[5], d[6]])
                    else:
                        writer.writerow(["No dues recorded"])
                    writer.writerow([])
                    # Work hours
                    writer.writerow(["Work Hours"])
                    if work_hours:
                        writer.writerow(["Date","Hours","Activity","Notes"])
                        for w in work_hours:
                            writer.writerow([w[2], w[4], w[3], w[5]])
                    else:
                        writer.writerow(["No work hours recorded"])
                    writer.writerow([])
                    # Attendance
                    writer.writerow(["Meeting Attendance"])
                    if attendance:
                        writer.writerow(["Date","Status","Notes"])
                        for a in attendance:
                            writer.writerow([a[2], a[3], a[4]])
                    else:
                        writer.writerow(["No attendance recorded"])
        ttk.Button(btn_frame, text="Save as TXT", command=save_report_txt).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Save as CSV", command=save_report_csv).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Close", command=preview.destroy).pack(side="right", padx=10)

            
    # ---------- Load Members ----------
    def load_data(self):
        for tree in self.trees.values():
            tree.delete(*tree.get_children())
        try:
            members = database.get_all_members()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load members: {e}")
            return

        for m in members:
            row_values = [m[1], m[4], m[3], m[2], m[6], m[13], m[7]]
            self.trees["All"].insert("", "end", iid=str(m[0]), values=row_values)
            mt_tree = self.trees.get(m[2])
            if mt_tree:
                mt_tree.insert("", "end", iid=str(m[0]), values=row_values)

    # ---------- Double click ----------
    def _on_tree_double_click(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected:
            return
        member_id = selected[0]
        form = self._open_member_form(member_id)
        self.root.wait_window(form.top)

    # ---------- Print Current Tab ----------
    def _print_members(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        items = tree.get_children()
        if not items:
            messagebox.showwarning("Print", "No members to print in this view.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = f"Member List - {current_tab}"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        generated_text = f"Generated: {generation_dt}"

        headers = [tree.heading(c)["text"] for c in self.TREE_COLUMNS]
        max_total_width = 100
        col_widths = [len(h) for h in headers]
        for idx, col in enumerate(self.TREE_COLUMNS):
            for item in items:
                value = str(tree.item(item, "values")[idx])
                if len(value) > col_widths[idx]:
                    col_widths[idx] = len(value)

        total_width = sum(col_widths) + 2 * len(col_widths)
        if total_width > max_total_width:
            scale = (max_total_width - 2 * len(col_widths)) / sum(col_widths)
            col_widths = [max(4, int(w * scale)) for w in col_widths]

        rows = []
        for item in items:
            row = []
            for idx, col in enumerate(self.TREE_COLUMNS):
                value = str(tree.item(item, "values")[idx])
                if col == "Badge":
                    row.append(value.center(col_widths[idx]))
                else:
                    row.append(value.ljust(col_widths[idx]))
            rows.append("  ".join(row))

        lines_per_page = 40
        total_pages = (len(rows) - 1) // lines_per_page + 1
        pages = [rows[i:i + lines_per_page] for i in range(0, len(rows), lines_per_page)]

        preview_text = ""
        header_line = "  ".join([h.center(col_widths[idx]) if self.TREE_COLUMNS[idx] == "Badge" else h.ljust(col_widths[idx])
                                for idx, h in enumerate(headers)])
        total_members_text = f"Total Members: {len(items)}".center(len(header_line))

        for current_page, page_lines in enumerate(pages, start=1):
            preview_text += f"{org_name.center(len(header_line))}\n"
            preview_text += f"{report_name.center(len(header_line))}\n"
            preview_text += f"{generated_text.center(len(header_line))}\n\n"
            preview_text += header_line + "\n"
            preview_text += "-" * len(header_line) + "\n"
            preview_text += "\n".join(page_lines) + "\n\n"
            preview_text += total_members_text + "\n"
            preview_text += f"Page {current_page} of {total_pages}".center(len(header_line)) + "\n"
            preview_text += "\n" + ("=" * len(header_line)) + "\n\n"

        preview = tk.Toplevel(self.root)
        preview.title(f"Print Preview - {current_tab}")
        text_frame = ttk.Frame(preview)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(text_frame, wrap="none")
        text.insert("1.0", preview_text)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, side="left")
        yscroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        yscroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(preview, orient="horizontal", command=text.xview)
        xscroll.pack(side="bottom", fill="x")
        text.configure(xscrollcommand=xscroll.set)

        btn_frame = ttk.Frame(preview)
        btn_frame.pack(fill="x", pady=5)
        def print_text():
            import tempfile
            temp_file = tempfile.mktemp(".txt")
            with open(temp_file, "w") as f:
                f.write(preview_text)
            os.startfile(temp_file, "print")
        ttk.Button(btn_frame, text="Print", command=print_text).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=preview.destroy).pack(side="right", padx=10)

    # ---------- Search ----------
    def _on_search(self, event=None):
        search_text = self.search_var.get().lower()
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        tree.delete(*tree.get_children())
        try:
            members = database.get_all_members()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load members: {e}")
            return
        for m in members:
            row_values = [m[1], m[4], m[3], m[2], m[6], m[13], m[7]]
            if any(search_text in str(val).lower() for val in row_values):
                tree.insert("", "end", iid=str(m[0]), values=row_values)

    # ---------- Settings ----------
    def open_settings(self):
        SettingsWindow(self.root)


    # ---------- Export Members ----------
    def _show_export_dialog(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_tab_name = current_tab.replace(" ", "_")
        default_filename = f"Members_{safe_tab_name}_{timestamp}.csv"

        path = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Members to CSV"
        )
        if not path:
            return

        try:
            tree = self.trees[current_tab]
            items = tree.get_children()
            if not items:
                messagebox.showwarning("Export", "No members to export in this tab.")
                return

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.FULL_COLUMNS)

                for iid in items:
                    # Fetch full member data from database for each displayed row
                    member = database.get_member_by_id(iid)
                    if member:
                        row_values = [
                            member[1], member[2], member[3], member[4], member[5],
                            member[6], member[13], member[7], member[8], member[9],
                            member[10], member[11], member[12], member[14], member[15],
                            member[16]
                        ]
                        writer.writerow(row_values)

            #messagebox.showinfo("Export Complete",
            #d                    f"Exported {len(items)} members from '{current_tab}' to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export members:\n{e}")
        
        
    def _show_import_dialog(self):
        from tkinter import filedialog
        import csv

        file_path = filedialog.askopenfilename(
            title="Import Members",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not file_path:
            return

        imported_count = 0
        skipped_count = 0

        try:
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    badge = row.get("Badge", "").strip()
                    if not badge:
                        continue  # skip rows without badge
                    existing_member = database.get_member_by_badge(badge)
                    if existing_member:
                        skipped_count += 1
                        continue

                    # Map CSV columns to database order
                    data = (
                        badge,
                        row.get("Membership Type", "").strip(),
                        row.get("First Name", "").strip(),
                        row.get("Last Name", "").strip(),
                        row.get("Date of Birth", "").strip(),
                        row.get("Email Address", "").strip(),
                        row.get("Phone Number", "").strip(),
                        row.get("Address", "").strip(),
                        row.get("City", "").strip(),
                        row.get("State", "").strip(),
                        row.get("Zip Code", "").strip(),
                        row.get("Join Date", "").strip(),
                        row.get("Email Address 2", "").strip(),
                        row.get("Sponsor", "").strip(),
                        row.get("Card/Fob Internal Number", "").strip(),
                        row.get("Card/Fob External Number", "").strip()
                    )
                    database.add_member(data)
                    imported_count += 1

            messagebox.showinfo(
                "Import Complete",
                f"Imported {imported_count} new members.\nSkipped {skipped_count} duplicates."
            )
            self.load_data()

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import members:\n{e}")

            # ---------- Stubs ----------
            
    def _show_recycle_bin(self):
        RecycleBinWindow(self.root, refresh_main_fn=self.load_data)


class NewMemberForm:
    MEMBERSHIP_TYPES = [
        "Probationary", "Associate", "Active", "Life", "Prospective", "Wait List", "Former"
    ]

    def __init__(self, parent, on_save_callback=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Add New Member")
        center_window(self.top, 400, 450, parent)  # <-- Center popup relative to parent
        self.on_save_callback = on_save_callback

        self.entries = {}
        fields = [
            "Badge", "Membership Type", "First Name", "Last Name", "Date of Birth",
            "Email Address", "Phone Number", "Address", "City", "State", "Zip Code",
            "Join Date", "Email Address 2", "Sponsor", "Card/Fob Internal Number",
            "Card/Fob External Number"
        ]

        for idx, field in enumerate(fields):
            tk.Label(self.top, text=field).grid(row=idx, column=0, sticky="e", padx=5, pady=2)
            if field == "Membership Type":
                cb = ttk.Combobox(self.top, values=self.MEMBERSHIP_TYPES, state="readonly")
                cb.grid(row=idx, column=1, padx=5, pady=2, sticky="w")
                self.entries[field] = cb
            else:
                entry = tk.Entry(self.top)
                entry.grid(row=idx, column=1, padx=5, pady=2, sticky="w")
                self.entries[field] = entry

        # Save button
        tk.Button(self.top, text="Save", command=self._save_member).grid(
            row=len(fields), column=0, columnspan=2, pady=10
        )

    def _save_member(self):
        data = (
            self.entries["Badge"].get().strip(),
            self.entries["Membership Type"].get().strip(),
            self.entries["First Name"].get().strip(),
            self.entries["Last Name"].get().strip(),
            self.entries["Date of Birth"].get().strip(),
            self.entries["Email Address"].get().strip(),
            self.entries["Phone Number"].get().strip(),
            self.entries["Address"].get().strip(),
            self.entries["City"].get().strip(),
            self.entries["State"].get().strip(),
            self.entries["Zip Code"].get().strip(),
            self.entries["Join Date"].get().strip(),
            self.entries["Email Address 2"].get().strip(),
            self.entries["Sponsor"].get().strip(),
            self.entries["Card/Fob Internal Number"].get().strip(),
            self.entries["Card/Fob External Number"].get().strip()
        )

        if not data[0] or not data[2] or not data[3]:  # Badge, First Name, Last Name
            messagebox.showwarning("Validation Error", "Badge, First Name, and Last Name are required.")
            return

        try:
            database.add_member(data)
            if self.on_save_callback:
                self.on_save_callback()
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add member: {e}")


class RecycleBinWindow:
    def __init__(self, parent, refresh_main_fn=None):
        self.parent = parent
        self.refresh_main_fn = refresh_main_fn

        self.top = tk.Toplevel(parent)
        self.top.title("Recycle Bin")
        self.top.geometry("900x500")
        center_window(self.top, 900, 500, parent)  # <-- Center popup relative to parent

        # ----- Top button frame -----
        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="✔️ Restore Selected", command=self.restore_selected).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="❌ Delete Selected Permanently", command=self.delete_selected).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🗑️ Empty Recycle Bin", command=self.empty_recycle_bin).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Close", command=self.top.destroy).pack(side="right", padx=10)

        # ----- Treeview -----
        columns = (
            "Badge", "Last Name", "First Name", "Membership Type",
            "Email Address", "Phone Number"
        )

        self.tree = ttk.Treeview(self.top, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
            if col == "Badge":
                self.tree.column(col, width=80, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        # Scrollbar
        yscroll = ttk.Scrollbar(self.top, orient="vertical", command=self.tree.yview)
        yscroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=yscroll.set)

        # Right-click menu
        self.row_menu = tk.Menu(self.top, tearoff=0)
        self.row_menu.add_command(label="Restore Selected", command=self.restore_selected)
        self.row_menu.add_command(label="Delete Selected Permanently", command=self.delete_selected)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="Empty Recycle Bin", command=self.empty_recycle_bin)
        self.tree.bind("<Button-3>", self._show_row_menu)

        self.load_deleted_members()

    def load_deleted_members(self):
        self.tree.delete(*self.tree.get_children())
        try:
            deleted_members = database.get_deleted_members()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load deleted members:\n{e}", parent=self.top)
            return

        for m in deleted_members:
            row_values = [m[1], m[4], m[3], m[2], m[6], m[7]]  # Badge, Last, First, Membership, Email, Phone
            self.tree.insert("", "end", iid=str(m[0]), values=row_values)

    def restore_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Restore", "Please select member(s) to restore.", parent=self.top)
            return
        confirm = messagebox.askyesno("Restore", f"Restore {len(selected)} member(s)?", parent=self.top)
        if not confirm:
            return
        for member_id in selected:
            try:
                database.restore_member_by_id(member_id)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore member {member_id}: {e}", parent=self.top)
        self.load_deleted_members()
        if self.refresh_main_fn:
            self.refresh_main_fn()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "Please select member(s) to delete permanently.", parent=self.top)
            return
        confirm = messagebox.askyesno(
            "Delete",
            f"Permanently delete {len(selected)} member(s)? This cannot be undone.",
            parent=self.top
        )
        if not confirm:
            return
        for member_id in selected:
            try:
                database.permanently_delete_member_by_id(member_id)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete member {member_id}: {e}", parent=self.top)
        self.load_deleted_members()
        if self.refresh_main_fn:
            self.refresh_main_fn()

    def empty_recycle_bin(self):
        confirm = messagebox.askyesno(
            "Empty Recycle Bin",
            "This will permanently delete ALL members in the recycle bin. "
            "This action cannot be undone. Continue?",
            parent=self.top
        )
        if not confirm:
            return
        try:
            for member_id in self.tree.get_children():
                database.permanently_delete_member_by_id(member_id)
            self.load_deleted_members()
            if self.refresh_main_fn:
                self.refresh_main_fn()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to empty recycle bin: {e}", parent=self.top)

    def _show_row_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
            self.row_menu.post(event.x_root, event.y_root)
        else:
            self.row_menu.unpost()


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x320")
        center_window(self, 400, 320, parent)
        self.resizable(False, False)

        # Load settings
        self.settings = database.get_all_settings()

        row = 0
        tk.Label(self, text="Dues Amounts", font=("Arial", 12, "bold")).grid(row=row, column=0, columnspan=2, pady=5)

        row += 1
        tk.Label(self, text="Probationary:").grid(row=row, column=0, sticky="w", padx=10)
        self.prob_var = tk.StringVar(value=self.settings.get("dues_probationary", "150"))
        tk.Entry(self, textvariable=self.prob_var, justify="left").grid(row=row, column=1, padx=10)

        row += 1
        tk.Label(self, text="Associate:").grid(row=row, column=0, sticky="w", padx=10)
        self.assoc_var = tk.StringVar(value=self.settings.get("dues_associate", "300"))
        tk.Entry(self, textvariable=self.assoc_var, justify="left").grid(row=row, column=1, padx=10)

        row += 1
        tk.Label(self, text="Active:").grid(row=row, column=0, sticky="w", padx=10)
        self.active_var = tk.StringVar(value=self.settings.get("dues_active", "150"))
        tk.Entry(self, textvariable=self.active_var, justify="left").grid(row=row, column=1, padx=10)

        # NEW: Life Member dues
        row += 1
        tk.Label(self, text="Life:").grid(row=row, column=0, sticky="w", padx=10)
        self.life_var = tk.StringVar(value=self.settings.get("dues_life", "0"))
        tk.Entry(self, textvariable=self.life_var, justify="left", state="disabled").grid(row=row, column=1, padx=10)

        row += 2
        tk.Label(self, text="Default Year:", font=("Arial", 12, "bold")).grid(row=row, column=0, sticky="w", padx=10)
        self.year_var = tk.StringVar(value=self.settings.get("default_year"))
        tk.Entry(self, textvariable=self.year_var, justify="left").grid(row=row, column=1, padx=10)

        row += 2
        tk.Button(self, text="Save", command=self.save_settings).grid(row=row, column=0, columnspan=2, pady=15)

    def save_settings(self):
        try:
            database.set_setting("dues_probationary", int(self.prob_var.get()))
            database.set_setting("dues_associate", int(self.assoc_var.get()))
            database.set_setting("dues_active", int(self.active_var.get()))
            database.set_setting("dues_life", 0)   # NEW
            database.set_setting("default_year", int(self.year_var.get()))
            messagebox.showinfo("Saved", "Settings have been updated.")
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for dues and year.")



DATE_FMT = "%m/%d/%Y"
STATUS_OPTIONS = ["Attended", "Exemption Approved"]
METHOD_OPTIONS = ["Cash", "Check", "Electronic"]


class DataTab:
    def __init__(self, parent, columns, db_load_func, db_add_func, db_update_func, db_delete_func,
                 entry_fields, row_adapter=None):
        self.parent = parent
        self.columns = columns
        self.db_load_func = db_load_func
        self.db_add_func = db_add_func
        self.db_update_func = db_update_func
        self.db_delete_func = db_delete_func
        self.entry_fields = entry_fields
        self.row_adapter = row_adapter or (lambda r: list(r[2:]))

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        #self.tree.bind("<Double-1>", self.edit_record)
        self.member_id = None

    def load_records(self, member_id):
        self.member_id = member_id
        for row in self.tree.get_children():
            self.tree.delete(row)
        records = self.db_load_func(member_id)
        for r in records:
            values = self.row_adapter(r)
            self.tree.insert("", "end", iid=r[0], values=values)

    def edit_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))

        popup = tk.Toplevel(self.parent)
        popup.title("Edit Entry")
        editors = []
        for i, field in enumerate(self.entry_fields):
            label = field[0]
            opts = field[2] if len(field) == 3 else {}
            ttk.Label(popup, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            new_var = tk.StringVar(value=current_values[i])
            if opts.get("widget") == "combobox":
                w = ttk.Combobox(popup, textvariable=new_var, values=opts.get("values", []), state="readonly")
            else:
                w = ttk.Entry(popup, textvariable=new_var)
            w.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            editors.append(new_var)

        def save():
            new_vals = [v.get() for v in editors]
            try:
                self.db_update_func(row_id, *new_vals)
                self.load_records(self.member_id)
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(popup, text="Save", command=save).grid(row=len(self.entry_fields), column=0, pady=8)
        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(row=len(self.entry_fields), column=1, pady=8)


# ----------------------- Member Form -----------------------
class MemberForm(tk.Frame):
    def __init__(self, parent, member_id=None, on_save_callback=None, select_tab=None):
        
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")

        # ----- Set reasonable default size first -----
        default_width = 850
        default_height = 400
        self.top.geometry(f"{default_width}x{default_height}")

        # ----- Force Tkinter to compute natural size -----
        self.top.update_idletasks()
        natural_width = self.top.winfo_width()
        natural_height = self.top.winfo_height()
        width = max(default_width, natural_width)
        height = max(default_height, natural_height)
        self.top.geometry(f"{width}x{height}")

        # ----- Center the window on the screen -----
        center_window(self.top, width, height)

        self.member_id = member_id
        self.on_save_callback = on_save_callback

        # ----- Notebook ----- 
        style = ttk.Style(self.top)
        style.configure(
            "CustomNotebook.TNotebook.Tab",
            padding=[12, 5],
            anchor="center"
        )

        self.notebook = ttk.Notebook(self.top, style="CustomNotebook.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # ----- Tabs -----
        self.tab_basic = ttk.Frame(self.notebook)
        self.tab_contact = ttk.Frame(self.notebook)
        self.tab_membership = ttk.Frame(self.notebook)
        self.tab_dues = ttk.Frame(self.notebook)
        self.tab_work_hours = ttk.Frame(self.notebook)
        self.tab_attendance = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_basic, text="Basic Info")
        self.notebook.add(self.tab_contact, text="Contact")
        self.notebook.add(self.tab_membership, text="Membership")
        self.notebook.add(self.tab_dues, text="Dues History")
        self.notebook.add(self.tab_work_hours, text="Work Hours")
        self.notebook.add(self.tab_attendance, text="Meeting Attendance")

        # ----- Select requested tab if provided -----
        if select_tab:
            tab_mapping = {
                "basic": self.tab_basic,
                "contact": self.tab_contact,
                "membership": self.tab_membership,
                "dues": self.tab_dues,
                "work_hours": self.tab_work_hours,
                "attendance": self.tab_attendance
            }
            if select_tab in tab_mapping:
                self.notebook.select(tab_mapping[select_tab])

        # ----- Resize tabs dynamically -----
        def resize_tabs(event=None):
            total_tabs = len(self.notebook.tabs())
            if total_tabs == 0:
                return
            notebook_width = self.notebook.winfo_width()
            tab_width = min(150, notebook_width // total_tabs)
            style.configure("CustomNotebook.TNotebook.Tab", width=tab_width)

        resize_tabs()
        self.notebook.bind("<Configure>", resize_tabs)

        # ----- Variables -----
        self.badge_number_var = tk.StringVar()
        self.membership_type_var = tk.StringVar()
        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.dob_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.state_var = tk.StringVar()
        self.zip_var = tk.StringVar()
        self.join_date_var = tk.StringVar()
        self.email2_var = tk.StringVar()
        self.sponsor_var = tk.StringVar()
        self.card_internal_var = tk.StringVar()
        self.card_external_var = tk.StringVar()
        self.membership_types = ["Probationary", "Associate", "Active", "Life", "Prospective", "Wait List", "Former"]

        self._display_labels = {}

        # ----- Build read-only tabs -----
        self._build_read_only_tab(self.tab_basic, [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._edit_basic, "basic")

        self._build_read_only_tab(self.tab_contact, [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._edit_contact, "contact")

        self._build_read_only_tab(self.tab_membership, [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var)
        ], self._edit_membership, "membership")

        # ----- Data tabs -----
        self.dues_tab = DuesTab(self.tab_dues, self.member_id)
        self.work_tab = WorkHoursTab(self.tab_work_hours, self.member_id)
        self.attendance_tab = AttendanceTab(self.tab_attendance, self.member_id)

        # ----- Load member data if ID provided -----
        if self.member_id:
            self._load_member_data()


        # ----- Set reasonable default window size -----
        self.top.update_idletasks()  # calculate natural size
        natural_width = self.top.winfo_width()
        natural_height = self.top.winfo_height()
        width = max(850, min(natural_width, 1000))  # limit max width
        height = max(300, natural_height)
        self.top.geometry(f"{width}x{height}")



    def _build_read_only_tab(self, tab, fields, edit_callback, tab_key):
        tab.grid_columnconfigure(0, weight=1)  # left column stretches
        tab.grid_columnconfigure(1, weight=1)  # right column stretches

        self._display_labels[tab_key] = {}

        # Define a larger font (adjust size as needed)
        big_font = font.nametofont("TkDefaultFont").copy()
        big_font.configure(size=12, weight="bold")   # e.g., bigger and bold
        label_font = font.nametofont("TkDefaultFont").copy()
        label_font.configure(size=12)

        for idx, (label_text, var) in enumerate(fields):
            ttk.Label(
                tab, text=label_text + ":", font=big_font
            ).grid(row=idx, column=0, sticky="e", padx=5, pady=4)

            lbl = ttk.Label(tab, text=var.get(), font=label_font)
            lbl.grid(row=idx, column=1, sticky="w", padx=5, pady=4)

            self._display_labels[tab_key][label_text] = (lbl, var)

        ttk.Button(tab, text="Edit", command=edit_callback).grid(
            row=len(fields), column=0, columnspan=2, pady=12
        )
        
    def _load_member_data(self):
        if not self.member_id:
            return
        m = database.get_member_by_id(self.member_id)
        if not m:
            return
        mapping = {
            "badge_number": m[1],
            "membership_type": m[2],
            "first_name": m[3],
            "last_name": m[4],
            "dob": m[5],
            "email": m[6],
            "phone": m[7],
            "address": m[8],
            "city": m[9],
            "state": m[10],
            "zip": m[11],
            "join_date": m[12],
            "email2": m[13],
            "sponsor": m[14],
            "card_internal": m[15],
            "card_external": m[16]
        }
        for var_name, value in mapping.items():
            var = getattr(self, f"{var_name}_var", None)
            if var:
                if var_name in ("dob", "join_date") and value:
                    try:
                        dt = datetime.strptime(value, "%Y-%m-%d")
                        var.set(dt.strftime("%m-%d-%Y"))
                    except ValueError:
                        var.set(value)
                else:
                    var.set(value or "")
        # Update read-only labels
        for tab_labels in self._display_labels.values():
            for lbl, var in tab_labels.values():
                lbl.config(text=var.get())

        # Load data tabs
        self.work_tab.load_records(self.member_id)
        self.attendance_tab.load_records(self.member_id)

    # --- Edit callbacks ---
    def _edit_basic(self):
        self._open_edit_popup_generic("Basic Info", [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._save_basic)

    def _edit_contact(self):
        self._open_edit_popup_generic("Contact", [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._save_contact)

    def _edit_membership(self):
        self._open_edit_popup_generic("Membership", [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var)
        ], self._save_membership)

    def _open_edit_popup_generic(self, title, field_names, save_callback):
        popup = tk.Toplevel()
        popup.title(title)

        # Make a frame to contain all widgets and center them
        frame = ttk.Frame(popup, padding=10)
        frame.pack(fill="both", expand=True)

        # Configure columns so labels are right-aligned, entries expand
        frame.columnconfigure(0, weight=1, uniform="a")
        frame.columnconfigure(1, weight=2, uniform="a")

        editors = []
        for i, (label, var) in enumerate(field_names):
            ttk.Label(frame, text=label + ":", font=("Arial", 12)).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            entry_var = tk.StringVar(value=var.get())

            # Use Combobox for Membership Type
            if label == "Membership Type":
                w = ttk.Combobox(frame, textvariable=entry_var,
                                values=self.membership_types, state="readonly", font=("Arial", 12))
            else:
                w = ttk.Entry(frame, textvariable=entry_var, font=("Arial", 12))

            w.grid(row=i, column=1, padx=5, pady=3, sticky="ew")
            editors.append((var, entry_var))

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=len(field_names), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=lambda: save()).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=popup.destroy).pack(side="left", padx=5)

        def save():
            for var, entry_var in editors:
                var.set(entry_var.get())
            save_callback()
            popup.destroy()

        # ----- Center popup on screen -----
        popup.update_idletasks()  # calculate natural size
        width = popup.winfo_width()
        height = popup.winfo_height()
        center_window(popup, width, height)


    def _save_basic(self):
        database.update_member_basic(self.member_id,
                                     self.first_name_var.get(),
                                     self.last_name_var.get(),
                                     self.dob_var.get())
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)

    def _save_contact(self):
        database.update_member_contact(self.member_id,
                                       self.email_var.get(),
                                       self.email2_var.get(),
                                       self.phone_var.get(),
                                       self.address_var.get(),
                                       self.city_var.get(),
                                       self.state_var.get(),
                                       self.zip_var.get())
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)

    def _save_membership(self):
        database.update_member_membership(self.member_id,
                                          self.badge_number_var.get(),
                                          self.membership_type_var.get(),
                                          self.join_date_var.get(),
                                          self.sponsor_var.get(),
                                          self.card_internal_var.get(),
                                          self.card_external_var.get())
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)


# ----------------------- Specialized Tabs -----------------------
class DuesTab(DataTab):
    def __init__(self, parent, member_id):
        super().__init__(
            parent,
            columns=["Date", "Year", "Amount", "Method", "Notes"],
            db_load_func=database.get_dues_by_member,
            db_add_func=self._add_dues,
            db_update_func=self._update_dues,
            db_delete_func=database.delete_dues_payment,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Year", tk.StringVar()),
                ("Amount", tk.StringVar()),
                ("Method", tk.StringVar(), {"widget": "combobox", "values": METHOD_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",
                r[3],
                f"{float(r[4]):.2f}" if r[4] else "0.00",
                r[5] or "",
                r[6] or ""
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind double-click event on the tree (or data table) to the handler
        self.tree.bind("<Double-1>", self.on_dues_double_click)

    def _transform_entries(self, entries):
        date_str, year, amount_str, method, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            payment_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            payment_date = date_str
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0
        year = str(year) if year else str(datetime.now().year)
        return payment_date, amount, method or "", notes or "", year

    def _add_dues(self, *entries):
        payment_date, amount, method, notes, year = self._transform_entries(entries)
        database.add_dues_payment(self.member_id, amount, payment_date, method, notes, year)
        self.load_records(self.member_id)

    def _update_dues(self, payment_id, *entries):
        payment_date, amount, method, notes, year = self._transform_entries(entries)
        database.update_dues_payment(payment_id, amount=amount, payment_date=payment_date,
                                     method=method, notes=notes, year=year)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")
        default_year = database.get_default_year()
        self._open_edit_popup("Add Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              self._add_dues, [today_str, str(default_year), "", "", ""])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              lambda *vals: self._update_dues(row_id, *vals), current_values)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_dues_payment(row_id)
            self.load_records(self.member_id)

    # Double-click handler for dues table
    def on_dues_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              lambda *vals: self._update_dues(row_id, *vals), current_values)
    def _open_edit_popup(self, title, labels, save_func, default_values):
        # Create the popup window
        popup = tk.Toplevel(self.parent)
        popup.title(title)

        # Create form entries
        form_entries = []
        row = 0
        for label, default_value in zip(labels, default_values):
            ttk.Label(popup, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="w")
            
            if label == "Method":
                # Create a combobox for "Method"
                entry_var = tk.StringVar(value=default_value)
                combobox = ttk.Combobox(popup, textvariable=entry_var, values=METHOD_OPTIONS)
                combobox.grid(row=row, column=1, padx=5, pady=5)
                form_entries.append(entry_var)
            else:
                # Create a regular entry for other fields
                entry_var = tk.StringVar(value=default_value)
                entry = ttk.Entry(popup, textvariable=entry_var)
                entry.grid(row=row, column=1, padx=5, pady=5)
                form_entries.append(entry_var)
            
            row += 1

        # Save button to save the data
        def save():
            entries = [entry.get() for entry in form_entries]
            save_func(*entries)  # Call the provided save function with the entries
            popup.destroy()

        ttk.Button(popup, text="Save", command=save).grid(row=row, column=0, columnspan=2, pady=5)

        # Make the popup modal
        popup.grab_set()
        popup.mainloop()


class WorkHoursTab(DataTab):
    def __init__(self, parent, member_id):
        super().__init__(
            parent,
            columns=["Date", "Activity", "Hours", "Notes"],  # Changed order: Activity and Hours
            db_load_func=database.get_work_hours_by_member,
            db_add_func=self._add_work,
            db_update_func=self._update_work,
            db_delete_func=database.delete_work_hours,
            entry_fields=[ 
                ("Date", tk.StringVar()),
                ("Hours", tk.StringVar()),
                ("Activity", tk.StringVar()),  # Changed field name to match updated order
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",  # Date is still in the second column
                r[3] or "",  # Activity is now the second column (was third before)
                f"{float(r[4]):.1f}" if r[4] else "0.0",  # Hours is now the third column (was second before)
                r[5] or ""   # Notes remains the same
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind double-click event on the tree (or data table) to the handler
        self.tree.bind("<Double-1>", self.on_work_hours_double_click)

    def _transform_entries(self, entries):
        date_str, hours_str, activity_str, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            date = date_str
        try:
            hours = float(hours_str)
        except ValueError:
            hours = 0.0
        return date, hours, activity_str or "", notes or ""

    def _add_work(self, *entries):
        date, hours, activity_str, notes = self._transform_entries(entries)
        database.add_work_hours(self.member_id, date, hours, activity_str, notes)
        self.load_records(self.member_id)

    def _update_work(self, work_id, *entries):
        date, hours, activity_str, notes = self._transform_entries(entries)
        database.update_work_hours(work_id, date=date, hours=hours, activity=activity_str, notes=notes)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")  # Get today's date
        # Open the edit popup, passing default values
        self._open_edit_popup("Add Work Hours", ["Date", "Hours", "Activity", "Notes"], 
                              self._add_work, [today_str, "", "", ""])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        
        # Ensure the values are in the correct order: Date, Activity, Hours, Notes
        current_values = [
            current_values[0],  # Date
            current_values[1],  # Activity
            current_values[2],  # Hours
            current_values[3]   # Notes
        ]
        
        self._open_edit_popup("Edit Work Hours", ["Date", "Activity", "Hours", "Notes"], 
                            lambda *vals: self._update_work(row_id, *vals), current_values)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_work_hours(row_id)
            self.load_records(self.member_id)

    # Double-click handler for work hours table
    def on_work_hours_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Work Hours", ["Date", "Activity", "Hours", "Notes"],
                              lambda *vals: self._update_work(row_id, *vals), current_values)

    def _open_edit_popup(self, title, labels, save_function, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)

        entry_vars = {}
        entries = []

        # Correct label order: Date, Activity, Hours, Notes
        correct_labels = ["Date", "Activity", "Hours", "Notes"]

        # Create label and entry widgets for each field
        for idx, label in enumerate(correct_labels):  # Use correct_labels order
            frame = tk.Frame(popup)
            tk.Label(frame, text=label).pack(side=tk.LEFT)

            var = tk.StringVar()
            # Set default value if any
            if default_values and idx < len(default_values):
                var.set(default_values[idx])

            # Create entry field for each label
            entry = tk.Entry(frame, textvariable=var)
            entry.pack(side=tk.RIGHT)
            entry_vars[label] = var
            entries.append(entry)
            frame.pack(fill="x", padx=10, pady=5)

        def save_record():
            # Get the values from the form
            date = entry_vars["Date"].get()
            hours = entry_vars["Hours"].get()
            activity = entry_vars["Activity"].get()
            notes = entry_vars["Notes"].get()

            # Call the save_function, e.g., _add_work or another
            save_function(date, hours, activity, notes)
            popup.destroy()

        save_button = tk.Button(popup, text="Save", command=save_record)
        save_button.pack(pady=10)

        popup.mainloop()


class AttendanceTab(DataTab):
    def __init__(self, parent, member_id):
        # Initialize the DataTab with correct parameters for the AttendanceTab
        super().__init__(
            parent,
            columns=["Date", "Status", "Notes"],
            db_load_func=database.get_meeting_attendance,
            db_add_func=self._add_attendance,
            db_update_func=self._update_attendance,
            db_delete_func=database.delete_meeting_attendance,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Status", tk.StringVar(), {"widget": "combobox", "values": STATUS_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",
                r[3] or "",
                r[4] or ""
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind the double-click event on the tree (or data table)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def edit_selected(self):
        """Triggered when 'Edit' button is clicked"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))

        # Ensure values are in correct order: Date, Status, Notes
        current_values = [
            current_values[0],  # Date
            current_values[1],  # Status
            current_values[2]   # Notes
        ]

        # Open the edit popup
        self._open_edit_popup("Edit Attendance", ["Date", "Status", "Notes"],
                              lambda *vals: self._update_attendance(row_id, *vals), current_values)

    def _on_tree_double_click(self, event):
        """Triggered when a row in the tree is double-clicked"""
        self.edit_selected()

    def _transform_entries(self, entries):
        date_str, status, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            date = date_str
        return date, status or "", notes or ""

    def _add_attendance(self, *entries):
        date, status, notes = self._transform_entries(entries)
        database.add_meeting_attendance(self.member_id, date, status, notes)
        self.load_records(self.member_id)

    def _update_attendance(self, attendance_id, *entries):
        date, status, notes = self._transform_entries(entries)
        database.update_meeting_attendance(attendance_id, date=date, status=status, notes=notes)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")
        self._open_edit_popup("Add Attendance", ["Date", "Status", "Notes"],
                              self._add_attendance, [today_str, STATUS_OPTIONS[0], ""])

    def _open_edit_popup(self, title, labels, save_function, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)

        entry_vars = {}
        entries = []

        for idx, label in enumerate(labels):
            frame = tk.Frame(popup)
            tk.Label(frame, text=label).pack(side=tk.LEFT)

            var = tk.StringVar()
            if default_values and idx < len(default_values):
                var.set(default_values[idx])

            if label == "Status":
                entry = ttk.Combobox(frame, textvariable=var, values=STATUS_OPTIONS)
            else:
                entry = tk.Entry(frame, textvariable=var)

            entry.pack(side=tk.RIGHT)
            entry_vars[label] = var
            entries.append(entry)
            frame.pack(fill="x", padx=10, pady=5)

        def save_record():
            date = entry_vars["Date"].get()
            status = entry_vars["Status"].get()
            notes = entry_vars["Notes"].get()
            save_function(date, status, notes)
            popup.destroy()

        save_button = tk.Button(popup, text="Save", command=save_record)
        save_button.pack(pady=10)

        popup.mainloop()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_meeting_attendance(row_id)
            self.load_records(self.member_id)





class ReportsWindow(tk.Toplevel):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.title("Reports")
        self.geometry("900x600")
        from gui import center_window
        center_window(self, 900, 600, parent)

                # Keep it on top of the main window
        self.transient(parent)   # Associate with main window
        self.grab_set()          # Make it modal (prevents interacting with main window)
        self.focus()             # Ensure it gets focus

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=5, pady=5)

        # ---------------- Dues Tab ---------------- #
        dues_tab_frame = ttk.Frame(notebook)
        notebook.add(dues_tab_frame, text="Dues")
        DuesReport(dues_tab_frame, member_id).pack(fill="both", expand=True)

        # ---------------- Work Hours Tab ---------------- #
        work_tab_frame = ttk.Frame(notebook)
        notebook.add(work_tab_frame, text="Work Hours")
        Work_HoursReport(work_tab_frame, member_id).pack(fill="both", expand=True)

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
        self.year_var.trace_add("write", lambda *args: self.populate_report())

        if self.include_month:
            tk.Label(frame, text="Month:").pack(side="left")
            months = ["All"] + list(calendar.month_name[1:])
            month_cb = ttk.Combobox(frame, values=months, textvariable=self.month_var, state="readonly", width=10)
            month_cb.pack(side="left", padx=(0,10))
            month_cb.configure(background="white")
            self.month_var.trace_add("write", lambda *args: self.populate_report())


        tk.Button(frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=5)
        tk.Button(frame, text="Print Report", command=self.print_report).pack(side="left", padx=5)

        # Checkbox to exclude names
        self.exclude_names_var = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(frame, text="Exclude Names From Print", variable=self.exclude_names_var)
        cb.pack(side="left", padx=10)


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

        # Alignment rules
        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.replace("_"," ").title(),
                              command=lambda c=col: self.sort_column(c, False))
            if col in ("badge", "year", "method", "last_payment_date"):
                self.tree.column(col, width=width, anchor="center")
            elif col in ("amount_due", "balance_due", "amount_paid", "work_hours"):
                self.tree.column(col, width=width, anchor="e")
            else:
                self.tree.column(col, width=width, anchor="w")

        self._sort_column = None
        self._sort_reverse = False

    def sort_column(self, col, reverse):
        # Extract data
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        
        # Detect numeric columns
        def try_num(val):
            try:
                return float(val)
            except ValueError:
                return val

        data.sort(key=lambda t: try_num(t[0]), reverse=reverse)

        # Rearrange rows
        for index, (_, k) in enumerate(data):
            self.tree.move(k, "", index)

        # Reset all headings
        for c in self.columns:
            self.tree.heading(c, text=c.replace("_"," ").title(),
                              command=lambda _c=c: self.sort_column(_c, False))

        # Apply arrow
        arrow = " ▲" if not reverse else " ▼"
        self.tree.heading(col, text=col.replace("_"," ").title() + arrow,
                          command=lambda: self.sort_column(col, not reverse))

        # Track current sort
        self._sort_column = col
        self._sort_reverse = reverse

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

        # alignment rules for printing
        alignment = {}
        for col in self.columns:
            if col in ("badge", "year", "method", "last_payment_date"):
                alignment[col] = "center"
            elif col in ("amount_due", "balance_due", "amount_paid"):
                alignment[col] = "right"
            else:
                alignment[col] = "left"

        # Pagination
        lines_per_page = 40
        pages = []
        current_lines = []

        def add_header():
            current_lines.append(org_name.center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append(report_name.center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append(f"Generated: {generation_dt}".center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append(f"Timeframe: {timeframe}".center(sum(col_widths) + len(col_widths) * 3))
            current_lines.append("=" * (sum(col_widths) + len(col_widths) * 3))
            header_line = ""
            for col, h, w in zip(self.columns, headers, col_widths):
                if alignment[col] == "center":
                    header_line += h.center(w + 3)
                elif alignment[col] == "right":
                    header_line += h.rjust(w + 3)
                else:
                    header_line += h.ljust(w + 3)
            current_lines.append(header_line)
            current_lines.append("-" * (sum(col_widths) + len(col_widths) * 3))

        add_header()
        row_count = 0

        for item in items:
            row = list(self.tree.item(item, "values"))
            # Replace names with "*****" if checkbox is selected
            if self.exclude_names_var.get():
                # Assume the "name" column is index 1
                if len(row) > 1:
                    row[1] = "*****"

            line = ""
            for col, val, w in zip(self.columns, row, col_widths):
                val = str(val)
                if alignment[col] == "center":
                    line += val.center(w + 3)
                elif alignment[col] == "right":
                    line += val.rjust(w + 3)
                else:
                    line += val.ljust(w + 3)
            current_lines.append(line)
            row_count += 1

            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()

        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)

        for i, page_lines in enumerate(pages, start=1):
            footer_width = sum(col_widths) + len(col_widths) * 3
            page_lines.append("=" * footer_width)
            page_lines.append(f"Page {i} of {total_pages}".center(footer_width))
            page_lines.append("End of Report".center(footer_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        text = tk.Text(print_window, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.pack(fill="both", expand=True)

        vsb = ttk.Scrollbar(print_window, orient="vertical", command=text.yview)
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(print_window, orient="horizontal", command=text.xview)
        hsb.pack(side="bottom", fill="x")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

    def populate_report(self):
        raise NotImplementedError("populate_report must be implemented in subclass")

    def on_double_click(self, event, report_type=None):
        selected = self.tree.selection()
        if not selected:
            return

        badge_number = self.tree.item(selected[0], "values")[0]
        member = database.get_member_by_badge(badge_number)
        if member:
            member_id = member[0]

            # Map report type to the desired tab
            tab_for_report = {
                "dues": "dues",
                "work_hours": "work_hours",
                "attendance": "attendance"
            }

            selected_tab = tab_for_report.get(report_type, "basic")

            MemberForm(self, member_id=member_id, select_tab=selected_tab)


# ---------------- Dues Report ---------------- #
class DuesReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "membership_type", "amount_due", "balance_due",
                        "year", "last_payment_date", "amount_paid", "method")
        self.column_widths = (60, 150, 110, 80, 80, 60, 120, 80, 80)
        super().__init__(parent, member_id, include_month=False)
        self.tree.bind("<Double-1>", lambda e: self.on_double_click(e, report_type="dues"))
        self.populate_report()


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

# ---------------- Work Hours Report ---------------- #
class Work_HoursReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "work_hours")
        self.column_widths = (10, 260, 120)
        super().__init__(parent, member_id)
        self.tree.bind("<Double-1>", lambda e: self.on_double_click(e, report_type="work_hours"))
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

# ---------------- Attendance Report ---------------- #
class AttendanceReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "status")
        self.column_widths = (90, 260, 120)
        super().__init__(parent, member_id)
        self.tree.bind("<Double-1>", lambda e: self.on_double_click(e, report_type="attendance"))
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

if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
