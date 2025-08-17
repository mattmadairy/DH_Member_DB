import tkinter as tk 
from tkinter import ttk, messagebox, filedialog, PhotoImage
import database
import sys
import os
import member_form
import csv
from datetime import datetime


class MemberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dug Hill Rod & Gun Club Membership Database")
        self.root.geometry("1100x600")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        # track recycle bin refresh function
        self.recycle_bin_refresh_fn = None  

        # Load icons (you can replace with actual .png/.gif files)
        self.icons = {}
        try:
            self.icons["add"] = PhotoImage(file=os.path.join(self.base_dir, "icons", "add.png"))
            self.icons["edit"] = PhotoImage(file=os.path.join(self.base_dir, "icons", "edit.png"))
            self.icons["delete"] = PhotoImage(file=os.path.join(self.base_dir, "icons", "delete.png"))
            self.icons["recycle"] = PhotoImage(file=os.path.join(self.base_dir, "icons", "recycle.png"))
            self.icons["export"] = PhotoImage(file=os.path.join(self.base_dir, "icons", "export.png"))
        except Exception:
            # fallback blank images if icons not found
            self.icons = {k: None for k in ["add", "edit", "delete", "recycle", "export"]}

        # Style
        style = ttk.Style(self.root)
        style.theme_use("default")

        style.configure(
            "Custom.Vertical.TScrollbar",
            troughcolor="#f0f0f0",
            background="#d0d0d0",
            bordercolor="#a0a0a0",
            arrowcolor="black"
        )
        style.configure(
            "Custom.Horizontal.TScrollbar",
            troughcolor="#f0f0f0",
            background="#d0d0d0",
            bordercolor="#a0a0a0",
            arrowcolor="black"
        )

        self.member_types = [
            "All",  
            "Probationary", 
            "Associate", 
            "Active", 
            "Life",
            "Prospective", 
            "Wait List", 
            "Former"
        ]

        self.trees = {}
        self.all_members_data = []

        self._build_gui()
        self.load_data()

    def _make_tree_with_scrollbars(self, parent, columns):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            if col == "ID":
                tree.column(col, width=0, stretch=False)
                tree.heading(col, text="", anchor="center")
            else:
                tree.heading(col, text=col,
                             command=lambda _col=col, _tree=tree: self._sort_treeview(_tree, _col, False))
                tree.column(col, width=120, anchor="center")

        yscroll = ttk.Scrollbar(container, orient="vertical", style="Custom.Vertical.TScrollbar")
        xscroll = ttk.Scrollbar(parent, orient="horizontal", style="Custom.Horizontal.TScrollbar")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.pack(side="bottom", fill="x")

        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.config(command=tree.yview)
        xscroll.config(command=tree.xview)

        tree.grid(row=0, column=0, sticky="nsew")
        return tree

    def _build_gui(self):
        # Toolbar
        toolbar = tk.Frame(self.root)
        toolbar.pack(side="top", fill="x")

        # Search bar + buttons in one line
        search_frame = tk.Frame(toolbar)
        search_frame.pack(fill="x", padx=5, pady=3)

        tk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        search_entry.pack(side="left", padx=5)
        search_entry.bind("<KeyRelease>", self._on_search)

        # Buttons aligned right (reversed order with icons)
        ttk.Button(search_frame, text="Export ⬇️", command=self._show_export_dialog).pack(side="right", padx=2)
        ttk.Button(search_frame, text="🗑️ Recycle Bin", command=self._show_recycle_bin).pack(side="right", padx=2)
        ttk.Button(search_frame, text="❌ Delete Selected", command=self.delete_selected).pack(side="right", padx=2)
        ttk.Button(search_frame, text="✏️ Edit Selected", command=self.edit_selected).pack(side="right", padx=2)
        ttk.Button(search_frame, text="➕ Add Member", command=self.add_member).pack(side="right", padx=2)

        # Notebook tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)

        columns = (
            "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
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


    def _sort_treeview(self, tree, col, reverse):
        items = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            if col == "Badge Number":
                items.sort(key=lambda t: int(t[0]) if t[0].isdigit() else float("inf"), reverse=reverse)
            else:
                items.sort(key=lambda t: t[0].lower() if isinstance(t[0], str) else t[0], reverse=reverse)
        except Exception:
            items.sort(reverse=reverse)

        for index, (val, k) in enumerate(items):
            tree.move(k, "", index)
        tree.heading(col, command=lambda: self._sort_treeview(tree, col, not reverse))

    def load_data(self):
        # Clear existing
        for mtype in self.member_types:
            for row in self.trees[mtype].get_children():
                self.trees[mtype].delete(row)

        self.all_members_data = []
        members = database.get_all_members()
        for m in members:
            data = tuple(str(x or "") for x in (
                m[0],  # ID
                m[1],  # Badge Number
                m[2],  # Membership Type
                m[3],  # First Name
                m[4],  # Last Name
                m[5],  # DOB
                m[6],  # Email
                m[13], # Email 2
                m[7],  # Phone
                m[8],  # Address
                m[9],  # City
                m[10], # State
                m[11], # Zip
                m[12], # Join Date
                m[14], # Sponsor
                m[15], # Card Internal
                m[16], # Card External
            ))
            self.all_members_data.append(data)
            self.trees["All"].insert("", "end", values=data)
            if m[2] in self.trees:
                self.trees[m[2]].insert("", "end", values=data)

    def _on_search(self, event=None):
        query = self.search_var.get().lower()
        for mtype in self.member_types:
            tree = self.trees[mtype]
            tree.delete(*tree.get_children())

            if query:
                filtered = [row for row in self.all_members_data if any(query in str(val).lower() for val in row)]
            else:
                filtered = self.all_members_data

            for data in filtered:
                if mtype == "All" or data[2] == mtype:
                    tree.insert("", "end", values=data)

    def _show_export_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Members")
        dialog.geometry("300x300")

        tk.Label(dialog, text="Select Membership Types:").pack(anchor="w", padx=10, pady=5)

        vars = {}
        for mtype in self.member_types:
            var = tk.BooleanVar(value=(mtype == "All"))
            chk = tk.Checkbutton(dialog, text=mtype, variable=var)
            chk.pack(anchor="w", padx=15)
            vars[mtype] = var

        def do_export():
            selected_types = [mtype for mtype, var in vars.items() if var.get()]
            if not selected_types:
                messagebox.showwarning("No Selection", "Please select at least one membership type.")
                return

            now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"members_{'_'.join(selected_types)}_{now_str}.csv"
            filepath = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=filename,
                                                    filetypes=[("CSV files", "*.csv")])
            if not filepath:
                return

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                headers = (
                    "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
                    "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
                    "Address", "City", "State", "Zip Code", "Join Date", "Sponsor",
                    "Card/Fob Internal Number", "Card/Fob External Number"
                )
                writer.writerow(headers)

                for row in self.all_members_data:
                    if "All" in selected_types or row[2] in selected_types:
                        writer.writerow(row)

            messagebox.showinfo("Export Complete", f"Data exported to {filepath}")
            dialog.destroy()

        ttk.Button(dialog, text="Export", command=do_export).pack(pady=10)

    def _show_recycle_bin(self):
        win = tk.Toplevel(self.root)
        win.title("Recycle Bin")
        win.geometry("800x400")

        cols = (
            "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
            "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
            "Address", "City", "State", "Zip Code", "Join Date", "Sponsor",
            "Card/Fob Internal Number", "Card/Fob External Number", "Deleted At",
        )

        tree = self._make_tree_with_scrollbars(win, cols)

        def refresh_recycle_bin():
            for row in tree.get_children():
                tree.delete(row)
            deleted_members = database.get_deleted_members()
            for m in deleted_members:
                data = tuple(str(x or "") for x in (
                    m[0], m[1], m[2], m[3], m[4], m[5],
                    m[6], m[13], m[7], m[8], m[9], m[10], m[11],
                    m[12], m[14], m[15], m[16], m[17],
                ))
                tree.insert("", "end", values=data)

        refresh_recycle_bin()
        self.recycle_bin_refresh_fn = refresh_recycle_bin  

        ttk.Button(win, text="Restore Selected", command=lambda: self.restore_selected(tree, refresh_recycle_bin)).pack(pady=5)
        ttk.Button(win, text="Delete Permanently", command=lambda: self.permanent_delete_selected(tree, refresh_recycle_bin)).pack(pady=5)
        tree.bind("<Double-1>", lambda event, _tree=tree: self._on_double_click_deleted(event, _tree, refresh_recycle_bin))

        def on_close():
            self.recycle_bin_refresh_fn = None
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_close)

    def add_member(self):
        form = member_form.MemberForm(self.root)
        self.root.wait_window(form.top)
        self.load_data()

    def edit_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to edit.")
            return
        member_id = tree.item(selected[0])["values"][0]
        form = member_form.MemberForm(self.root, member_id)
        self.root.wait_window(form.top)
        self.load_data()

    def delete_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select one or more members to delete.")
            return
        if not messagebox.askyesno("Confirm", "Are you sure you want to delete selected members?"):
            return

        for sel in selected:
            member_id = tree.item(sel)["values"][0]
            database.soft_delete_member_by_id(member_id)

        self.load_data()
        if self.recycle_bin_refresh_fn:  
            self.recycle_bin_refresh_fn()

    def restore_selected(self, tree, refresh_recycle_bin):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to restore.")
            return
        for sel in selected:
            member_id = tree.item(sel)["values"][0]
            database.restore_member(member_id)
        self.load_data()
        refresh_recycle_bin()

    def permanent_delete_selected(self, tree, refresh_recycle_bin):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to delete permanently.")
            return
        if not messagebox.askyesno("Permanent Delete", "This cannot be undone. Delete permanently?"):
            return
        for sel in selected:
            member_id = tree.item(sel)["values"][0]
            database.permanent_delete_member(member_id)
        refresh_recycle_bin()

    def _on_tree_double_click(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected:
            return
        member_id = tree.item(selected[0])["values"][0]
        form = member_form.MemberForm(self.root, member_id)
        self.root.wait_window(form.top)
        self.load_data()

    def _on_double_click_deleted(self, event, tree, refresh_recycle_bin):
        selected = tree.selection()
        if not selected:
            return
        member_id = tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Restore Member", "Do you want to restore this member?"):
            database.restore_member(member_id)
            self.load_data()
            refresh_recycle_bin()


if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
