import tkinter as tk
from tkinter import ttk, messagebox
import database
import sys


class MemberForm:
    def __init__(self, master, member_id=None):
        self.master = master
        self.member_id = member_id

        self.top = tk.Toplevel(master)
        self.top.title("Member Form")
        self.top.geometry("600x700")
        self.top.grab_set()

        # --- Fields dictionary ---
        self.entries = {}

        # --- Form layout ---
        form_frame = tk.Frame(self.top)
        form_frame.pack(fill="both", expand=True, padx=10, pady=10)

        labels = [
            "Badge Number", "Membership Type", "First Name", "Last Name",
            "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
            "Address", "City", "State", "Zip Code", "Join Date", "Sponsor",
            "Card/Fob Internal Number", "Card/Fob External Number"
        ]

        for i, label in enumerate(labels):
            tk.Label(form_frame, text=label).grid(row=i, column=0, sticky="w", pady=3)

            if label in ("Address",):  # multi-line fields
                txt = tk.Text(form_frame, height=3, width=30)
                txt.grid(row=i, column=1, pady=3, sticky="ew")
                self.entries[label] = txt
            else:
                entry = ttk.Entry(form_frame, width=30)
                entry.grid(row=i, column=1, pady=3, sticky="ew")
                self.entries[label] = entry

        # Buttons
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(fill="x", pady=10)

        self.save_button = ttk.Button(btn_frame, text="Save", command=self._save)
        self.save_button.pack(side="right", padx=5)

        self.cancel_button = ttk.Button(btn_frame, text="Cancel", command=self.top.destroy)
        self.cancel_button.pack(side="right", padx=5)

        # --- Keyboard bindings ---
        self.top.bind("<Return>", lambda event: self._save())
        self.top.bind("<Escape>", lambda event: self.top.destroy())

        # Allow Ctrl+Enter newlines in Text widgets
        def allow_newline(event):
            event.widget.insert("insert", "\n")
            return "break"

        for widget in self.entries.values():
            if isinstance(widget, tk.Text):
                widget.bind("<Control-Return>", allow_newline)

        # Load existing data if editing
        if self.member_id:
            self._load_data()

    def _load_data(self):
        member = database.get_member_by_id(self.member_id)
        if not member:
            messagebox.showerror("Error", "Member not found")
            self.top.destroy()
            return

        fields = [
            member[1], member[2], member[3], member[4], member[5],
            member[6], member[13], member[7], member[8], member[9],
            member[10], member[11], member[12], member[14], member[15],
            member[16]
        ]

        for key, val in zip(self.entries.keys(), fields):
            widget = self.entries[key]
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
                widget.insert("1.0", val if val else "")
            else:
                widget.delete(0, tk.END)
                widget.insert(0, val if val else "")

    def _save(self):
        values = []
        for key, widget in self.entries.items():
            if isinstance(widget, tk.Text):
                val = widget.get("1.0", "end-1c").strip()
            else:
                val = widget.get().strip()
            values.append(val if val else None)  # <-- allow blank fields

        try:
            if self.member_id:
                database.update_member(self.member_id, *values)
            else:
                database.add_member(*values)

            messagebox.showinfo("Success", "Member saved successfully!")
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save member: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    member_id = sys.argv[1] if len(sys.argv) > 1 else None
    MemberForm(root, member_id)
    root.mainloop()
