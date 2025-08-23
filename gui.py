import tkinter as tk
from tkinter import ttk, messagebox, filedialog, PhotoImage
import os
import csv
import tempfile
import platform
from datetime import datetime

import database
import member_form
import settings_window
from attendance_report import AttendanceReport
from reports_window import ReportsWindow
import work_hours_reporting_window

class MemberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dug Hill Rod & Gun Club Membership Database")
        self.root.geometry("1100x600")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # ----- Menubar -----
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="➕ Add Member", command=self.add_member)
        file_menu.add_command(label="✏️ Edit Selected", command=self.edit_selected)
        file_menu.add_command(label="❌ Delete Selected", command=self.delete_selected)
        file_menu.add_separator()
        file_menu.add_command(label="Import ⬆️", command=self._show_import_dialog)
        file_menu.add_command(label="Export ⬇️", command=self._show_export_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Print Current Tab 🖨", command=self._print_members)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Members menu
        members_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Members", menu=members_menu)
        members_menu.add_command(label="Add Member", command=self.add_member)

        # Reports menu
        #reports_menu = tk.Menu(menubar, tearoff=0)
        #menubar.add_cascade(label="Reports", menu=reports_menu)
        # In gui.py menu command
        menubar.add_command(label="Reports",
                    command=lambda: ReportsWindow(self.root))



        # Recycle Bin
        menubar.add_command(label="Recycle Bin", command=self._show_recycle_bin)

        # Settings menu
        menubar.add_command(label="Settings", command=self.open_settings)

        self.recycle_bin_refresh_fn = None
        self.member_types = ["All", "Probationary", "Associate", "Active", "Life",
                             "Prospective", "Wait List", "Former"]
        self.trees = {}
        self.all_members_data = []

        # ----- Notebook -----
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        # Build main member tabs
        self._build_member_tabs()
        self.load_data()

    # ---------- Member Tabs ----------
    def _build_member_tabs(self):
        columns = (
            "Badge", "Membership Type", "First Name", "Last Name",
            "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
            "Address", "City", "State", "Zip Code", "Join Date", "Sponsor",
            "Card/Fob Internal Number", "Card/Fob External Number",
        )

        for mtype in self.member_types:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=mtype)
            tree = self._make_tree_with_scrollbars(frame, columns)
            tree.bind("<Double-1>", self._on_tree_double_click)
            self.trees[mtype] = tree


    def _make_tree_with_scrollbars(self, parent, columns):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            tree.heading(col, text=col, command=lambda _c=col, _t=tree: self._sort_treeview(_t, _c, False))
            tree.column(col, width=120, anchor="w")

        yscroll = ttk.Scrollbar(container, orient="vertical")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(parent, orient="horizontal")
        xscroll.pack(side="bottom", fill="x")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.config(command=tree.yview)
        xscroll.config(command=tree.xview)
        tree.grid(row=0, column=0, sticky="nsew")
        return tree

    # ---------- Open Report Tabs ----------
    def _open_report_tab(self, report_name):
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text=report_name)
        self.notebook.select(frame)
        if report_name == "Meeting Attendance":
            AttendanceReport(frame).pack(fill="both", expand=True)
        elif report_name == "Work Hours":
            work_hours_reporting_window.WorkHoursReportingWindow(frame).pack(fill="both", expand=True)

    # ---------- Sorting ----------
    def _sort_treeview(self, tree, col, reverse):
        items = [(tree.set(k, col), k) for k in tree.get_children()]
        items.sort(key=lambda t: str(t[0]).lower() if isinstance(t[0], str) else t[0], reverse=reverse)
        for idx, (_, k) in enumerate(items):
            tree.move(k, "", idx)
        tree.heading(col, command=lambda: self._sort_treeview(tree, col, not reverse))

    # ---------- Member Management ----------
    def add_member(self):
        form = self._open_member_form()
        self.root.wait_window(form.top)

    def edit_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to edit.")
            return
        member_id = tree.item(selected[0])["values"][0]
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
            member_id = tree.item(sel)["values"][0]
            database.soft_delete_member_by_id(member_id)
        self.load_data()
        if self.recycle_bin_refresh_fn:
            self.recycle_bin_refresh_fn()

    def _open_member_form(self, member_id=None):
        def on_save_callback(saved_id, saved_type=None):
            self.load_data()
        form = member_form.MemberForm(self.root, member_id, on_save_callback=on_save_callback)
        return form

    # ---------- Load Members ----------
    def load_data(self):
        for tree in self.trees.values():
            tree.delete(*tree.get_children())

        try:
            members = database.get_all_members()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load members: {e}")
            return

        self.all_members_data = []
        for m in members:
            # Here, we skip the ID and insert only the relevant columns in the correct order
            data = [
                str(m[1] or ""),  # Badge
                str(m[2] or ""),  # Membership Type
                str(m[3] or ""),  # First Name
                str(m[4] or ""),  # Last Name
                str(m[5] or ""),  # Date of Birth
                str(m[6] or ""),  # Email Address
                str(m[7] or ""),  # Email Address 2
                str(m[8] or ""),  # Phone Number
                str(m[9] or ""),  # Address
                str(m[10] or ""), # City
                str(m[11] or ""), # State
                str(m[12] or ""), # Zip Code
                str(m[13] or ""), # Join Date
                str(m[14] or ""), # Sponsor
                str(m[15] or ""), # Card/Fob Internal Number
                str(m[16] or ""), # Card/Fob External Number
            ]
            
            # Insert the data in the "All" member tab (or specific membership type tab)
            self.all_members_data.append(data)
            self.trees["All"].insert("", "end", values=data)
            
            # For specific membership type tabs, insert data
            mt_tree = self.trees.get(m[2])  # Using membership type for tree lookup
            if mt_tree:
                mt_tree.insert("", "end", values=data)



    # ---------- Double click ----------
    def _on_tree_double_click(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected:
            return
        member_id = tree.item(selected[0])["values"][0]
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
        rows = [tree.item(i,"values") for i in items]
        report_text = "\n".join(["  ".join(r) for r in rows])
        preview = tk.Toplevel(self.root)
        preview.title(f"Print Preview - {current_tab}")
        text = tk.Text(preview)
        text.insert("1.0", report_text)
        text.configure(state="disabled")
        text.pack(fill="both", expand=True)

    # ---------- Settings ----------
    def open_settings(self):
        settings_window.SettingsWindow(self.root)

    # ---------- Import / Export ----------
    def _show_export_dialog(self):
        pass  # Keep your existing export logic

    def _show_import_dialog(self):
        pass  # Keep your existing import logic

    # ---------- Recycle Bin ----------
    def _show_recycle_bin(self):
        pass  # Keep your existing recycle bin logic


if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
