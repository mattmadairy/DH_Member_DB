import tkinter as tk
from tkinter import ttk

class BaseReportWindow(tk.Toplevel):
    """
    Base class for reports. Provides a Treeview, basic layout, and helper functions.
    """

    columns = ()
    column_widths = ()

    def __init__(self, parent, title="Report", geometry=None):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        if geometry:
            self.geometry(geometry)

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings")
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        self._setup_controls()

    def _setup_controls(self):
        """Override in child classes to add year/month selectors or buttons"""
        pass

    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
