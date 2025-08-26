import tkinter as tk
from tkinter import ttk, messagebox
import os
import database
import member_form
import settings_window
from reports_window import ReportsWindow
from datetime import datetime




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
        self.root.geometry("1100x600")

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
        file_menu.add_command(label="Import ⬆️", command=self._show_import_dialog)
        file_menu.add_command(label="Export ⬇️", command=self._show_export_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Print Current Tab 🖨", command=self._print_members)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        members_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Members", menu=members_menu)
        members_menu.add_command(label="➕ Add Member", command=self.add_member)
        members_menu.add_command(label="✏️ Edit Selected", command=self.edit_selected)
        members_menu.add_command(label="❌ Delete Selected", command=self.delete_selected)

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
        self.row_menu.add_command(label="Full Member Report", command=self._full_member_report_from_menu)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="Delete Member", command=self._delete_selected_row)

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
        for col in columns:
            tree.heading(col, text=col)
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

    # ---------- Member Management ----------
    def add_member(self):
        form = member_form.NewMemberForm(self.root, on_save_callback=self.load_data)
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
            messagebox.showwarning("No selection", "Please select members to delete.")
            return
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
            messagebox.showwarning("No selection", "Please select a member to delete.")
            return
        confirm = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this member?")
        if confirm:
            member_id = selected[0]
            database.soft_delete_member_by_id(member_id)
            self.load_data()
            if self.recycle_bin_refresh_fn:
                self.recycle_bin_refresh_fn()

    def _open_member_form(self, member_id=None):
        return member_form.MemberForm(self.root, member_id, on_save_callback=lambda mid, mtype=None: self.load_data())

    # ---------- Right-click ----------
    def _show_row_menu(self, event):
        tree = event.widget
        row_id = tree.identify_row(event.y)
        if row_id:
            tree.selection_set(row_id)
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
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member.")
            return
        member_id = selected[0]
        self._full_member_report(member_id)

    # ---------- Full Member Report ----------
    def _full_member_report(self, member_id):
        try:
            member = database.get_member_by_id(member_id)
            if not member:
                messagebox.showwarning("Member Not Found", "Could not find member data.")
                return
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to retrieve member: {e}")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = "Full Member Report"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        generated_text = f"Generated: {generation_dt}"

        headers = self.FULL_COLUMNS
        values = [
            member[1], member[2], member[3], member[4], member[5], member[6], member[13], member[7],
            member[8], member[9], member[10], member[11], member[12], member[14], member[15], member[16]
        ]

        max_header_len = max(len(h) for h in headers)
        row_lines = [f"{h.ljust(max_header_len)}    {str(v)}" for h, v in zip(headers, values)]

        total_members_text = "1 Member"

        header_line_len = max(len(org_name), len(report_name), len(generated_text), max(len(line) for line in row_lines))
        report_text = f"{org_name.center(header_line_len)}\n"
        report_text += f"{report_name.center(header_line_len)}\n"
        report_text += f"{generated_text.center(header_line_len)}\n"
        report_text += "=" * header_line_len + "\n\n"  # Separator under header
        report_text += "\n".join(row_lines) + "\n\n"
        report_text += "=" * header_line_len + "\n"    # Separator above footer
        


        # Display
        preview = tk.Toplevel(self.root)
        preview.title(f"Full Member Report - {member[3]} {member[4]}")
        text_frame = ttk.Frame(preview)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(text_frame, wrap="none")
        text.insert("1.0", report_text)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, side="left")
        yscroll = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        yscroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(preview, orient="horizontal", command=text.xview)
        xscroll.pack(side="bottom", fill="x")
        text.configure(xscrollcommand=xscroll.set)

        # Buttons
        btn_frame = ttk.Frame(preview)
        btn_frame.pack(fill="x", pady=5)
        def print_text():
            import tempfile
            temp_file = tempfile.mktemp(".txt")
            with open(temp_file, "w") as f:
                f.write(report_text)
            os.startfile(temp_file, "print")
        ttk.Button(btn_frame, text="Print", command=print_text).pack(side="left", padx=10)
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
        settings_window.SettingsWindow(self.root)

    # ---------- Stubs ----------
    def _show_export_dialog(self): pass
    def _show_import_dialog(self): pass
    def _show_recycle_bin(self): pass


class NewMemberForm:
    MEMBERSHIP_TYPES = [
        "Probationary", "Associate", "Active", "Life", "Prospective", "Wait List", "Former"
    ]

    def __init__(self, parent, on_save_callback=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Add New Member")
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


if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
