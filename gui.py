import tkinter as tk
from tkinter import ttk, messagebox
import database
import subprocess

class MemberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dug Hill Rod & Gun Club Membership Database")
        self.root.geometry("1100x600")

        self.member_types = ["All", "Probationary", "Associate", "Active", "Life", "Former"]

        # Notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.trees = {}

        columns = (
            "Badge Number",
            "Membership Type",
            "First Name",
            "Last Name",
            "Date of Birth",
            "Email Address",
            "Email Address 2",
            "Phone Number",
            "Address",
            "City",
            "State",
            "Zip Code",
            "Join Date",
            "Sponsor",
            "Card/Fob Internal Number",
            "Card/Fob External Number"
        )

        for mtype in self.member_types:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=mtype)

            tree = ttk.Treeview(frame, columns=columns, show="headings")
            for col in columns:
                tree.heading(col, text=col, command=lambda _col=col, _tree=tree: self._sort_treeview(_tree, _col, False))
                tree.column(col, width=120)

            tree.pack(side="top", fill="both", expand=True)

            yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            xscroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
            yscroll.pack(side="right", fill="y")
            xscroll.pack(side="bottom", fill="x")

            tree.bind("<Double-1>", lambda event, _tree=tree: self._on_double_click(event, _tree))

            self.trees[mtype] = tree

        self.notebook.select(0)

        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Add Member", command=self._add_member).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Edit Member", command=self._edit_member).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Member", command=self._delete_member).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Recycle Bin", command=self._show_recycle_bin).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self._refresh_members).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Export Data", command=self._export_data).pack(side="left", padx=5)

        self._refresh_members()

    def _sort_treeview(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            tree.move(k, "", index)
        tree.heading(col, command=lambda: self._sort_treeview(tree, col, not reverse))

    def _refresh_members(self):
        members = database.get_all_members()
        for mtype, tree in self.trees.items():
            for row in tree.get_children():
                tree.delete(row)
        for m in members:
            data = (
                m[1],   # Badge Number
                m[2],   # Membership Type
                m[3],   # First Name
                m[4],   # Last Name
                m[5],   # DOB
                m[6],   # Email 1
                m[13],  # Email 2
                m[7],   # Phone
                m[8],   # Address
                m[9],   # City
                m[10],  # State
                m[11],  # Zip
                m[12],  # Join Date
                m[14],  # Sponsor
                m[15],  # Card/Fob Internal
                m[16],  # Card/Fob External
            )
            for mtype, tree in self.trees.items():
                if mtype == "All" or m[2].lower() == mtype.lower():
                    tree.insert("", "end", values=data)

    def _on_double_click(self, event, tree):
        item = tree.identify_row(event.y)
        if item:
            member = tree.item(item, "values")
            all_members = database.get_all_members()
            badge_number = member[0]
            member_id = next((m[0] for m in all_members if m[1] == badge_number), None)
            if member_id:
                self._open_member_form(member_id)

    def _add_member(self):
        self._open_member_form()

    def _edit_member(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            return
        member = tree.item(selected[0], "values")
        all_members = database.get_all_members()
        badge_number = member[0]
        member_id = next((m[0] for m in all_members if m[1] == badge_number), None)
        if member_id:
            self._open_member_form(member_id)

    def _delete_member(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            return
        member = tree.item(selected[0], "values")
        badge_number = member[0]
        database.soft_delete_member_by_badge(badge_number)
        self._refresh_members()

    def _show_recycle_bin(self):
        win = tk.Toplevel(self.root)
        win.title("Recycle Bin")
        cols = (
            "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
            "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
            "Address", "City", "State", "Zip Code", "Join Date", "Sponsor",
            "Card/Fob Internal Number", "Card/Fob External Number", "Deleted At",
        )
        tree = ttk.Treeview(win, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col, command=lambda _col=col, _tree=tree: self._sort_treeview(_tree, _col, False))
            tree.column(col, width=120)
        tree.pack(side="top", fill="both", expand=True)
        yscroll = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        xscroll = ttk.Scrollbar(win, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        yscroll.pack(side="right", fill="y")
        xscroll.pack(side="bottom", fill="x")

        deleted_members = database.get_deleted_members()
        for m in deleted_members:
            data = (
                m[0], m[1], m[2], m[3], m[4], m[5],
                m[6], m[13], m[7], m[8], m[9], m[10], m[11],
                m[12], m[14], m[15], m[16], m[17],
            )
            tree.insert("", "end", values=data)

        ttk.Button(win, text="Restore Selected", command=lambda: self.restore_selected(tree)).pack(pady=5)
        tree.bind("<Double-1>", lambda event, _tree=tree: self._on_double_click_deleted(event, _tree))

    def _on_double_click_deleted(self, event, tree):
        item = tree.identify_row(event.y)
        if item:
            member = tree.item(item, "values")
            member_id = member[0]
            self._open_member_form(member_id)

    def restore_selected(self, tree):
        selected = tree.selection()
        if not selected:
            return
        member = tree.item(selected[0], "values")
        badge_number = member[1]
        database.restore_member_by_badge(badge_number)
        tree.delete(selected[0])
        self._refresh_members()

    def _open_member_form(self, member_id=None):
        win = tk.Toplevel(self.root)
        win.title("Member Add/Edit Form")

        labels = [
            "Badge Number", "Membership Type", "First Name", "Last Name",
            "Date of Birth (MM/DD/YYYY)", "Email Address", "Email Address 2",
            "Phone Number", "Address", "City", "State", "Zip Code",
            "Join Date (MM/DD/YYYY)", "Sponsor", "Card/Fob Internal Number",
            "Card/Fob External Number"
        ]
        inputs = {}
        for i, label in enumerate(labels):
            ttk.Label(win, text=label).grid(row=i, column=0, sticky="w", pady=2)
            if label == "Membership Type":
                combo = ttk.Combobox(
                    win,
                    values=["Probationary", "Associate", "Active", "Life", "Former"],
                    state="readonly",
                )
                combo.grid(row=i, column=1, pady=2, sticky="ew")
                inputs[label] = combo
            else:
                entry = ttk.Entry(win)
                entry.grid(row=i, column=1, pady=2, sticky="ew")
                inputs[label] = entry

        if member_id:
            member = database.get_member_by_id(member_id)
            if member:
                mapping = {
                    "Badge Number": member[1],
                    "Membership Type": member[2],
                    "First Name": member[3],
                    "Last Name": member[4],
                    "Date of Birth (MM/DD/YYYY)": member[5],
                    "Email Address": member[6],
                    "Email Address 2": member[13],
                    "Phone Number": member[7],
                    "Address": member[8],
                    "City": member[9],
                    "State": member[10],
                    "Zip Code": member[11],
                    "Join Date (MM/DD/YYYY)": member[12],
                    "Sponsor": member[14],
                    "Card/Fob Internal Number": member[15],
                    "Card/Fob External Number": member[16],
                }
                for key, widget in inputs.items():
                    val = mapping.get(key, "")
                    if key == "Membership Type":
                        widget.set(val.capitalize() if val else "")
                    else:
                        widget.delete(0, tk.END)
                        if val is not None:
                            widget.insert(0, val)

        btns = ttk.Frame(win)
        btns.grid(row=len(labels), columnspan=2, pady=10)
        ttk.Button(btns, text="Save", command=lambda: self._save_form(win, inputs, member_id)).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left", padx=4)
        win.bind('<Return>', lambda event: self._save_form(win, inputs, member_id))

    def _save_form(self, win, inputs, member_id=None):
        data = [widget.get() for widget in inputs.values()]
        if member_id:
            database.update_member(member_id, *data)
        else:
            database.add_member(*data)
        win.destroy()
        self._refresh_members()

    def _export_data(self):
        export_win = tk.Toplevel(self.root)
        export_win.title("Export Members")
        export_win.geometry("300x300")

        selected_types = {mtype: tk.BooleanVar(value=(mtype == "All")) for mtype in self.member_types}

        def on_check_change(changed_type):
            if changed_type == "All":
                if selected_types["All"].get():
                    for m in self.member_types:
                        if m != "All":
                            selected_types[m].set(False)
            else:
                if selected_types[changed_type].get():
                    selected_types["All"].set(False)
                else:
                    if not any(selected_types[m].get() for m in self.member_types if m != "All"):
                        selected_types["All"].set(True)

        for mtype in self.member_types:
            cb = ttk.Checkbutton(
                export_win,
                text=mtype,
                variable=selected_types[mtype],
                command=lambda m=mtype: on_check_change(m)
            )
            cb.pack(anchor="w", pady=2)

        def export_selected():
            chosen_types = [m for m, var in selected_types.items() if var.get()]
            try:
                filepath = database.export_members_to_csv(chosen_types)
                messagebox.showinfo("Export Successful", f"Data exported to:\n{filepath}")
                subprocess.Popen(f'explorer /select,"{filepath}"')
                export_win.destroy()
            except Exception as e:
                messagebox.showerror("Export Failed", str(e))

        ttk.Button(export_win, text="Export", command=export_selected).pack(pady=10)
        ttk.Button(export_win, text="Cancel", command=export_win.destroy).pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()
