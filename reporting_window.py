import tkinter as tk
from tkinter import ttk, messagebox
import database
from datetime import datetime


class ReportingWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Dues Reports")
        self.geometry("800x500")

        # Year selector
        year_frame = tk.Frame(self)
        year_frame.pack(pady=10)

        tk.Label(year_frame, text="Select Year:").pack(side=tk.LEFT, padx=5)

        current_year = datetime.now().year
        self.year_var = tk.StringVar(value=str(current_year))
        year_spin = tk.Spinbox(
            year_frame, from_=2000, to=2100, textvariable=self.year_var, width=6
        )
        year_spin.pack(side=tk.LEFT, padx=5)

        tk.Button(year_frame, text="Payments", command=self.show_payments).pack(
            side=tk.LEFT, padx=10
        )
        tk.Button(year_frame, text="Outstanding", command=self.show_outstanding).pack(
            side=tk.LEFT, padx=10
        )

        # Results tree
        self.tree = ttk.Treeview(self, columns=(
            "Name", "Type", "Paid", "Expected", "Outstanding"
        ), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Type", text="Membership Type")
        self.tree.heading("Paid", text="Paid")
        self.tree.heading("Expected", text="Expected")
        self.tree.heading("Outstanding", text="Outstanding")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Resize column widths
        self.tree.column("Name", width=200)
        self.tree.column("Type", width=150)
        self.tree.column("Paid", width=100, anchor="e")
        self.tree.column("Expected", width=100, anchor="e")
        self.tree.column("Outstanding", width=120, anchor="e")

    def show_payments(self):
        """Display total payments by year."""
        year = self.year_var.get()
        try:
            rows = database.get_payments_by_year(year)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch report: {e}")
            return

        self.clear_tree()
        for _, first, last, mtype, paid, expected in rows:
            name = f"{last}, {first}"
            self.tree.insert(
                "", tk.END, values=(name, mtype, f"${paid:.2f}", f"${expected:.2f}", "")
            )

    def show_outstanding(self):
        """Display outstanding dues by year."""
        year = self.year_var.get()
        try:
            rows = database.get_outstanding_dues(year)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch report: {e}")
            return

        self.clear_tree()
        for _, first, last, mtype, paid, expected, outstanding in rows:
            name = f"{last}, {first}"
            self.tree.insert(
                "", tk.END,
                values=(
                    name,
                    mtype,
                    f"${paid:.2f}",
                    f"${expected:.2f}",
                    f"${outstanding:.2f}"
                )
            )

    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
