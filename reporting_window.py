import tkinter as tk
from tkinter import ttk
import database

from work_hours_report import WorkHoursReportFrame
from attendance_report import AttendanceReport
from dues_report import DuesReportFrame


class ReportingWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Reporting")
        self.geometry("700x500")

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Tabs
        dues_tab = DuesReportFrame(notebook)
        notebook.add(dues_tab, text="Dues")
        dues_tab.populate_report()

        hours_tab = WorkHoursReportFrame(notebook)
        notebook.add(hours_tab, text="Work Hours")
        hours_tab.populate_report()

        attend_tab = AttendanceReportFrame(notebook)
        notebook.add(attend_tab, text="Attendance")
        attend_tab.populate_report()
