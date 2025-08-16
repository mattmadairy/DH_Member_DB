import tkinter as tk 
from tkinter import ttk, messagebox
import database
import sys
import os
import member_form


class MemberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dug Hill Rod & Gun Club Membership Database")
        self.root.geometry("1100x600")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

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

        self.member_types = ["All", "Probationary", "Associate", "Active", "Life", "Former"]
        self.trees = {}

        self._build_gui()
        self.load_data()

    def _make_tree_with_scrollbars(self, parent, columns):
        container = ttk.Frame(parent)
        container.pack(fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        tree = ttk.Treeview(container, columns=columns, show="headings")
        for col in columns:
            if col == "ID":
                # Hide ID column completely
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

        ttk.Button(toolbar, text="Add Member", command=self.add_member).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=2, pady=2)
        ttk.Button(toolbar, text="Recycle Bin", command=self._show_recycle_bin).pack(side="left", padx=2, pady=2)

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
            items.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            items.sort(reverse=reverse)

        for index, (val, k) in enumerate(items):
            tree.move(k, "", index)
        tree.heading(col, command=lambda: self._sort_treeview(tree, col, not reverse))

    def load_data(self):
        for mtype in self.member_types:
            for row in self.trees[mtype].get_children():
                self.trees[mtype].delete(row)

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
            self.trees["All"].insert("", "end", values=data)
            if m[2] in self.trees:
                self.trees[m[2]].insert("", "end", values=data)

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

        deleted_members = database.get_deleted_members()
        for m in deleted_members:
            data = tuple(str(x or "") for x in (
                m[0], m[1], m[2], m[3], m[4], m[5],
                m[6], m[13], m[7], m[8], m[9], m[10], m[11],
                m[12], m[14], m[15], m[16], m[17],
            ))
            tree.insert("", "end", values=data)

        ttk.Button(win, text="Restore Selected", command=lambda: self.restore_selected(tree)).pack(pady=5)
        ttk.Button(win, text="Delete Permanently", command=lambda: self.permanent_delete_selected(tree)).pack(pady=5)
        tree.bind("<Double-1>", lambda event, _tree=tree: self._on_double_click_deleted(event, _tree))

    def add_member(self):
        member_form.MemberForm(self.root)
        self.root.after(500, self.load_data)

    def edit_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to edit.")
            return
        member_id = tree.item(selected[0])["values"][0]
        member_form.MemberForm(self.root, member_id)
        self.root.after(500, self.load_data)

    def delete_selected(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to delete.")
            return
        member_id = tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Confirm", "Are you sure you want to delete this member?"):
            database.soft_delete_member_by_badge(member_id)
            self.load_data()

    def restore_selected(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to restore.")
            return
        member_id = tree.item(selected[0])["values"][0]
        database.restore_member(member_id)
        self.load_data()
        tree.delete(selected[0])

    def permanent_delete_selected(self, tree):
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to delete permanently.")
            return
        member_id = tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Permanent Delete", "This cannot be undone. Delete permanently?"):
            database.permanent_delete_member(member_id)
            tree.delete(selected[0])

    def _on_tree_double_click(self, event):
        tree = event.widget
        selected = tree.selection()
        if not selected:
            return
        member_id = tree.item(selected[0])["values"][0]
        member_form.MemberForm(self.root, member_id)
        self.root.after(500, self.load_data)

    def _on_double_click_deleted(self, event, tree):
        selected = tree.selection()
        if not selected:
            return
        member_id = tree.item(selected[0])["values"][0]
        if messagebox.askyesno("Restore Member", "Do you want to restore this member?"):
            database.restore_member(member_id)
            self.load_data()
            tree.delete(selected[0])


if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
