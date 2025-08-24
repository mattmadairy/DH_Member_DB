import tkinter as tk
from tkinter import ttk, messagebox
import os
import database
import member_form
import settings_window
from reports_window import ReportsWindow

class MemberApp:
    # Update TREE_COLUMNS to include Email Address 2
    TREE_COLUMNS = (
        "Badge", "Membership Type", "First Name", "Last Name",
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

        members_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Members", menu=members_menu)
        members_menu.add_command(label="Add Member", command=self.add_member)

        menubar.add_command(label="Reports", command=lambda: ReportsWindow(self.root))
        menubar.add_command(label="Recycle Bin", command=self._show_recycle_bin)
        menubar.add_command(label="Settings", command=self.open_settings)

        # ----- Notebook -----
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        self._build_member_tabs()
        self.load_data()

    # ---------- Member Tabs ----------
    def _build_member_tabs(self):
        """Build Treeview tabs for each member type, using only TREE_COLUMNS."""
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

        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        xscroll.pack(side="bottom", fill="x")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        return tree

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

    def _open_member_form(self, member_id=None):
        return member_form.MemberForm(
            self.root,
            member_id,
            on_save_callback=lambda mid, mtype=None: self.load_data()
        )

    # ---------- Load Members ----------
    def load_data(self):
        """Load members from database and populate Treeviews with mapped columns."""
        for tree in self.trees.values():
            tree.delete(*tree.get_children())

        try:
            members = database.get_all_members()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load members: {e}")
            return

        for m in members:
            # Map full row from DB to TREE_COLUMNS
            tree_row = [
                m[1],  # Badge
                m[2],  # Membership Type
                m[3],  # First Name
                m[4],  # Last Name
                m[6],  # Email Address
                m[13], # Email Address 2
                m[7],  # Phone Number
            ]
            # Insert into "All" tab
            self.trees["All"].insert("", "end", iid=str(m[0]), values=tree_row)
            # Insert into specific membership type tab
            mt_tree = self.trees.get(m[2])
            if mt_tree:
                mt_tree.insert("", "end", iid=str(m[0]), values=tree_row)

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
        rows = [tree.item(i, "values") for i in items]
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

    # ---------- Stubs ----------
    def _show_export_dialog(self): pass
    def _show_import_dialog(self): pass
    def _show_recycle_bin(self): pass


if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
