import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font
import tkinter.font as tkFont
import os, sys,tempfile, webbrowser, platform, subprocess
import database
from datetime import datetime
import csv
import calendar
#import pyperclip
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageTk


DATE_FMT = "%m/%d/%Y"
STATUS_OPTIONS = ["Attended", "Exemption Approved"]
METHOD_OPTIONS = ["Cash", "Check", "Electronic"]

    # Map report class names to MemberForm tabs
REPORT_TAB_MAP = {
    "DuesReport": "dues",
    "Work_HoursReport": "work_hours",
    "AttendanceReport": "attendance",
    "WaiverReport": "membership",
    "CommitteesReport": "membership",
}

# Add this utility function near the top of your code
def center_window(window, width=None, height=None, parent=None):
    """Center a Tkinter window on the screen or relative to parent."""
    window.update_idletasks()
    if width is None:
        width = window.winfo_width()
    if height is None:
        height = window.winfo_height()

    if parent:
        parent.update_idletasks()
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = px + (pw // 2) - (width // 2)
        y = py + (ph // 2) - (height // 2)
    else:
        screen_width = window.winfo_screenwidth()
        screen_height = window.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)

    window.geometry(f"{width}x{height}+{x}+{y}")


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

        # ---- Window geometry ----
        window_width = 1100
        window_height = 600
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2)
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        center_window(self.root, 1100, 600)

        # ---- Base directory ----
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

      

        # ---- Window icon for titlebar (all platforms) ----
        png_icon_path = os.path.join(self.base_dir, "Club_logo_smaller-removebg-preview.png")
        if os.path.exists(png_icon_path):
            try:
                img = Image.open(png_icon_path)
                img = img.resize((32, 32), Image.Resampling.LANCZOS)
                self.tk_icon = ImageTk.PhotoImage(img)
                self.root.iconphoto(True, self.tk_icon)  # Sets window icon (not taskbar)
            except Exception as e:
                print(f"Failed to set window icon: {e}")


        self.recycle_bin_refresh_fn = None
        self.member_types = ["All", "Probationary", "Associate", "Active", "Life",
                             "Prospective", "Wait List", "Former"]
        self.trees = {}


        # ----- Menubar -----
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="⬆️ Import Members", command=self._show_import_dialog)
        file_menu.add_command(label="📃     Import Meeting Data", command=self._add_meeting_records_from_excel)
        file_menu.add_command(label="⬇️ Export Current Tab", command=self._show_export_dialog)
        file_menu.add_command(label="📧     Export Emails (Mail Merge)", command=self._export_emails_for_mail_merge)
        file_menu.add_separator()
        file_menu.add_command(label="🖨  Print/Save Current Tab", command=self._print_members)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        members_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Members", menu=members_menu)
        members_menu.add_command(label="➕  Add Member", command=self.add_member)
        members_menu.add_command(label="✏️  Edit Selected", command=self.edit_selected)
        members_menu.add_command(label="📝  Generate Member Report ", command=self._full_member_report_from_menu)
        members_menu.add_separator()
        members_menu.add_command(label="🗑️ Move to Recycle Bin", command=self.delete_selected)

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
        self.row_menu.add_command(label="Generate Member Report", command=self._full_member_report_from_menu)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="Move to Recycle Bin", command=self._delete_selected_row)

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

        # Canvas for watermark
        canvas = tk.Canvas(container, bg="white")
        canvas.grid(row=0, column=0, sticky="nsew")

        # Load and resize logo
        logo_path = os.path.join(self.base_dir, "Club_logo_smaller-removebg-preview.png")  # adjust path/extension
        logo_image = Image.open(logo_path)

        # Pillow 10+ safe resampling
        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS

        logo_image = logo_image.resize((300, 300), resample)
        self.logo_tk = ImageTk.PhotoImage(logo_image)

        # Draw logo centered
        canvas.create_image(0, 0, image=self.logo_tk, anchor="nw", tags="logo")

        # Treeview on top of canvas
        tree = ttk.Treeview(container, columns=columns, show="headings", selectmode="extended")
        tree.place(relx=0, rely=0, relwidth=1, relheight=1)  # overlay full container

        # Setup columns and headings
        self._sort_column_states = {}
        for col in columns:
            tree.heading(col, text=col, command=lambda c=col, t=tree: self._sort_tree_column(t, c, False))
            tree.column(col, width=120, anchor="w")
            if col == "Badge":
                tree.column(col, width=90, anchor="center")

        # Scrollbars
        yscroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        xscroll.pack(side="bottom", fill="x")
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Keep logo centered on resize
        def resize_watermark(event):
            canvas.coords(
                "logo",
                (canvas.winfo_width() // 2 - logo_image.width // 2,
                canvas.winfo_height() // 2 - logo_image.height // 2)
            )

        container.bind("<Configure>", resize_watermark)

        return tree



    def _sort_tree_column(self, tree, col, reverse):
        """Sort tree contents by column and update header arrows."""
        try:
            # Get all rows and the values in the given column
            data = [(tree.set(k, col), k) for k in tree.get_children("")]
            
            # Try converting values to numbers if possible, otherwise lowercase string
            def try_convert(val):
                try:
                    return float(val)
                except ValueError:
                    return val.lower()
            data.sort(key=lambda t: try_convert(t[0]), reverse=reverse)

            # Rearrange items in sorted order
            for index, (val, k) in enumerate(data):
                tree.move(k, "", index)

            # Reset all headings to plain text
            for c in tree["columns"]:
                tree.heading(c, text=c, command=lambda c=c, t=tree: self._sort_tree_column(t, c, False))

            # Add arrow to the sorted column
            arrow = " ▲" if not reverse else " ▼"
            tree.heading(col, text=col + arrow,
                         command=lambda: self._sort_tree_column(tree, col, not reverse))

        except Exception as e:
            pass
            #messagebox.showerror("Sort Error", f"Failed to sort column {col}: {e}")


    # ---------- Member Management ----------
    def add_member(self):
        form = NewMemberForm(self.root, on_save_callback=self.load_data)
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
            messagebox.showwarning("No selection", "Please select members to move to the Recycle Bin.")
            return

        confirm = messagebox.askyesno("Confirm move to Recycle Bin", f"Are you sure you want to move {len(selected)} member(s) to the Recycle Bin?")
        if confirm:
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
            messagebox.showwarning("No selection", "Please select member(s) to move to the Recycle Bin.")
            return

        confirm = messagebox.askyesno("Confirm Recycle Bin", f"Are you sure you want to move {len(selected)} member(s) to the Recycle Bin?")
        if confirm:
            for member_id in selected:
                database.soft_delete_member_by_id(member_id)
            self.load_data()
            if self.recycle_bin_refresh_fn:
                self.recycle_bin_refresh_fn()


    def _open_member_form(self, member_id, select_tab=None):
        return MemberForm(
            self.root,
            member_id,
            on_save_callback=lambda mid: self.load_data(),  # wrap in lambda
            select_tab=select_tab
        )


    # ---------- Right-click ----------
    def _show_row_menu(self, event):
        tree = event.widget
        row_id = tree.identify_row(event.y)
        if row_id:
            # If the clicked row is not already selected, select it
            if row_id not in tree.selection():
                tree.selection_set(row_id)
            # Otherwise, keep current selection (supports multi-select)
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
        """Wrapper to get selected member from the current tab and call the full report."""
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a member first.")
            return
        member_id = selected[0]  # assuming iid = member_id
        self._full_member_report(member_id)

    

    def _full_member_report(self, member_id, year=None):
        # Ask for year if not provided
        if year is None:
            current_year = datetime.now().year
            years = [str(y) for y in range(current_year, current_year - 30, -1)]

            year_popup = tk.Toplevel(self.root)
            year_popup.title("Select Year")
            center_window(year_popup, 250, 120, self.root)

            tk.Label(year_popup, text="Select Year for Report:").pack(pady=(10,5))
            year_var = tk.StringVar(value=str(current_year))
            year_combobox = ttk.Combobox(year_popup, values=years, textvariable=year_var, state="readonly", width=10)
            year_combobox.pack(pady=5)
            year_combobox.focus_set()

            selected_year = []

            def confirm_year():
                val = year_var.get()
                if val.isdigit():
                    selected_year.append(int(val))
                    year_popup.destroy()
                else:
                    messagebox.showwarning("Invalid Year", "Please select a valid year.")

            ttk.Button(year_popup, text="OK", command=confirm_year).pack(pady=(5,10))
            self.root.wait_window(year_popup)

            if not selected_year:
                return
            year = selected_year[0]

        # Fetch member info
        member = database.get_member_by_id(member_id)
        if not member:
            messagebox.showwarning("Member Not Found", "Could not find member data.")
            return

        # Report header
        org_name = "Dug Hill Rod & Gun Club"
        report_name = f"Full Member Report for {member[3]} {member[4]} ({year})"
        report_text = f"{org_name.center(85)}\n{report_name.center(85)}\n{'='*85}\n\n"


        # ---------- Top Blocks with Indented Lines ----------
        indent = "    "  # 4 spaces for indent
        left_width = 38
        right_width = 38


        # Row 1: Personal | Membership
        left_fields = [("First Name", member[3]), ("Last Name", member[4]), ("DOB", member[5])]
        right_fields = [("Badge", member[1]), ("Type", member[2]), ("Join Date", member[12]),
                        ("Sponsor", member[14]), ("Waiver", member[19])]
        report_text += "Personal".ljust(left_width) + "Membership\n"
        max_lines = max(len(left_fields), len(right_fields))
        for i in range(max_lines):
            left_text = f"{indent}{left_fields[i][0]}: {left_fields[i][1]}" if i < len(left_fields) else ""
            right_text = f"{indent}{right_fields[i][0]}: {right_fields[i][1]}" if i < len(right_fields) else ""
            report_text += f"{left_text.ljust(left_width)}{right_text.ljust(right_width)}\n"
        report_text += "\n"

        # Row 2: Contact | Access
        left_fields = [("Email", member[6]), ("Email 2", member[13]), ("Phone", member[7]), ("Phone 2", member[18])]
        right_fields = [("Card Internal #", member[15]), ("Card External #", member[16])]
        report_text += "Contact".ljust(left_width) + "Access\n"
        max_lines = max(len(left_fields), len(right_fields))
        for i in range(max_lines):
            left_text = f"{indent}{left_fields[i][0]}: {left_fields[i][1]}" if i < len(left_fields) else ""
            right_text = f"{indent}{right_fields[i][0]}: {right_fields[i][1]}" if i < len(right_fields) else ""
            report_text += f"{left_text.ljust(left_width)}{right_text.ljust(right_width)}\n"
        report_text += "\n"


        # Row 3: Address | Roles & Committees
        # Fetch role, term, and committees
        role_record = database.get_member_role(member_id) or {}
        role = role_record.get("position", "")
        term_start = role_record.get("term_start", "")
        term_end = role_record.get("term_end", "")
        term_concat = term_start + "  unitl  " + term_end

        # Committees – only include those the member is on
        committees_record = database.get_member_committees(member_id) or {}

        # Only include committees that are marked as active (non-empty, non-zero)
        selected_committees = [c for c, val in committees_record.items() if c != "committee_id" and str(val) == "1"]
        readable_names = [c.replace("_", " ").title() for c in selected_committees]

        # Build right_fields: Role first, then Term, then active committees vertically
        right_fields = [("Role:", role), ("   Term:", term_concat), ("Committees:", "")]
        for c in readable_names:
            right_fields.append(("  ", c, ""))  # Committee name in left column, blank in value

        # Address fields on the left
        left_fields = [
            ("Address", member[8]),
            ("City", member[9]),
            ("State", member[10]),
            ("Zip", member[11])
        ]

        # Print left and right columns side by side
        report_text += "Address".ljust(left_width) + "Roles & Committees\n"
        max_lines = max(len(left_fields), len(right_fields))
        for i in range(max_lines):
            left_text = f"{indent}{left_fields[i][0]}: {left_fields[i][1]}" if i < len(left_fields) else ""
            right_text = f"{indent}{right_fields[i][0]} {right_fields[i][1]}" if i < len(right_fields) else ""
            report_text += f"{left_text.ljust(left_width)}{right_text.ljust(right_width)}\n"

        report_text += "\n" + "="*85 + "\n"


        # ---------- Dues ----------
        report_text += "\n" + "  Dues History\n"
        dues = database.get_dues_by_member(member_id, year=year)
        if dues:
            report_text += f"{'Date':12}{'Year':6}{'Amount':8}{'Method':10}{'Notes':40}\n"
            report_text += "-"*85 + "\n"
            total_dues = 0.0
            for d in dues:
                payment_date = d[2] or "N/A"
                amt = float(d[4] or 0.0)
                total_dues += amt
                report_text += f"{payment_date:12}{d[3]:6}{amt:<8.2f}{(d[5] or ''):10}{(d[6] or ''):40}\n"
            report_text += "-"*85 + f"\nTotal Dues: ${total_dues:.2f}\n" + "="* 85 + "\n"

        else:
            report_text += "No dues recorded\n"
        report_text += "\n"

        # ---------- Work Hours ----------
        report_text += "  Work Hours\n"
        work_hours = database.get_work_hours_by_member(member_id, year=year)
        if work_hours:
            report_text += f"{'Date':12}{'Hours':6}{'Activity':20}{'Notes':40}\n"
            report_text += "-"*85 + "\n"
            total_hours = 0.0
            for w in work_hours:
                date = w[2] or "N/A"
                hours = float(w[4] or 0.0)
                total_hours += hours
                report_text += f"{date:12}{hours:<6}{(w[3] or ''):20}{(w[5] or ''):40}\n"
            report_text += "-"*85 + f"\nTotal Work Hours: {total_hours}\n" + "="* 85 + "\n"
        else:
            report_text += "No work hours recorded\n"
        report_text += "\n"

        # ---------- Attendance ----------
        report_text += "  Meeting Attendance\n"
        attendance = database.get_meeting_attendance(member_id, year=year)
        if attendance:
            report_text += f"{'Date':12}{'Status':20}{'Notes':40}\n"
            report_text += "-"*85 + "\n"
            total_meetings = 0
            for a in attendance:
                date = a[2] or "N/A"
                report_text += f"{date:12}{(a[3] or ''):20}{(a[4] or ''):40}\n"
                total_meetings += 1
            report_text += "-"*85 + f"\nTotal Meetings Attended: {total_meetings}\n" + "="* 85 + "\n"
        else:
            report_text += "No attendance recorded\n"

        # ---------- End of Report ----------
        generation_dt = "Generated: " + datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        footer = ("--End of Report--".center(85) )
        report_text += "\n"+ footer+"\n" + generation_dt.center(85) 

        # ---------- Display in Preview ----------
        preview = tk.Toplevel(self.root)
        preview.title(f"Full Member Report - {member[3]} {member[4]} ({year})")
        preview.transient()
        preview.focus_set()
        center_window(preview, 850, 600, parent=self.root)

        text_widget = tk.Text(preview, wrap="none", font=("Courier New", 10))
        text_widget.insert("1.0", report_text)
        text_widget.configure(state="disabled")
        text_widget.pack(fill="both", expand=True, side="top")

        # Scrollbars
        yscroll = ttk.Scrollbar(preview, orient="vertical", command=text_widget.yview)
        yscroll.pack(side="right", fill="y")
        text_widget.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(preview, orient="horizontal", command=text_widget.xview)
        xscroll.pack(side="bottom", fill="x")
        text_widget.configure(xscrollcommand=xscroll.set)

        # ---------- Buttons at Bottom ----------
        btn_frame = ttk.Frame(preview)
        btn_frame.pack(fill="x", pady=5)
        
        def save_report_pdf():
            path = filedialog.asksaveasfilename(
                initialfile=f"MemberReport_{member[3]}_{member[4]}_{year}.pdf",
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf")]
            )
            if path:
                try:
                    c = canvas.Canvas(path, pagesize=letter)
                    width, height = letter
                    c.setFont("Courier", 10)
                    y = height - 50
                    for line in report_text.splitlines():
                        c.drawString(50, y, line)
                        y -= 12
                        if y < 50:
                            c.showPage()
                            c.setFont("Courier", 10)
                            y = height - 50
                    c.save()
                except Exception as e:
                    messagebox.showerror("PDF Error", f"Failed to save PDF: {e}")

        def save_report_csv():
            path = filedialog.asksaveasfilename(
                initialfile=f"MemberReport_{member[3]}_{member[4]}_{year}.csv",
                defaultextension=".csv",
                filetypes=[("CSV Files", "*.csv")]
            )
            if path:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    # Write top blocks
                    for section, fields in [("Personal", left_fields), ("Membership", right_fields)]:
                        for field, value in fields:
                            writer.writerow([section, field, value])
                    writer.writerow([])
                    # Dues
                    writer.writerow(["Dues History"])
                    if dues:
                        writer.writerow(["Payment Date", "Year", "Amount", "Method", "Notes"])
                        for d in dues:
                            writer.writerow([d[2], d[3], f"{float(d[4]):.2f}", d[5], d[6]])
                    else:
                        writer.writerow(["No dues recorded"])
                    writer.writerow([])
                    # Work hours
                    writer.writerow(["Work Hours"])
                    if work_hours:
                        writer.writerow(["Date","Hours","Activity","Notes"])
                        for w in work_hours:
                            writer.writerow([w[2], w[4], w[3], w[5]])
                    else:
                        writer.writerow(["No work hours recorded"])
                    writer.writerow([])
                    # Attendance
                    writer.writerow(["Meeting Attendance"])
                    if attendance:
                        writer.writerow(["Date","Status","Notes"])
                        for a in attendance:
                            writer.writerow([a[2], a[3], a[4]])
                    else:
                        writer.writerow(["No attendance recorded"])

        def print_report():
            try:
                # Save PDF to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    path = tmp.name

                c = canvas.Canvas(path, pagesize=letter)
                width, height = letter
                c.setFont("Courier", 10)
                y = height - 50
                for line in report_text.splitlines():
                    c.drawString(50, y, line)
                    y -= 12
                    if y < 50:
                        c.showPage()
                        c.setFont("Courier", 10)
                        y = height - 50
                c.save()

                # Open the PDF in the system default viewer
                os.startfile(path)

            except Exception as e:
                messagebox.showerror("Print Error", f"Failed to open PDF: {e}")



        ttk.Button(btn_frame, text="Print", command=print_report).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Save as PDF", command=save_report_pdf).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Save as CSV", command=save_report_csv).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Close", command=preview.destroy).pack(side="right", padx=10)


    # ---------- Mail Merge Export ----------
    def _export_emails_for_mail_merge(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        items = tree.get_children()
        if not items:
            messagebox.showwarning("Mail Merge Export", "No members to export in this tab.")
            return

        try:
            emails = []
            for iid in items:
                member = database.get_member_by_id(iid)
                if member:
                    primary = member[6] or ""
                    secondary = member[13] or ""
                    if primary.strip():
                        emails.append(primary.strip())
                    if secondary.strip():
                        emails.append(secondary.strip())

            if not emails:
                messagebox.showinfo("Mail Merge Export", "No email addresses found for this tab.")
                return

            # Prompt for CSV save
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            default_filename = f"MailMerge_{current_tab.replace(' ','_')}_{timestamp}.csv"
            path = filedialog.asksaveasfilename(
                title="Export Emails for Mail Merge",
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[("CSV Files", "*.csv")]
            )

            if path:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Email Address"])
                    for e in emails:
                        writer.writerow([e])

            # Copy emails to clipboard using Tkinter after a tiny delay
            def copy_to_clipboard():
                clipboard_text = "\n".join(emails)
                self.root.clipboard_clear()
                self.root.clipboard_append(clipboard_text)
                self.root.update()  # Force update
                #messagebox.showinfo(
                #    "Mail Merge Export",
                #    f"Exported {len(emails)} email addresses."
                #    #f"\nEmails have been copied to the clipboard."
                #)

            # Use `after` to ensure focus is back to main window
            self.root.after(100, copy_to_clipboard)

        except Exception as e:
            messagebox.showerror("Mail Merge Export Error", f"Failed to export emails:\n{e}")



                
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

    def _print_members(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        tree = self.trees[current_tab]
        items = tree.get_children()
        if not items:
            messagebox.showwarning("Print", "No members to print in this view.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = f"Member List - {current_tab}\n"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        generated_text = f"Generated: {generation_dt}"

        # remove Email2 / Email Address 2
        print_columns = [c for c in self.TREE_COLUMNS if c.lower() not in ("email2", "email address 2")]
        headers = [tree.heading(c)["text"] for c in print_columns]

        col_widths = [len(h) for h in headers]
        for idx, col in enumerate(print_columns):
            for item in items:
                value = str(tree.item(item, "values")[self.TREE_COLUMNS.index(col)])
                if len(value) > col_widths[idx]:
                    col_widths[idx] = len(value)

        # build rows with proper justification
        rows = []
        for item in items:
            values = tree.item(item, "values")
            row = []
            for idx, col in enumerate(print_columns):
                value = str(values[self.TREE_COLUMNS.index(col)])
                if col == "Badge":
                    row.append(value.ljust(col_widths[idx]))
                elif "phone" in col.lower():
                    row.append(value.rjust(col_widths[idx]))
                else:
                    row.append(value.ljust(col_widths[idx]))
            rows.append("  ".join(row))

        # pagination
        lines_per_page = 40
        total_pages = (len(rows) - 1) // lines_per_page + 1
        pages = [rows[i:i + lines_per_page] for i in range(0, len(rows), lines_per_page)]

        header_line = "  ".join(
            [h.center(col_widths[idx]) if print_columns[idx] == "Badge" else h.ljust(col_widths[idx])
            for idx, h in enumerate(headers)]
        )
        total_members_text = f"Total Members: {len(items)}".center(len(header_line))

        preview_text = ""
        for current_page, page_lines in enumerate(pages, start=1):
            preview_text += f"{org_name.center(len(header_line))}\n"
            preview_text += f"{report_name.center(len(header_line))}\n"
            preview_text += header_line + "\n"
            preview_text += "-" * len(header_line) + "\n"
            preview_text += "\n".join(page_lines) + "\n\n"
            preview_text += ("=" * len(header_line)) + "\n"
            preview_text += total_members_text + "\n"
            preview_text += f"{generated_text.center(len(header_line))}\n"
            preview_text += f"Page {current_page} of {total_pages}".center(len(header_line)) + "\n"
            preview_text += ("=" * len(header_line)) + "\n\n"

        # Preview window
        preview = tk.Toplevel(self.root)
        preview.title(f"Print Preview - {current_tab}")
        preview.transient()
        preview.focus_set()

        preview.update_idletasks()

        text_width = max(len(line) for line in preview_text.splitlines()) if preview_text else 85
        text_height = min(len(preview_text.splitlines()), 50)
        win_width = min(1200, text_width * 8) + 50
        win_height = min(900, text_height * 18) + 100
        center_window(preview, width=win_width, height=win_height, parent=self.root)

        text_frame = ttk.Frame(preview)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(text_frame, wrap="none", font=("Courier New", 10))
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

        # PDF export helper
        def export_to_pdf(filepath):
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(filepath, pagesize=letter)
            width, height = letter
            c.setFont("Courier", 10)
            y = height - 50
            for line in preview_text.splitlines():
                c.drawString(50, y, line)
                y -= 12
                if y < 50:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - 50
            c.save()

        # Print opens temporary PDF
        def print_text():
            import tempfile, os
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    pdf_path = tmp.name
                export_to_pdf(pdf_path)
                os.startfile(pdf_path)
            except Exception as e:
                messagebox.showerror("Print Error", f"Failed to open PDF: {e}")

        # Save as PDF with auto filename
        def save_as_pdf():
            from tkinter import filedialog
            import os
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"Member_List-{current_tab}-{timestamp}.pdf"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                initialfile=default_name,
                filetypes=[("PDF files", "*.pdf")],
                title="Save Member List as PDF"
            )
            if filepath:
                try:
                    export_to_pdf(filepath)
                    os.startfile(filepath)
                    messagebox.showinfo("Save PDF", f"PDF saved successfully:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save PDF: {e}")

        # Save CSV raw
        def save_as_csv():
            from tkinter import filedialog
            import csv
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"Member_List-{current_tab}-{timestamp}.csv"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=default_name,
                filetypes=[("CSV files", "*.csv")],
                title="Save Member List as CSV"
            )
            if filepath:
                try:
                    with open(filepath, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(headers)
                        for item in items:
                            values = tree.item(item, "values")
                            row = [values[self.TREE_COLUMNS.index(col)] for col in print_columns]
                            writer.writerow(row)
                    messagebox.showinfo("Save CSV", f"CSV saved successfully:\n{filepath}")
                except Exception as e:
                    messagebox.showerror("Save Error", f"Failed to save CSV: {e}")

        ttk.Button(btn_frame, text="Print", command=print_text).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Save as CSV", command=save_as_csv).pack(side="left", padx=10)
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
        SettingsWindow(self.root)


    # ---------- Export Members ----------
    def _show_export_dialog(self):
        current_tab = self.notebook.tab(self.notebook.select(), "text")
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        safe_tab_name = current_tab.replace(" ", "_")
        default_filename = f"Members_{safe_tab_name}_{timestamp}.csv"

        path = filedialog.asksaveasfilename(
            initialfile=default_filename,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Members to CSV"
        )
        if not path:
            return

        try:
            tree = self.trees[current_tab]
            items = tree.get_children()
            if not items:
                messagebox.showwarning("Export", "No members to export in this tab.")
                return

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.FULL_COLUMNS)

                for iid in items:
                    # Fetch full member data from database for each displayed row
                    member = database.get_member_by_id(iid)
                    if member:
                        row_values = [
                            member[1], member[2], member[3], member[4], member[5],
                            member[6], member[13], member[7], member[8], member[9],
                            member[10], member[11], member[12], member[14], member[15],
                            member[16]
                        ]
                        writer.writerow(row_values)

            #messagebox.showinfo("Export Complete",
            #d                    f"Exported {len(items)} members from '{current_tab}' to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export members:\n{e}")
        
        
    def _show_import_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Import Members",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not file_path:
            return

        imported_count = 0
        skipped_count = 0

        try:
            with open(file_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    badge = row.get("Badge", "").strip()
                    if not badge:
                        continue  # skip rows without badge
                    existing_member = database.get_member_by_badge(badge)
                    if existing_member:
                        skipped_count += 1
                        continue

                    # Map CSV columns to database order
                    data = (
                        badge,
                        row.get("Membership Type", "").strip(),
                        row.get("First Name", "").strip(),
                        row.get("Last Name", "").strip(),
                        row.get("Date of Birth", "").strip(),
                        row.get("Email Address", "").strip(),
                        row.get("Phone Number", "").strip(),
                        row.get("Address", "").strip(),
                        row.get("City", "").strip(),
                        row.get("State", "").strip(),
                        row.get("Zip Code", "").strip(),
                        row.get("Join Date", "").strip(),
                        row.get("Email Address 2", "").strip(),
                        row.get("Sponsor", "").strip(),
                        row.get("Card/Fob Internal Number", "").strip(),
                        row.get("Card/Fob External Number", "").strip()
                    )
                    database.add_member(data)
                    imported_count += 1

            messagebox.showinfo(
                "Import Complete",
                f"Imported {imported_count} new members.\nSkipped {skipped_count} duplicates."
            )
            self.load_data()

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import members:\n{e}")

            # ---------- Stubs ----------
            
    def _show_recycle_bin(self):
        RecycleBinWindow(self.root, refresh_main_fn=self.load_data)
    
    def _add_meeting_records_from_excel(self):
        pass


class NewMemberForm:
    MEMBERSHIP_TYPES = [
        "Probationary", "Associate", "Active", "Life", "Honorary", "Prospective", "Wait List", "Former"
    ]

    def __init__(self, parent, on_save_callback=None):
        self.top = tk.Toplevel(parent)
        self.top.title("Add New Member")
        center_window(self.top, 370, 575, parent)  # Center popup
        self.top.transient()
        self.top.focus_set()
        self.on_save_callback = on_save_callback
        

        self.entries = {}
        self.waiver_var = tk.BooleanVar()

        # Bold font for labels
        label_font = tkFont.Font(self.top, family="TkDefaultFont", size=12, weight="bold")

        # Define fields in logical order: badge -> membership -> names -> contact -> other
        fields = [
            "Badge",
            "Membership Type",
            "First Name",
            "Last Name",
            "Date of Birth",
            "Email Address",
            "Email Address 2",
            "Phone Number",
            "Phone Number 2",
            "Address",
            "City",
            "State",
            "Zip Code",
            "Join Date (MM-DD-YYYY)",
            "Sponsor",
            "Card/Fob Internal Number",
            "Card/Fob External Number",
            "Waiver Signed"
        ]

        for idx, field in enumerate(fields):
            tk.Label(self.top, text=field + ":", font=label_font).grid(
                row=idx, column=0, sticky="e", padx=5, pady=2
            )

            if field == "Membership Type":
                cb = ttk.Combobox(self.top, values=self.MEMBERSHIP_TYPES, state="readonly", width=17)
                cb.grid(row=idx, column=1, padx=5, pady=2, sticky="w")
                self.entries[field] = cb
            elif field == "Waiver Signed":
                cb = tk.Checkbutton(self.top, variable=self.waiver_var)
                cb.grid(row=idx, column=1, padx=5, pady=2, sticky="w")
            else:
                entry = tk.Entry(self.top)
                entry.grid(row=idx, column=1, padx=5, pady=2, sticky="w")
                self.entries[field] = entry

        # Save button
        tk.Button(self.top, text="Save", command=self._save_member).grid(
            row=len(fields), column=0, columnspan=1, padx=10, pady=10, sticky="w")
        # Cancel button
        tk.Button(self.top, text="Cancel", command=self.top.destroy).grid(
            row=len(fields), column=1, columnspan=2, pady=10, sticky="e")


    def _save_member(self):
        data = (
            self.entries["Badge"].get().strip(),
            self.entries["Membership Type"].get().strip(),
            self.entries["First Name"].get().strip(),
            self.entries["Last Name"].get().strip(),
            self.entries["Date of Birth"].get().strip(),
            self.entries["Email Address"].get().strip(),
            self.entries["Email Address 2"].get().strip(),
            self.entries["Phone Number"].get().strip(),
            self.entries["Phone Number 2"].get().strip(),
            self.entries["Address"].get().strip(),
            self.entries["City"].get().strip(),
            self.entries["State"].get().strip(),
            self.entries["Zip Code"].get().strip(),
            self.entries["Join Date"].get().strip(),
            self.entries["Sponsor"].get().strip(),
            self.entries["Card/Fob Internal Number"].get().strip(),
            self.entries["Card/Fob External Number"].get().strip(),
            self.waiver_var.get()  # boolean
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


class RecycleBinWindow:
    def __init__(self, parent, refresh_main_fn=None):
        self.parent = parent
        self.refresh_main_fn = refresh_main_fn

        self.top = tk.Toplevel(parent)
        self.top.title("Recycle Bin")
        
        center_window(self.top, 900, 500, parent)  # <-- Center popup relative to parent
        self.top.transient()
        self.top.focus_set()



        # ----- Top button frame -----
        btn_frame = ttk.Frame(self.top)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="✔️ Restore Selected", command=self.restore_selected).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="❌ Delete Selected Permanently", command=self.delete_selected).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="🗑️ Empty Recycle Bin", command=self.empty_recycle_bin).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Close", command=self.top.destroy).pack(side="right", padx=10)

        # ----- Treeview -----
        columns = (
            "Badge", "Last Name", "First Name", "Membership Type",
            "Email Address", "Phone Number"
        )

        self.tree = ttk.Treeview(self.top, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
            if col == "Badge":
                self.tree.column(col, width=90, anchor="center")
        self.tree.pack(fill="both", expand=True, side="left")

        # Scrollbar
        yscroll = ttk.Scrollbar(self.top, orient="vertical", command=self.tree.yview)
        yscroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=yscroll.set)

        # Right-click menu
        self.row_menu = tk.Menu(self.top, tearoff=0)
        self.row_menu.add_command(label="Restore Selected", command=self.restore_selected)
        self.row_menu.add_command(label="Delete Selected Permanently", command=self.delete_selected)
        self.row_menu.add_separator()
        self.row_menu.add_command(label="Empty Recycle Bin", command=self.empty_recycle_bin)
        self.tree.bind("<Button-3>", self._show_row_menu)

        self.load_deleted_members()

    def load_deleted_members(self):
        self.tree.delete(*self.tree.get_children())
        try:
            deleted_members = database.get_deleted_members()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load deleted members:\n{e}", parent=self.top)
            return

        for m in deleted_members:
            row_values = [m[1], m[4], m[3], m[2], m[6], m[7]]  # Badge, Last, First, Membership, Email, Phone
            self.tree.insert("", "end", iid=str(m[0]), values=row_values)

    def restore_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Restore", "Please select member(s) to restore.", parent=self.top)
            return
        confirm = messagebox.askyesno("Restore", f"Restore {len(selected)} member(s)?", parent=self.top)
        if not confirm:
            return
        for member_id in selected:
            try:
                database.restore_member_by_id(member_id)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restore member {member_id}: {e}", parent=self.top)
        self.load_deleted_members()
        if self.refresh_main_fn:
            self.refresh_main_fn()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Delete", "Please select member(s) to delete permanently.", parent=self.top)
            return
        confirm = messagebox.askyesno(
            "Delete",
            f"Permanently delete {len(selected)} member(s)? This cannot be undone.",
            parent=self.top
        )
        if not confirm:
            return
        for member_id in selected:
            try:
                database.permanently_delete_member_by_id(member_id)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete member {member_id}: {e}", parent=self.top)
        self.load_deleted_members()
        if self.refresh_main_fn:
            self.refresh_main_fn()

    def empty_recycle_bin(self):
        confirm = messagebox.askyesno(
            "Empty Recycle Bin",
            "This will permanently delete ALL members in the recycle bin. "
            "This action cannot be undone. Continue?",
            parent=self.top
        )
        if not confirm:
            return
        try:
            for member_id in self.tree.get_children():
                database.permanently_delete_member_by_id(member_id)
            self.load_deleted_members()
            if self.refresh_main_fn:
                self.refresh_main_fn()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to empty recycle bin: {e}", parent=self.top)

    def _show_row_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            if row_id not in self.tree.selection():
                self.tree.selection_set(row_id)
            self.row_menu.post(event.x_root, event.y_root)
        else:
            self.row_menu.unpost()


class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        center_window(self, 400, 320, parent)
        self.transient()
        self.focus_set()
        self.resizable(False, False)

        # Load settings
        self.settings = database.get_all_settings()

        # Container frame to center everything
        container = ttk.Frame(self)
        container.pack(expand=True)

        row = 0
        tk.Label(container, text="Dues Amounts", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, pady=5
        )

        row += 1
        tk.Label(container, text="Probationary:").grid(row=row, column=0, sticky="e", padx=10, pady=2)
        self.prob_var = tk.StringVar(value=self.settings.get("dues_probationary", "150"))
        tk.Entry(container, textvariable=self.prob_var, justify="center", width=15).grid(row=row, column=1, sticky="w", padx=10, pady=2)

        row += 1
        tk.Label(container, text="Associate:").grid(row=row, column=0, sticky="e", padx=10, pady=2)
        self.assoc_var = tk.StringVar(value=self.settings.get("dues_associate", "300"))
        tk.Entry(container, textvariable=self.assoc_var, justify="center", width=15).grid(row=row, column=1, sticky="w", padx=10, pady=2)

        row += 1
        tk.Label(container, text="Active:").grid(row=row, column=0, sticky="e", padx=10, pady=2)
        self.active_var = tk.StringVar(value=self.settings.get("dues_active", "150"))
        tk.Entry(container, textvariable=self.active_var, justify="center", width=15).grid(row=row, column=1, sticky="w", padx=10, pady=2)

        row += 1
        tk.Label(container, text="Life:").grid(row=row, column=0, sticky="e", padx=10, pady=2)
        self.life_var = tk.StringVar(value=self.settings.get("dues_life", "0"))
        tk.Entry(container, textvariable=self.life_var, justify="center", state="disabled", width=15).grid(row=row, column=1, sticky="w", padx=10, pady=2)

        row += 2
        # Heading above entry
        tk.Label(container, text="Default Year:", font=("Arial", 12, "bold")).grid(
            row=row, column=0, columnspan=2, pady=(10, 2)
        )
        row += 1

        current_year = datetime.now().year
        self.year_var = tk.StringVar(value=self.settings.get("default_year", str(current_year)))

        tk.Spinbox(
            container,
            from_=current_year - 20,  # 20 years ago
            to=current_year + 5,      # 5 years in future
            textvariable=self.year_var,
            width=10,
            justify="center"
        ).grid(row=row, column=0, columnspan=2, pady=(0, 5))


        row += 2
        ttk.Button(container, text="Save", command=self.save_settings).grid(row=row, column=0, columnspan=2, pady=15)


    def save_settings(self):
        try:
            database.set_setting("dues_probationary", int(self.prob_var.get()))
            database.set_setting("dues_associate", int(self.assoc_var.get()))
            database.set_setting("dues_active", int(self.active_var.get()))
            database.set_setting("dues_life", 0)  # Life dues fixed/disabled
            database.set_setting("default_year", int(self.year_var.get()))
            messagebox.showinfo("Saved", "Settings have been updated.")
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers for dues and year.")


class DataTab:
    def __init__(self, parent, columns, db_load_func, db_add_func, db_update_func, db_delete_func,
                 entry_fields, row_adapter=None):
        self.parent = parent
        self.columns = columns
        self.db_load_func = db_load_func
        self.db_add_func = db_add_func
        self.db_update_func = db_update_func
        self.db_delete_func = db_delete_func
        self.entry_fields = entry_fields
        self.row_adapter = row_adapter or (lambda r: list(r[2:]))

        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(parent, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120, anchor="w")
        self.tree.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        
        self.member_id = None

    def load_records(self, member_id):
        self.member_id = member_id
        for row in self.tree.get_children():
            self.tree.delete(row)
        records = self.db_load_func(member_id)
        for r in records:
            values = self.row_adapter(r)
            self.tree.insert("", "end", iid=r[0], values=values)

    def edit_record(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))

        popup = tk.Toplevel(self.parent)
        popup.title("Edit Entry")
        editors = []
        for i, field in enumerate(self.entry_fields):
            label = field[0]
            opts = field[2] if len(field) == 3 else {}
            ttk.Label(popup, text=label).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            new_var = tk.StringVar(value=current_values[i])
            if opts.get("widget") == "combobox":
                w = ttk.Combobox(popup, textvariable=new_var, values=opts.get("values", []), state="readonly")
            else:
                w = ttk.Entry(popup, textvariable=new_var)
            w.grid(row=i, column=1, padx=5, pady=3, sticky="w")
            editors.append(new_var)

        def save():
            new_vals = [v.get() for v in editors]
            try:
                self.db_update_func(row_id, *new_vals)
                self.load_records(self.member_id)
                popup.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        ttk.Button(popup, text="Save", command=save).grid(row=len(self.entry_fields), column=0, pady=8)
        ttk.Button(popup, text="Cancel", command=popup.destroy).grid(row=len(self.entry_fields), column=1, pady=8)


class MemberForm(tk.Frame):
    def __init__(self, parent, member_id=None, on_save_callback=None, select_tab=None):
        super().__init__(parent)
        self.top = tk.Toplevel(parent)
        self.top.title("Member Form")
        center_window(self.top, 850, 400, parent)
        self.top.transient(parent)
        self.top.focus_set()

        self.member_id = member_id
        self.on_save_callback = on_save_callback
        self.select_tab = select_tab 

        # ----- Notebook -----
        style = ttk.Style(self.top)
        style.configure("CustomNotebook.TNotebook.Tab", padding=[12, 5], anchor="center")
        self.notebook = ttk.Notebook(self.top, style="CustomNotebook.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # ----- Tabs -----
        self.tab_basic = ttk.Frame(self.notebook)
        self.tab_contact = ttk.Frame(self.notebook)
        self.tab_membership = ttk.Frame(self.notebook)
        self.tab_dues = ttk.Frame(self.notebook)
        self.tab_work_hours = ttk.Frame(self.notebook)
        self.tab_attendance = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_basic, text="Basic Info")
        self.notebook.add(self.tab_contact, text="Contact")
        self.notebook.add(self.tab_membership, text="Membership")
        self.notebook.add(self.tab_dues, text="Dues History")
        self.notebook.add(self.tab_work_hours, text="Work Hours")
        self.notebook.add(self.tab_attendance, text="Meeting Attendance")

        if select_tab:
            tab_mapping = {
                "basic": self.tab_basic,
                "contact": self.tab_contact,
                "membership": self.tab_membership,
                "dues": self.tab_dues,
                "work_hours": self.tab_work_hours,
                "attendance": self.tab_attendance
            }
            if select_tab in tab_mapping:
                self.notebook.select(tab_mapping[select_tab])

        # ----- Variables -----
        self.badge_number_var = tk.StringVar()
        self.membership_type_var = tk.StringVar()
        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.dob_var = tk.StringVar()
        self.email_var = tk.StringVar()
        self.email2_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.phone2_var = tk.StringVar()
        self.address_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.state_var = tk.StringVar()
        self.zip_var = tk.StringVar()
        self.join_date_var = tk.StringVar()
        self.sponsor_var = tk.StringVar()
        self.card_internal_var = tk.StringVar()
        self.card_external_var = tk.StringVar()
        self.waiver_var = tk.StringVar()
        self.role_var = tk.StringVar()
        self.term_var = tk.StringVar()
        self.committees_var = tk.StringVar()  # read-only display in membership tab
        self.notes_var = tk.StringVar()  # for read-only display in membership tab


        self.membership_types = ["Probationary", "Associate", "Active", "Life", "Prospective", "Wait List", "Former"]
        self._display_labels = {}

        # ----- Build read-only tabs -----
        self._build_read_only_tab(self.tab_basic, [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._edit_basic, "basic")

        self._build_read_only_tab(self.tab_contact, [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Phone Number 2", self.phone2_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._edit_contact, "contact")

        self._build_read_only_tab(
            self.tab_membership,
            [
                ("Badge Number", self.badge_number_var),
                ("Membership Type", self.membership_type_var),
                ("Join Date", self.join_date_var),
                ("Sponsor", self.sponsor_var),
                ("Card/Fob Internal Number", self.card_internal_var),
                ("Card/Fob External Number", self.card_external_var),
                ("Waiver Signed", self.waiver_var)
            ],
            self._edit_membership,
            "membership",
            right_fields=[
                ("Role", self.role_var),
                ("Term", self.term_var),
                ("Committees", self.committees_var),
                ("Committee Notes", self.notes_var)  # <- add Notes here
            ]
        )


        # ----- Data tabs -----
        self.dues_tab = DuesTab(self.tab_dues, self.member_id)
        self.work_tab = WorkHoursTab(self.tab_work_hours, self.member_id)
        self.attendance_tab = AttendanceTab(self.tab_attendance, self.member_id)

        if self.member_id:
            self._load_member_data()

        # ----- Window size -----
        self.top.update_idletasks()
        width = max(850, min(self.top.winfo_width(), 1000))
        height = max(300, self.top.winfo_height())
        self.top.geometry(f"{width}x{height}")
        center_window(self.top, width, height)

        # ----- Build read-only tabs -----
    def _build_read_only_tab(self, tab, fields, edit_callback, tab_key, right_fields=None):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_columnconfigure(2, weight=1)
        tab.grid_columnconfigure(3, weight=1)

        self._display_labels[tab_key] = {}
        big_font = font.nametofont("TkDefaultFont").copy()
        big_font.configure(size=12, weight="bold")
        label_font = font.nametofont("TkDefaultFont").copy()
        label_font.configure(size=12)

        max_rows = max(len(fields), len(right_fields) if right_fields else 0)

        # Left column
        for row in range(max_rows):
            if row < len(fields):
                label_text, var = fields[row]
                ttk.Label(tab, text=label_text + ":", font=big_font).grid(
                    row=row, column=0, sticky="w", padx=50, pady=4
                )
                lbl = ttk.Label(tab, text=var.get(), font=label_font)
                lbl.grid(row=row, column=1, sticky="w", padx=0, pady=4)
                self._display_labels[tab_key][label_text] = (lbl, var)
            else:
                ttk.Label(tab, text="").grid(row=row, column=0)
                ttk.Label(tab, text="").grid(row=row, column=1)

            # Right block
            if right_fields and row < len(right_fields):
                label_text, var = right_fields[row]
                ttk.Label(tab, text=label_text + ":", font=big_font).grid(
                    row=row, column=2, sticky="nw", padx=0, pady=4
                )

                # Wrap Notes text nicely
                if label_text == "Committee Notes":
                    lbl = ttk.Label(tab, text=var.get(), font=label_font,
                                    wraplength=300, justify="left")
                else:
                    lbl = ttk.Label(tab, text=var.get(), font=label_font)

                lbl.grid(row=row, column=3, sticky="w", padx=0, pady=4)
                self._display_labels[tab_key][label_text] = (lbl, var)
            elif right_fields:
                ttk.Label(tab, text="").grid(row=row, column=2)
                ttk.Label(tab, text="").grid(row=row, column=3)

        ttk.Button(tab, text="Edit", command=edit_callback).grid(
            row=max_rows,
            column=0, columnspan=4, pady=12
        )


    # ----- Load member data -----
    def _load_member_data(self):
        if not self.member_id:
            return

        m = database.get_member_by_id(self.member_id)
        if not m:
            return

        columns = [
            ("badge_number_var", "badge_number", ""),
            ("membership_type_var", "membership_type", ""),
            ("first_name_var", "first_name", ""),
            ("last_name_var", "last_name", ""),
            ("dob_var", "dob", ""),
            ("email_var", "email", ""),
            ("email2_var", "email2", ""),
            ("phone_var", "phone", ""),
            ("phone2_var", "phone2", ""),
            ("address_var", "address", ""),
            ("city_var", "city", ""),
            ("state_var", "state", ""),
            ("zip_var", "zip", ""),
            ("join_date_var", "join_date", ""),
            ("sponsor_var", "sponsor", ""),
            ("card_internal_var", "card_internal", ""),
            ("card_external_var", "card_external", ""),
            ("waiver_var", "waiver", "No")
        ]

        for var_name, col_name, default in columns:
            getattr(self, var_name).set(m[col_name] if col_name in m.keys() and m[col_name] is not None else default)

        # Role info
        role_record = database.get_member_role(self.member_id)
        if role_record:
            self.role_var.set(role_record["position"])
            start = role_record.get("term_start", "")
            end = role_record.get("term_end", "")

            def fmt(d):
                try:
                    return datetime.strptime(d, "%Y-%m-%d").strftime("%m-%d-%Y")
                except:
                    return d or ""

            start_fmt = fmt(start)
            end_fmt = fmt(end)
            if start_fmt and end_fmt:
                self.term_var.set(f"{start_fmt} until {end_fmt}")
            elif start_fmt:
                self.term_var.set(f"from {start_fmt}")
            elif end_fmt:
                self.term_var.set(f"until {end_fmt}")
            else:
                self.term_var.set("")
        else:
            self.role_var.set("")
            self.term_var.set("")


        # Committees
        committees_record = database.get_member_committees(self.member_id) or {}
        selected_committees = [c for c, val in committees_record.items()
                            if c != "committee_id" and c != "notes" and str(val) == "1"]
        readable_names = [c.replace("_", " ").title() for c in selected_committees]
        self.committees_var.set("\n".join(readable_names))

        # Notes
        self.notes_var.set(committees_record.get("notes", ""))



        # Update labels
        for tab_labels in self._display_labels.values():
            for lbl, var in tab_labels.values():
                lbl.config(text=var.get())

        self.work_tab.load_records(self.member_id)
        self.attendance_tab.load_records(self.member_id)
        self.dues_tab.load_records(self.member_id)

    # ----- Edit callbacks -----
    def _edit_basic(self):
        self._open_edit_popup_generic("Basic Info", [
            ("First Name", self.first_name_var),
            ("Last Name", self.last_name_var),
            ("Date of Birth", self.dob_var)
        ], self._save_basic)


    def _get_term_start(self):
        term_text = self.term_var.get()
        if "until" in term_text:
            return term_text.split("until")[0].replace("from","").strip()
        elif "from" in term_text:
            return term_text.replace("from","").strip()
        return ""

    def _get_term_end(self):
        term_text = self.term_var.get()
        if "until" in term_text:
            return term_text.split("until")[1].strip()
        elif "until" in term_text:
            return term_text.replace("until","").strip()
        return ""



    def _edit_contact(self):
        self._open_edit_popup_generic("Contact", [
            ("Email Address", self.email_var),
            ("Email Address 2", self.email2_var),
            ("Phone Number", self.phone_var),
            ("Phone Number 2", self.phone2_var),
            ("Address", self.address_var),
            ("City", self.city_var),
            ("State", self.state_var),
            ("Zip Code", self.zip_var)
        ], self._save_contact)

    def _edit_membership(self):
        fields = [
            ("Badge Number", self.badge_number_var),
            ("Membership Type", self.membership_type_var),
            ("Join Date", self.join_date_var),
            ("Sponsor", self.sponsor_var),
            ("Card/Fob Internal Number", self.card_internal_var),
            ("Card/Fob External Number", self.card_external_var),
            ("Waiver Signed", self.waiver_var),
            ("Role", self.role_var),
            ("Term Start", tk.StringVar(value=self._get_term_start())),
            ("Term End", tk.StringVar(value=self._get_term_end()))
        ]

        # Fetch member's committee record
        committees_record = database.get_member_committees(self.member_id) or {}

        # Committees checkboxes
        committee_names = [
            "executive_committee", "membership", "trap", "still_target",
            "gun_bingo_social_events", "rifle", "pistol", "archery",
            "building_and_grounds", "hunting"
        ]
        committees_vars = {
            c: tk.IntVar(value=int(committees_record.get(c, 0) or 0))
            for c in committee_names
        }

        # Notes field from committees table
        notes_var = tk.StringVar(value=committees_record.get("notes", ""))

        self._open_edit_popup_generic(
            "Membership",
            fields,
            lambda editors, popup, notes_text: self._save_membership_edit(
                editors, committees_vars, notes_text, popup
            ),
            committees_vars,
            notes_var
        )


        # ----- Generic popup editor -----
    def _open_edit_popup_generic(self, title, fields, save_callback,
                                 committees_vars=None, notes_var=None):
        popup = tk.Toplevel(self.top)
        popup.title(f"Edit {title}")
        popup.transient(self.top)
        popup.focus_set()
        editors = {}

        label_font = tkFont.Font(popup, family="TkDefaultFont", size=10, weight="bold")

        for label_text, var in fields:
            frame = ttk.Frame(popup)
            frame.pack(fill="x", padx=10, pady=5)

            ttk.Label(frame, text=label_text + ":", font=label_font).pack(side="left")

            if label_text == "Membership Type":
                combo = ttk.Combobox(frame, textvariable=var,
                                     values=["Probationary", "Associate", "Active", "Life", "Honorary",
                                             "Waitlist", "Prospective", "Former"],
                                     state="readonly", width=27)
                combo.set(var.get())
                combo.pack(side="right", padx=5)
                editors[label_text] = combo

            elif label_text == "Role":
                combo = ttk.Combobox(frame, textvariable=var,
                                     values=["", "President", "Vice President", "Treasurer", "Secretary", "Trustee"],
                                     state="readonly", width=27)
                combo.set(var.get())
                combo.pack(side="right", padx=5)
                editors[label_text] = combo

            else:
                entry = ttk.Entry(frame, width=30)
                entry.insert(0, var.get())
                entry.pack(side="right", padx=5)
                editors[label_text] = entry

        if committees_vars is not None:
            ttk.Label(popup, text="Committees:", font=label_font).pack(anchor="w", padx=10, pady=(10, 0))
            for c, var in committees_vars.items():
                ttk.Checkbutton(popup, text=c.replace("_", " ").title(), variable=var).pack(anchor="w", padx=20)

        # Notes field
        notes_text = None
        if notes_var is not None:
            ttk.Label(popup, text="Committee Notes:", font=label_font).pack(anchor="w", padx=10, pady=(10, 0))
            notes_text = tk.Text(popup, width=60, height=5, wrap="word")
            notes_text.insert("1.0", notes_var.get())
            notes_text.pack(fill="x", padx=20, pady=5)

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Save",
                   command=lambda: save_callback(editors, popup, notes_text)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=popup.destroy).pack(side="left", padx=5)

        popup.update_idletasks()
        center_window(popup, popup.winfo_reqwidth(), popup.winfo_reqheight(), self.top)


    def _save_basic(self, editors, popup, notes_text=None):
        """Save Basic Info tab edits back to DB."""
        first_name = editors["First Name"].get().strip()
        last_name = editors["Last Name"].get().strip()
        dob = editors["Date of Birth"].get().strip()

        database.update_member_basic(self.member_id, first_name, last_name, dob)
        self._load_member_data()
        popup.destroy()


    def _save_contact(self, editors, popup, notes_text=None):
        """Save Contact Info tab edits back to DB."""
        email  = editors["Email Address"].get().strip()
        email2 = editors["Email Address 2"].get().strip()
        phone  = editors["Phone Number"].get().strip()
        phone2 = editors["Phone Number 2"].get().strip()
        address = editors["Address"].get().strip()
        city    = editors["City"].get().strip()
        state   = editors["State"].get().strip()
        zip_code= editors["Zip Code"].get().strip()

        database.update_member_contact(
            self.member_id, email, email2, phone, phone2,
            address, city, state, zip_code
        )
        self._load_member_data()
        popup.destroy()



        # Update in DB
        database.update_member_contact(
            self.member_id, email, email2, phone, phone2,
            address, city, state, zip_code
        )

        # Refresh UI
        self._load_member_data()
        popup.destroy()



    # ----- Save membership edit -----
    def _save_membership_edit(self, editors, committees_vars, notes_text, popup):
        # ----- Membership info -----
        waiver_str = self.waiver_var.get() if self.waiver_var.get() in ("Yes", "No") else "No"
        database.update_member_membership(
            member_id=self.member_id,
            badge_number=self.badge_number_var.get(),
            membership_type=self.membership_type_var.get(),
            join_date=self.join_date_var.get(),
            sponsor=self.sponsor_var.get(),
            card_internal=self.card_internal_var.get(),
            card_external=self.card_external_var.get(),
            phone2=self.phone2_var.get(),
            waiver=waiver_str
        )

        # ----- Role/Term -----
        term_start = editors["Term Start"].get().strip()
        term_end = editors["Term End"].get().strip()
        database.update_member_role(self.member_id, self.role_var.get(), term_start, term_end)

        # ----- Committees + Notes -----
        committees_data = {k: int(v.get()) for k, v in committees_vars.items()}
        if notes_text is not None:
            committees_data["notes"] = notes_text.get("1.0", "end-1c").strip()

        database.update_member_committees(self.member_id, committees_data)

        # ----- Refresh UI -----
        self._load_member_data()
        if self.on_save_callback:
            self.on_save_callback(self.member_id)
        popup.destroy()


class DuesTab(DataTab):
    def __init__(self, parent, member_id):
        super().__init__(
            parent,
            columns=["Date", "Year", "Amount", "Method", "Notes"],
            db_load_func=database.get_dues_by_member,
            db_add_func=self._add_dues,
            db_update_func=self._update_dues,
            db_delete_func=database.delete_dues_payment,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Year", tk.StringVar()),
                ("Amount", tk.StringVar()),
                ("Method", tk.StringVar(), {"widget": "combobox", "values": METHOD_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",
                r[3],
                f"{float(r[4]):.2f}" if r[4] else "0.00",
                r[5] or "",
                r[6] or ""
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind double-click event on the tree (or data table) to the handler
        self.tree.bind("<Double-1>", self.on_dues_double_click)

    def _transform_entries(self, entries):
        date_str, year, amount_str, method, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            payment_date = dt.strftime("%Y-%m-%d")
        except ValueError:
            payment_date = date_str
        try:
            amount = float(amount_str)
        except ValueError:
            amount = 0.0
        year = str(year) if year else str(datetime.now().year)
        return payment_date, amount, method or "", notes or "", year

    def _add_dues(self, *entries):
        payment_date, amount, method, notes, year = self._transform_entries(entries)
        database.add_dues_payment(self.member_id, amount, payment_date, method, notes, year)
        self.load_records(self.member_id)

    def _update_dues(self, payment_id, *entries):
        payment_date, amount, method, notes, year = self._transform_entries(entries)
        database.update_dues_payment(payment_id, amount=amount, payment_date=payment_date,
                                     method=method, notes=notes, year=year)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")
        default_year = database.get_default_year()
        self._open_edit_popup("Add Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              self._add_dues, [today_str, str(default_year), "", "", ""])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              lambda *vals: self._update_dues(row_id, *vals), current_values)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_dues_payment(row_id)
            self.load_records(self.member_id)

    # Double-click handler for dues table
    def on_dues_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Dues", ["Date", "Year", "Amount", "Method", "Notes"],
                              lambda *vals: self._update_dues(row_id, *vals), current_values)

    def _open_edit_popup(self, title, labels, save_func, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)
        popup.transient()
        popup.focus_set()

        # Fonts
        popup_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
        entry_font = tkFont.Font(family="Helvetica", size=12)
        input_width = 20  # uniform width for entries/combobox

        entry_vars = {}

        for idx, (label, default_value) in enumerate(zip(labels, default_values)):
            frame = tk.Frame(popup)
            lbl = tk.Label(frame, text=label, font=popup_font)
            lbl.pack(side=tk.LEFT)

            var = tk.StringVar(value=default_value)
            entry_vars[label] = var

            if label == "Method":
                entry = ttk.Combobox(frame, textvariable=var, values=METHOD_OPTIONS, font=entry_font, width=input_width)
            else:
                entry = tk.Entry(frame, textvariable=var, font=entry_font, width=input_width)
            entry.pack(side=tk.RIGHT)
            frame.pack(fill="x", padx=10, pady=5)

        def save():
            values = [entry_vars[label].get() for label in labels]
            save_func(*values)
            popup.destroy()  # only closes the popup

        save_button = tk.Button(popup, text="Save", command=save, font=popup_font)
        save_button.pack(pady=10)

        # Center and size the popup
        popup.update_idletasks()
        center_window(popup, width=350, height=250)

        # Make the popup modal
        popup.grab_set()
        # <-- IMPORTANT: remove popup.mainloop() here!


class WorkHoursTab(DataTab):
    def __init__(self, parent, member_id):
        super().__init__(
            parent,
            columns=["Date", "Activity", "Hours", "Notes"],  # Changed order: Activity and Hours
            db_load_func=database.get_work_hours_by_member,
            db_add_func=self._add_work,
            db_update_func=self._update_work,
            db_delete_func=database.delete_work_hours,
            entry_fields=[ 
                ("Date", tk.StringVar()),
                ("Hours", tk.StringVar()),
                ("Activity", tk.StringVar()),  # Changed field name to match updated order
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",  # Date is still in the second column
                r[3] or "",  # Activity is now the second column (was third before)
                f"{float(r[4]):.1f}" if r[4] else "0.0",  # Hours is now the third column (was second before)
                r[5] or ""   # Notes remains the same
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind double-click event on the tree (or data table) to the handler
        self.tree.bind("<Double-1>", self.on_work_hours_double_click)

    def _transform_entries(self, entries):
        date_str, hours_str, activity_str, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            date = date_str
        try:
            hours = float(hours_str)
        except ValueError:
            hours = 0.0
        return date, hours, activity_str or "", notes or ""

    def _add_work(self, *entries):
        date, hours, activity_str, notes = self._transform_entries(entries)
        database.add_work_hours(self.member_id, date, hours, activity_str, notes)
        self.load_records(self.member_id)

    def _update_work(self, work_id, *entries):
        date, hours, activity_str, notes = self._transform_entries(entries)
        database.update_work_hours(work_id, date=date, hours=hours, activity=activity_str, notes=notes)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")  # Get today's date
        # Open the edit popup, passing default values
        self._open_edit_popup("Add Work Hours", ["Date", "Hours", "Activity", "Notes"], 
                              self._add_work, [today_str, "", "", ""])

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
            
        
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        
        # Ensure the values are in the correct order: Date, Activity, Hours, Notes
        current_values = [
            current_values[0],  # Date
            current_values[1],  # Activity
            current_values[2],  # Hours
            current_values[3]   # Notes
        ]
        
        self._open_edit_popup("Edit Work Hours", ["Date", "Activity", "Hours", "Notes"], 
                            lambda *vals: self._update_work(row_id, *vals), current_values)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_work_hours(row_id)
            self.load_records(self.member_id)

    # Double-click handler for work hours table
    def on_work_hours_double_click(self, event):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))
        self._open_edit_popup("Edit Work Hours", ["Date", "Activity", "Hours", "Notes"],
                              lambda *vals: self._update_work(row_id, *vals), current_values)

    def _open_edit_popup(self, title, labels, save_function, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)
        popup.transient()
        popup.focus_set()

        # Define fonts
        popup_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
        entry_font = tkFont.Font(family="Helvetica", size=12)
        input_width = 23  # uniform width for all fields

        entry_vars = {}
        entries = []

        # Correct label order
        correct_labels = ["Date", "Activity", "Hours", "Notes"]

        for idx, label in enumerate(correct_labels):
            frame = tk.Frame(popup)

            # Bold label
            lbl = tk.Label(frame, text=label, font=popup_font)
            lbl.pack(side=tk.LEFT)

            var = tk.StringVar()
            if default_values and idx < len(default_values):
                var.set(default_values[idx])

            # Entry field
            entry = tk.Entry(frame, textvariable=var, font=entry_font, width=input_width)
            entry.pack(side=tk.RIGHT)

            entry_vars[label] = var
            entries.append(entry)
            frame.pack(fill="x", padx=10, pady=5)

        def save_record():
            date = entry_vars["Date"].get()
            activity = entry_vars["Activity"].get()
            hours = entry_vars["Hours"].get()
            notes = entry_vars["Notes"].get()
            save_function(date, hours, activity, notes)
            popup.destroy()

        save_button = tk.Button(popup, text="Save", command=save_record, font=popup_font)
        save_button.pack(pady=10)

        # Center and size popup
        popup.update_idletasks()
        center_window(popup, width=300, height=200)


class AttendanceTab(DataTab):
    def __init__(self, parent, member_id):
        # Initialize the DataTab with correct parameters for the AttendanceTab
        super().__init__(
            parent,
            columns=["Date", "Status", "Notes"],
            db_load_func=database.get_meeting_attendance,
            db_add_func=self._add_attendance,
            db_update_func=self._update_attendance,
            db_delete_func=database.delete_meeting_attendance,
            entry_fields=[
                ("Date", tk.StringVar()),
                ("Status", tk.StringVar(), {"widget": "combobox", "values": STATUS_OPTIONS}),
                ("Notes", tk.StringVar())
            ],
            row_adapter=lambda r: [
                datetime.strptime(r[2], "%Y-%m-%d").strftime("%m-%d-%Y") if r[2] else "",
                r[3] or "",
                r[4] or ""
            ]
        )
        self.member_id = member_id
        self._add_buttons(parent)
        self.load_records(member_id)

        # Bind the double-click event on the tree (or data table)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def edit_selected(self):
        """Triggered when 'Edit' button is clicked"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to edit")
            return
        row_id = int(selected[0])
        current_values = list(self.tree.item(selected[0], "values"))

        # Ensure values are in correct order: Date, Status, Notes
        current_values = [
            current_values[0],  # Date
            current_values[1],  # Status
            current_values[2]   # Notes
        ]

        # Open the edit popup
        self._open_edit_popup("Edit Attendance", ["Date", "Status", "Notes"],
                              lambda *vals: self._update_attendance(row_id, *vals), current_values)

    def _on_tree_double_click(self, event):
        """Triggered when a row in the tree is double-clicked"""
        self.edit_selected()

    def _transform_entries(self, entries):
        date_str, status, notes = entries
        try:
            dt = datetime.strptime(date_str, "%m-%d-%Y")
            date = dt.strftime("%Y-%m-%d")
        except ValueError:
            date = date_str
        return date, status or "", notes or ""

    def _add_attendance(self, *entries):
        date, status, notes = self._transform_entries(entries)
        database.add_meeting_attendance(self.member_id, date, status, notes)
        self.load_records(self.member_id)

    def _update_attendance(self, attendance_id, *entries):
        date, status, notes = self._transform_entries(entries)
        database.update_meeting_attendance(attendance_id, meeting_date=date, status=status, notes=notes)
        self.load_records(self.member_id)

    def _add_buttons(self, parent):
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5, sticky="w")
        ttk.Button(btn_frame, text="Add", command=self.add_record).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_selected).grid(row=0, column=2, padx=5)

    def add_record(self):
        today_str = datetime.now().strftime("%m-%d-%Y")
        self._open_edit_popup("Add Attendance", ["Date", "Status", "Notes"],
                              self._add_attendance, [today_str, STATUS_OPTIONS[0], ""])



    def _open_edit_popup(self, title, labels, save_function, default_values):
        popup = tk.Toplevel(self.parent)
        popup.title(title)
        popup.transient()
        popup.focus_set()

        # Define a bigger, bold font
        popup_font = tkFont.Font(family="Helvetica", size=12, weight="bold")
        entry_font = tkFont.Font(family="Helvetica", size=12)
        
        input_width = 20
        
        entry_vars = {}
        entries = []

        for idx, label in enumerate(labels):
            frame = tk.Frame(popup)
            
            lbl = tk.Label(frame, text=label, font=popup_font)
            lbl.pack(side=tk.LEFT)

            var = tk.StringVar()
            if default_values and idx < len(default_values):
                var.set(default_values[idx])

            if label == "Status":
                entry = ttk.Combobox(frame, textvariable=var, values=STATUS_OPTIONS, font=entry_font, width=input_width)
            else:
                entry = tk.Entry(frame, textvariable=var, font=entry_font, width=22)

            entry.pack(side=tk.RIGHT)
            entry_vars[label] = var
            entries.append(entry)
            frame.pack(fill="x", padx=10, pady=5)

        def save_record():
            date = entry_vars["Date"].get()
            status = entry_vars["Status"].get()
            notes = entry_vars["Notes"].get()
            save_function(date, status, notes)
            popup.destroy()

        save_button = tk.Button(popup, text="Save", command=save_record, font=popup_font)
        save_button.pack(pady=10)

        # Center the popup and optionally set a reasonable default size
        popup.update_idletasks()
        center_window(popup, width=300, height=200)  # Adjust size for larger font

        

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Info", "Select a record to delete")
            return
        row_id = int(selected[0])
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this record?"):
            database.delete_meeting_attendance(row_id)
            self.load_records(self.member_id)


class ReportsWindow(tk.Toplevel):
    def __init__(self, parent, member_id=None):
        super().__init__(parent)
        self.title("Reports")
        center_window(self, 900, 600, parent)

                # Keep it on top of the main window
        self.transient(parent)   # Associate with main window
        #self.grab_set()          # Make it modal (prevents interacting with main window)
        self.focus_set()             # Ensure it gets focus

        style = ttk.Style()
        #notebook = ttk.Notebook(self)
        #notebook.pack(fill="both", expand=True, padx=5, pady=5)
        style.configure("CustomNotebook.TNotebook.Tab", padding=[10, 5], anchor="center")
        self.notebook = ttk.Notebook(self, style="CustomNotebook.TNotebook")
        self.notebook.pack(fill="both", expand=True)

        # ---------------- Dues Tab ---------------- #
        dues_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(dues_tab_frame, text="Dues")
        DuesReport(dues_tab_frame, member_id).pack(fill="both", expand=True)

        # ---------------- Work Hours Tab ---------------- #
        work_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(work_tab_frame, text="Work Hours")
        Work_HoursReport(work_tab_frame, member_id).pack(fill="both", expand=True)

        # ---------------- Attendance Tab ---------------- #
        attendance_tab = ttk.Frame(self.notebook)
        self.notebook.add(attendance_tab, text="Meeting Attendance")
        AttendanceReport(attendance_tab, member_id).pack(fill="both", expand=True)

        # ---------------- Waiver Tab ---------------- #
        waiver_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(waiver_tab_frame, text="Waivers")
        WaiverReport(waiver_tab_frame, member_id).pack(fill="both", expand=True)

        # ---------------- Committees Tab ---------------- #
        committees_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(committees_tab_frame, text="Committees")
        CommitteesReport(committees_tab_frame, member_id).pack(fill="both", expand=True)

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
        
    
# ---------------- BaseReport ---------------- #
class BaseReport(tk.Frame):
    def __init__(self, parent, member_id=None, include_month=True):
        super().__init__(parent)
        self.member_id = member_id
        self.include_month = include_month
        self.tree = None

        try:
            default_year = database.get_setting("default_year")
            if default_year is None:
                default_year = datetime.now().year
        except Exception:
            default_year = datetime.now().year

        self.year_var = tk.IntVar(value=int(default_year))
        self.month_var = tk.StringVar(value="All")
        self.exclude_names_var = tk.BooleanVar(value=False)

        self._setup_controls()

    def _setup_controls(self):
        frame = tk.Frame(self)
        frame.pack(fill="x", pady=3)

        bold_font = tkFont.Font(family="Arial", size=10, weight="bold")
        tk.Label(frame, text="Year:", font=bold_font).pack(side="left", padx=(10,0))
        year_spin = tk.Spinbox(frame, from_=2000, to=2100, textvariable=self.year_var, width=6)
        year_spin.pack(side="left", padx=(0,10))
        self.year_var.trace_add("write", lambda *args: self.populate_report())

        if self.include_month:
            tk.Label(frame, text="Month:").pack(side="left")
            months = ["All"] + list(calendar.month_name[1:])
            month_cb = ttk.Combobox(frame, values=months, textvariable=self.month_var, state="readonly", width=10)
            month_cb.pack(side="left", padx=(0,10))
            self.month_var.trace_add("write", lambda *args: self.populate_report())

        tk.Button(frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=5)
        tk.Button(frame, text="Print Report", command=self.print_report).pack(side="left", padx=5)
        cb = ttk.Checkbutton(frame, text="Exclude Names From Print", variable=self.exclude_names_var)
        cb.pack(side="left", padx=10)

    def _get_default_filename(self, ext=".pdf"):
        report_name = self.__class__.__name__.replace("Report", " Report")
        year = self.year_var.get()
        month = self.month_var.get()
        if month == "All" or not self.include_month:
            filename = f"{report_name} {year}{ext}"
        else:
            filename = f"{report_name} {year} {month}{ext}"
        filename = "".join(c for c in filename if c not in r'\/:*?"<>|')
        return filename

    def export_csv(self):
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Export CSV", "No data to export.")
            return
        default_name = self._get_default_filename(".csv")
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files","*.csv")],
            initialfile=default_name
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([c.replace("_", " ").title() for c in self.columns])
                for item in items:
                    writer.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Export CSV", f"CSV exported successfully to {path}")
        except Exception as e:
            messagebox.showerror("Export CSV", f"Failed to export CSV: {e}")

    def print_report(self):
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        report_name = self.__class__.__name__.replace("Report", " Report")
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")
        headers = [c.replace("_", " ").title() for c in self.columns]

        col_widths = [len(h) for h in headers]
        for idx, col in enumerate(self.columns):
            for item in items:
                val = str(self.tree.item(item, "values")[idx])
                if len(val) > col_widths[idx]:
                    col_widths[idx] = len(val)
        col_widths = [w + 2 for w in col_widths]

        def format_val(col, val, width):
            val = "" if val is None else str(val)
            if col in ("badge", "badge_number", "roles", "terms"):
                return f"{val:^{width}}"
            else:
                return f"{val:<{width}}"

        def format_row(values):
            return " ".join(format_val(c, v, w) for c, v, w in zip(self.columns, values, col_widths))

        lines_per_page = 40
        pages, current_lines = [], []

        def add_header():
            total_width = sum(col_widths) + (len(col_widths) - 1)
            current_lines.append("Dug Hill Rod & Gun Club".center(total_width))
            current_lines.append(report_name.center(total_width))
            current_lines.append("=" * total_width)
            current_lines.append(format_row(headers))
            current_lines.append("-" * total_width)

        add_header()
        row_count = 0
        for item in items:
            row = list(self.tree.item(item, "values"))
            if self.exclude_names_var.get() and len(row) > 1:
                row[1] = "*****"
            current_lines.append(format_row(row))
            row_count += 1
            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)
        for i, page_lines in enumerate(pages, start=1):
            footer_width = sum(col_widths) + (len(col_widths) - 1)
            page_lines.append("=" * footer_width)
            page_lines.append(f"Generated: {generation_dt}".center(footer_width))
            page_lines.append(f"Page {i} of {total_pages}".center(footer_width))
            page_lines.append("End of Report".center(footer_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        def generate_pdf(path, full_text):
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Courier", 10)
            width, height = letter
            margin = 50
            usable_width = width - (2 * margin)
            char_width = c.stringWidth("M", "Courier", 10)
            max_chars = int(usable_width // char_width)
            y = height - margin
            line_height = 12
            for line in full_text.split("\n"):
                padded = line.ljust(max_chars)
                c.drawString(margin, y, padded)
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - margin
            c.save()

        parent_window = self.winfo_toplevel()
        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        print_window.transient(parent_window)
        print_window.focus_set()

        frame = tk.Frame(print_window)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        btn_frame = tk.Frame(print_window)
        btn_frame.pack(fill="x", pady=5)

        def save_as_pdf():
            default_name = self._get_default_filename(".pdf")
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Files","*.pdf")],
                initialfile=default_name
            )
            if not path:
                return
            generate_pdf(path, full_text)
            messagebox.showinfo("Save as PDF", f"PDF saved to {path}")

        def print_to_pdf():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            generate_pdf(tmp.name, full_text)
            webbrowser.open_new(tmp.name)

        tk.Button(btn_frame, text="Print", command=print_to_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export CSV", command=self.export_csv).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=print_window.destroy).pack(side="right", padx=5)

    def _on_row_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        values = self.tree.item(item_id, "values")
        if not values:
            return

        badge_or_member_id = values[0]
        member_id = database.get_member_id_from_badge(badge_or_member_id)
        if member_id is None:
            return

        tab_name = REPORT_TAB_MAP.get(self.__class__.__name__, "membership")
        try:
            member_form = MemberForm(
                self.winfo_toplevel(),
                member_id=member_id,
                select_tab=tab_name
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not open member form: {e}")

    def populate_report(self):
        raise NotImplementedError


# ---------------- DuesReport ---------------- #
class DuesReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "membership_type", "amount_due", "balance_due",
                        "year", "last_payment_date", "amount_paid", "method")
        self.column_widths = (80, 150, 105, 90, 90, 60, 120, 90, 90)
        super().__init__(parent, member_id, include_month=False)
        self._create_tree()
        self.populate_report()
        self.tree.bind("<Double-1>", self._on_row_double_click)


    def _create_tree(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Which columns should be centered?
        center_cols = {"badge", "year", "last_payment_date", "method"}

        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.replace("_", " ").title(),
                              command=lambda c=col: self._sort_column(c, False))
            if col in center_cols:
                anchor = "center"
            elif col in ("amount_due", "balance_due", "amount_paid"):
                anchor = "e"
            else:
                anchor = "w"
            self.tree.column(col, width=width, anchor=anchor, stretch=True)

    def _sort_column(self, col, reverse):
            """Sort treeview column and show arrow."""
            data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
            # Numeric sort if possible
            try:
                data = [(float(v), k) for v, k in data]
            except ValueError:
                pass

            data.sort(reverse=reverse)
            for idx, (_, k) in enumerate(data):
                self.tree.move(k, "", idx)

            # Update all headings to add arrow to sorted column
            for c in self.columns:
                header_text = c.replace("_", " ").title()
                if c == "badge":
                    header_text = "Badge"
                if c == col:
                    arrow = " ▲" if not reverse else " ▼"
                    self.tree.heading(c, text=header_text + arrow,
                                    command=lambda c=c: self._sort_column(c, not reverse))
                else:
                    self.tree.heading(c, text=header_text,
                                    command=lambda c=c: self._sort_column(c, False))


    def populate_report(self):
        self.tree.delete(*self.tree.get_children())
        year = self.year_var.get()
        members = database.get_all_members()
        for m in members:
            badge = m[1]
            name = f"{m[3]} {m[4]}"
            membership_type = m[2]
            amount_due = 0
            setting_key = f"dues_{membership_type.lower()}" if membership_type else ""
            try:
                amount_due = float(database.get_setting(setting_key) or 0)
            except:
                pass
            dues = database.get_dues_by_member(m[0])
            total_paid, last_payment_date, method = 0, "", ""
            for d in dues:
                try:
                    amt = float(d[4])
                except:
                    amt = 0
                pay_year = int(d[3]) if len(d) > 3 else year
                if pay_year != year:
                    continue
                total_paid += amt
                date = d[2] if len(d) > 2 else ""
                if date and (not last_payment_date or date > last_payment_date):
                    last_payment_date = date
                    method = d[5] if len(d) > 5 else ""
            if last_payment_date:
                try:
                    last_payment_date = datetime.strptime(last_payment_date, "%Y-%m-%d").strftime("%m-%d-%Y")
                except:
                    pass
            balance_due = max(amount_due - total_paid, 0)
            self.tree.insert("", "end", values=(badge, name, membership_type,
                                                f"{amount_due:.2f}", f"{balance_due:.2f}",
                                                year, last_payment_date, f"{total_paid:.2f}", method))

    def print_report(self):
        """Print preview of dues report."""
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = f"Dues Report - Year {self.year_var.get()}"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")

        rows = [self.tree.item(item, "values") for item in items]
        page_width = 100  # wider for financial data
        num_cols = len(self.columns)

        # Widths
        raw_widths = [max(len(str(row[idx])) for row in rows) if rows else 5 for idx in range(num_cols)]
        raw_widths = [max(raw_widths[i], len(self.columns[i])) for i in range(num_cols)]
        total_raw = sum(raw_widths)
        col_widths = [max(5, int(w / total_raw * page_width)) for w in raw_widths]
        diff = page_width - sum(col_widths)
        if diff != 0:
            col_widths[-1] += diff

        center_cols = {"badge", "year", "last_payment_date", "method"}
        right_cols = {"amount_due", "balance_due", "amount_paid"}

        def format_row(values):
            out = []
            for v, w, col in zip(values, col_widths, self.columns):
                v = str(v)
                if col in center_cols:
                    out.append(v.center(w))
                elif col in right_cols:
                    out.append(v.rjust(w))
                else:
                    out.append(v.ljust(w))
            return " ".join(out)

        # Paging
        lines_per_page = 35
        pages, current_lines = [], []

        def add_header():
            total_width = page_width
            current_lines.append(org_name.center(total_width))
            
            # Split title and timeframe
            report_title = "Dues Report"
            timeframe = f"Year: {self.year_var.get()}"
            
            current_lines.append(report_title.center(total_width))
            current_lines.append(timeframe.center(total_width))  # new line for timeframe
            current_lines.append("=" * total_width)
            current_lines.append(format_row([c.replace("_", " ").title() for c in self.columns]))
            current_lines.append("-" * total_width)


        add_header()
        row_count = 0
        for row in rows:
            row_vals = list(row)
            if self.exclude_names_var.get() and len(row_vals) > 1:
                row_vals[1] = "*****"
            current_lines.append(format_row(row_vals))
            row_count += 1
            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)
        for i, page_lines in enumerate(pages, start=1):
            page_lines.append("=" * page_width)
            page_lines.append(f"Generated: {generation_dt}".center(page_width))
            page_lines.append(f"Page {i} of {total_pages}".center(page_width))
            page_lines.append("End of Report".center(page_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        # --- Print Preview Window ---
        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        center_window(print_window, width=800, height=600, parent=self.winfo_toplevel())
        print_window.transient()
        print_window.focus_set()
        frame = tk.Frame(print_window)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # --- Buttons ---
        btn_frame = tk.Frame(print_window)
        btn_frame.pack(fill="x", pady=5)

        def generate_pdf(path, full_text):
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Courier", 10)
            width, height = letter
            margin = 50
            usable_width = width - 2 * margin
            char_width = c.stringWidth("M", "Courier", 10)
            max_chars = int(usable_width // char_width)
            y = height - margin
            line_height = 12
            for line in full_text.split("\n"):
                padded = line.ljust(max_chars)
                c.drawString(margin, y, padded)
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - margin
            c.save()

        def save_as_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files","*.pdf")])
            if path:
                generate_pdf(path, full_text)
                messagebox.showinfo("Save as PDF", f"PDF saved to {path}")

        def print_to_pdf():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            generate_pdf(tmp.name, full_text)
            webbrowser.open_new(tmp.name)

        def export_csv():
            self.export_csv()

        tk.Button(btn_frame, text="Print", command=print_to_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export CSV", command=export_csv).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=print_window.destroy).pack(side="right", padx=5)


# ---------------- WorkHoursReport ---------------- #
class Work_HoursReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "work_hours")
        self.column_widths = (80, 260, 120)
        super().__init__(parent, member_id)
        self._create_tree()
        self.populate_report()
        self.tree.bind("<Double-1>", self._on_row_double_click)


    def _create_tree(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(
                col,
                text=col.replace("_", " ").title(),
                command=lambda c=col: self._sort_column(c, False)  # sortable
            )
            anchor = "center" if col in ("work_hours", "badge") else "w"
            self.tree.column(col, width=width, anchor=anchor, stretch=True)

    def _sort_column(self, col, reverse):
            """Sort treeview data by column and add arrow to sorted column."""
            data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
            try:
                data.sort(key=lambda t: float(t[0]) if t[0] != "" else 0, reverse=reverse)
            except ValueError:
                data.sort(key=lambda t: t[0], reverse=reverse)

            for index, (_, k) in enumerate(data):
                self.tree.move(k, "", index)

            # Update headings to show arrow only on the sorted column
            for c in self.columns:
                header_text = c.replace("_", " ").title()
                if c == "badge":
                    header_text = "Badge"
                if c == col:
                    arrow = " ▲" if not reverse else " ▼"
                    self.tree.heading(c, text=header_text + arrow,
                                    command=lambda c=c: self._sort_column(c, not reverse))
                else:
                    self.tree.heading(c, text=header_text,
                                    command=lambda c=c: self._sort_column(c, False))


    def populate_report(self):
        self.tree.delete(*self.tree.get_children())
        year = self.year_var.get()
        month_name = self.month_var.get()
        if month_name == "All":
            start, end = f"{year}-01-01", f"{year}-12-31"
        else:
            month_idx = list(calendar.month_name).index(month_name)
            start = f"{year}-{month_idx:02d}-01"
            last_day = calendar.monthrange(year, month_idx)[1]
            end = f"{year}-{month_idx:02d}-{last_day}"
        rows = database.get_work_hours_report(self.member_id, start, end)
        for badge, first, last, total_hours in rows:
            name = f"{last}, {first}"
            self.tree.insert("", "end", values=(badge or "", name, total_hours or 0))

    def print_report(self):
        """Print preview of work hours report with timeframe under report name."""
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = "Work Hours Report"
        # new timeframe line
        if self.month_var.get() == "All":
            timeframe = f"Year: {self.year_var.get()}"
        else:
            timeframe = f"{self.month_var.get()} {self.year_var.get()}"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")

        rows = [self.tree.item(item, "values") for item in items]
        page_width = 85
        num_cols = len(self.columns)
        raw_widths = [max(len(str(row[idx])) for row in rows) if rows else 5 for idx in range(num_cols)]
        raw_widths = [max(raw_widths[i], len(self.columns[i])) for i in range(num_cols)]
        total_raw = sum(raw_widths)
        col_widths = [max(3, int(w / total_raw * page_width)) for w in raw_widths]
        diff = page_width - sum(col_widths)
        if diff != 0:
            col_widths[-1] += diff

        def format_row(values):
            formatted = []
            for v, w, col in zip(values, col_widths, self.columns):
                v = str(v)
                # center badge column
                if col == "badge":
                    formatted.append(v.center(w))
                else:
                    formatted.append(v.ljust(w))
            return " ".join(formatted)

        lines_per_page = 40
        pages, current_lines = [], []

        def add_header():
            total_width = page_width
            current_lines.append(org_name.center(total_width))
            current_lines.append(report_name.center(total_width))
            current_lines.append(timeframe.center(total_width))  # new timeframe line
            current_lines.append("=" * total_width)
            current_lines.append(format_row([c.replace("_", " ").title() for c in self.columns]))
            current_lines.append("-" * total_width)

        add_header()
        row_count = 0
        for row in rows:
            row_vals = list(row)
            if self.exclude_names_var.get() and len(row_vals) > 1:
                row_vals[1] = "*****"
            current_lines.append(format_row(row_vals))
            row_count += 1
            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)
        for i, page_lines in enumerate(pages, start=1):
            page_lines.append("=" * page_width)
            page_lines.append(f"Generated: {generation_dt}".center(page_width))
            page_lines.append(f"Page {i} of {total_pages}".center(page_width))
            page_lines.append("End of Report".center(page_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        # PDF helper
        def generate_pdf(path, full_text):
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Courier", 10)
            width, height = letter
            margin = 50
            usable_width = width - 2 * margin
            char_width = c.stringWidth("M", "Courier", 10)
            max_chars = int(usable_width // char_width)
            y = height - margin
            line_height = 12
            for line in full_text.split("\n"):
                padded = line.ljust(max_chars)
                c.drawString(margin, y, padded)
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - margin
            c.save()

        # --- Print Preview ---
        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        center_window(print_window, width=725, height=600, parent=self.winfo_toplevel())
        print_window.transient()
        print_window.focus_set()
        frame = tk.Frame(print_window)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # --- Buttons ---
        btn_frame = tk.Frame(print_window)
        btn_frame.pack(fill="x", pady=5)

        def save_as_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
            if path:
                generate_pdf(path, full_text)
                messagebox.showinfo("Save as PDF", f"PDF saved to {path}")

        def print_to_pdf():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            generate_pdf(tmp.name, full_text)
            webbrowser.open_new(tmp.name)

        def export_csv():
            self.export_csv()

        tk.Button(btn_frame, text="Print", command=print_to_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export CSV", command=export_csv).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=print_window.destroy).pack(side="right", padx=5)


# ---------------- AttendanceReport ---------------- #
class AttendanceReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge", "name", "status")
        self.column_widths = (80, 260, 120)
        self.sort_states = {}  # Track column sort states
        super().__init__(parent, member_id)
        self._create_tree()
        self.populate_report()
        self.tree.bind("<Double-1>", self._on_row_double_click)

    def _create_tree(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        for col, width in zip(self.columns, self.column_widths):
            header_text = "Badge" if col == "badge" else col.replace("_", " ").title()
            self.tree.heading(col, text=header_text,
                              command=lambda c=col: self.sort_by_column(c))
            anchor = "center" if col in ("status", "badge") else "w"
            self.tree.column(col, width=width, anchor=anchor, stretch=True)

    def sort_by_column(self, col):
        """Sort treeview contents and show arrow on the sorted column."""
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        # Detect numeric vs text sort
        try:
            items = [(float(v), k) for v, k in items]
        except ValueError:
            pass

        reverse = self.sort_states.get(col, False)
        self.sort_states[col] = not reverse
        items.sort(reverse=reverse)

        for index, (val, k) in enumerate(items):
            self.tree.move(k, "", index)

        # Update headings with arrow
        for c in self.columns:
            base = "Badge" if c == "badge" else c.replace("_", " ").title()
            if c == col:
                arrow = " ▲" if not reverse else " ▼"
                self.tree.heading(c, text=base + arrow,
                                  command=lambda c=c: self.sort_by_column(c))
            else:
                self.tree.heading(c, text=base, command=lambda c=c: self.sort_by_column(c))

    # ... keep populate_report() and print_report() as-is ...


    def populate_report(self):
        self.tree.delete(*self.tree.get_children())
        year = self.year_var.get()
        month_name = self.month_var.get()

        # Change column header based on report type
        if month_name == "All":
            self.tree.heading("status", text="Number of Meetings", command=lambda: self.sort_by_column("status"))
        else:
            self.tree.heading("status", text="Status", command=lambda: self.sort_by_column("status"))

        members = database.get_all_members()
        for m in members:
            badge = m[1]
            name = f"{m[3]} {m[4]}"

            if month_name == "All":
                total = database.count_member_attendance(m[0], year)
                self.tree.insert("", "end", values=(badge, name, total))
            else:
                month_idx = list(calendar.month_name).index(month_name)
                status = database.get_member_status_for_month(m[0], year, month_idx)

                if status not in ("Attended", "Exempt", "Exemption Granted"):
                    continue  # Skip irrelevant statuses

                self.tree.insert("", "end", values=(badge, name, status))

    def print_report(self):
        """Print preview of attendance report with month/year in header."""
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = "Meeting Attendance Report"
        month_name = self.month_var.get()
        month_display = month_name if month_name != "All" else "Yearly"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")

        # Gather rows
        rows = [self.tree.item(item, "values") for item in items]
        headers = [self.tree.heading(c)["text"] for c in self.columns]

        page_width = 85
        num_cols = len(self.columns)

        raw_widths = [max(len(str(row[idx])) for row in rows) if rows else 5 for idx in range(num_cols)]
        raw_widths = [max(raw_widths[i], len(headers[i])) for i in range(num_cols)]
        total_raw = sum(raw_widths)
        col_widths = [max(3, int(w / total_raw * page_width)) for w in raw_widths]
        diff = page_width - sum(col_widths)
        if diff != 0:
            col_widths[-1] += diff

        def format_row(values):
            formatted = []
            for (v, w, col) in zip(values, col_widths, self.columns):
                # Center badge always
                if col == "badge":
                    formatted.append(str(v).center(w))
                # Center status if it's a yearly report
                elif col == "status" and self.month_var.get() == "All":
                    formatted.append(str(v).center(w))
                else:
                    formatted.append(str(v).ljust(w))
            return " ".join(formatted)


        lines_per_page = 40
        pages, current_lines = [], []

        def add_header():
            total_width = page_width
            current_lines.append(org_name.center(total_width))
            current_lines.append(report_name.center(total_width))
            year_display = str(self.year_var.get())
            if month_name != "All":
                current_lines.append(f"Month: {month_name}    Year: {year_display}".center(total_width))
            else:
                current_lines.append(f"Year: {year_display}".center(total_width))
            current_lines.append("=" * total_width)
            current_lines.append(format_row(headers))
            current_lines.append("-" * total_width)

        add_header()
        row_count = 0
        for row in rows:
            row_vals = list(row)
            if self.exclude_names_var.get() and len(row_vals) > 1:
                row_vals[1] = "*****"
            current_lines.append(format_row(row_vals))
            row_count += 1
            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)
        for i, page_lines in enumerate(pages, start=1):
            page_lines.append("=" * page_width)
            page_lines.append(f"Generated: {generation_dt}".center(page_width))
            page_lines.append(f"Page {i} of {total_pages}".center(page_width))
            page_lines.append("End of Report".center(page_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        # PDF generator
        def generate_pdf(path, full_text):
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Courier", 10)
            width, height = letter
            margin = 50
            usable_width = width - 2 * margin
            char_width = c.stringWidth("M", "Courier", 10)
            max_chars = int(usable_width // char_width)
            y = height - margin
            line_height = 12
            for line in full_text.split("\n"):
                padded = line.ljust(max_chars)
                c.drawString(margin, y, padded)
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - margin
            c.save()

        # Print Preview Window
        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        center_window(print_window, width=725, height=600, parent=self.winfo_toplevel())
        print_window.transient()
        print_window.focus_set()
        frame = tk.Frame(print_window)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # Buttons
        btn_frame = tk.Frame(print_window)
        btn_frame.pack(fill="x", pady=5)

        def save_as_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
            if path:
                generate_pdf(path, full_text)
                messagebox.showinfo("Save as PDF", f"PDF saved to {path}")

        def print_to_pdf():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            generate_pdf(tmp.name, full_text)
            webbrowser.open_new(tmp.name)

        def export_csv():
            self.export_csv()

        tk.Button(btn_frame, text="Print", command=print_to_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export CSV", command=export_csv).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=print_window.destroy).pack(side="right", padx=5)


# ---------------- WaiverReport ---------------- #
class WaiverReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ["badge", "name", "waiver"]
        self.column_widths = [80, 200, 100]
        super().__init__(parent, member_id, include_month=False)
        self._create_tree()
        self.populate_report()
        self.tree.bind("<Double-1>", self._on_row_double_click)


    def _create_tree(self):
        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, pady=5)
        self.tree = ttk.Treeview(frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Track sort order per column
        self._sort_orders = {col: False for col in self.columns}

        for col, width in zip(self.columns, self.column_widths):
            self.tree.heading(col, text=col.replace("_", " ").title(),
                            command=lambda c=col: self._sort_by(c))
            anchor = "center" if col == "badge" else "w"
            self.tree.column(col, width=width, anchor=anchor, stretch=True)

    def _sort_by(self, col):
        """Sort treeview by given column and display arrow for sort direction."""
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

        # Determine sort type
        try:
            data = [(float(d[0]), d[1]) for d in data]
        except ValueError:
            data = [(d[0].lower(), d[1]) for d in data]

        # Toggle sort order
        reverse = self._sort_orders.get(col, False)
        data.sort(reverse=reverse)
        self._sort_orders[col] = not reverse

        # Rearrange items in the tree
        for index, (_, k) in enumerate(data):
            self.tree.move(k, "", index)

        # Update column headers to show arrows
        for c in self.tree["columns"]:
            base = c.replace("_", " ").title()
            if c == col:
                arrow = " ▲" if not reverse else " ▼"
                self.tree.heading(c, text=base + arrow, command=lambda c=c: self._sort_by(c))
            else:
                self.tree.heading(c, text=base, command=lambda c=c: self._sort_by(c))



    def populate_report(self):
        self.tree.delete(*self.tree.get_children())
        rows = database.get_waiver_report()
        for m in rows:
            self.tree.insert("", "end", values=(m["badge_number"], m["name"], m["waiver"]))

    def print_report(self):
        """Print preview of waiver report."""
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = "Waiver Report"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")

        # Gather rows from the tree
        rows = [self.tree.item(item, "values") for item in items]

        # Format column headers nicely
        headers = [c.replace("_", " ").title() for c in self.columns]

        # Determine page width (characters)
        page_width = 85
        num_cols = len(self.columns)

        # Compute column widths proportionally
        raw_widths = [max(len(str(row[idx])) for row in rows) if rows else 5 for idx in range(num_cols)]
        raw_widths = [max(raw_widths[i], len(headers[i])) for i in range(num_cols)]
        total_raw = sum(raw_widths)
        col_widths = [max(3, int(w / total_raw * page_width)) for w in raw_widths]
        diff = page_width - sum(col_widths)
        if diff != 0:
            col_widths[-1] += diff

        def format_row(values):
            formatted = []
            for v, w, col in zip(values, col_widths, self.columns):
                if col == "badge":
                    formatted.append(str(v).center(w))  # center badge
                else:
                    formatted.append(str(v).ljust(w))
            return " ".join(formatted)


        lines_per_page = 40
        pages, current_lines = [], []

        def add_header():
            total_width = page_width
            current_lines.append(org_name.center(total_width))
            current_lines.append(report_name.center(total_width))
            current_lines.append("=" * total_width)
            current_lines.append(format_row(headers))
            current_lines.append("-" * total_width)

        add_header()
        row_count = 0
        for row in rows:
            row_vals = list(row)
            if self.exclude_names_var.get() and len(row_vals) > 1:
                row_vals[1] = "*****"
            current_lines.append(format_row(row_vals))
            row_count += 1
            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)
        for i, page_lines in enumerate(pages, start=1):
            page_lines.append("=" * page_width)
            page_lines.append(f"Generated: {generation_dt}".center(page_width))
            page_lines.append(f"Page {i} of {total_pages}".center(page_width))
            page_lines.append("End of Report".center(page_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        # PDF generation helper
        def generate_pdf(path, full_text):
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Courier", 10)
            width, height = letter
            margin = 50
            usable_width = width - 2 * margin
            char_width = c.stringWidth("M", "Courier", 10)
            max_chars = int(usable_width // char_width)
            y = height - margin
            line_height = 12
            for line in full_text.split("\n"):
                padded = line.ljust(max_chars)
                c.drawString(margin, y, padded)
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - margin
            c.save()

        # --- Print Preview Window ---
        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        center_window(print_window, width=725, height=600, parent=self.winfo_toplevel())
        print_window.transient()
        print_window.focus_set()
        frame = tk.Frame(print_window)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        # --- Buttons ---
        btn_frame = tk.Frame(print_window)
        btn_frame.pack(fill="x", pady=5)

        def save_as_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files","*.pdf")])
            if path:
                generate_pdf(path, full_text)
                messagebox.showinfo("Save as PDF", f"PDF saved to {path}")

        def print_to_pdf():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            generate_pdf(tmp.name, full_text)
            webbrowser.open_new(tmp.name)

        def export_csv():
            self.export_csv()

        tk.Button(btn_frame, text="Print", command=print_to_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export CSV", command=export_csv).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=print_window.destroy).pack(side="right", padx=5)


# ---------------- CommitteesReport ---------------- #
class CommitteesReport(BaseReport):
    def __init__(self, parent, member_id=None):
        self.columns = ("badge_number", "name", "notes")
        self.column_widths = (80, 250, 300)
        super().__init__(parent, member_id, include_month=False)

        self._setup_committee_filter()
        self._create_tree()
        self.populate_report()
        
    def _setup_committee_filter(self):
        bold_font = tkFont.Font(family="Arial", size=10, weight="bold")
        tk.Label(self, text="Committee:", font=bold_font).pack(anchor="w", padx=10, pady=(5, 2))

        raw_committees = database.get_committee_names()
        committees = sorted([c for c in raw_committees if c.lower() != "committee id"])
        committees.append("Executive Committee")
        self.committee_var = tk.StringVar()
        cb = ttk.Combobox(self, values=committees, textvariable=self.committee_var, state="readonly")
        cb.pack(anchor="w", padx=10, pady=(0, 5))
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_committee_change())

    def _on_committee_change(self):
        selected = self.committee_var.get()
        if selected == "Executive Committee":
            self.columns = ("badge_number", "name", "role", "term")  # notes removed
            self.column_widths = (80, 200, 150, 100)
        else:
            self.columns = ("badge_number", "name", "notes")
            self.column_widths = (80, 250, 300)

        if hasattr(self, "tree_frame") and self.tree_frame:
            self.tree_frame.destroy()
        self._create_tree()
        self.populate_report()


    def _create_tree(self):
        self.tree_frame = tk.Frame(self)
        self.tree_frame.pack(fill="both", expand=True, pady=5)

        self.tree = ttk.Treeview(self.tree_frame, columns=self.columns, show="headings")
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._on_row_double_click)

        for col, width in zip(self.columns, self.column_widths):
            header_text = "Badge" if col == "badge_number" else col.replace("_", " ").title()
            self.tree.heading(col, text=header_text, command=lambda c=col: self._sort_tree(c, False))
            if col == "role":
                anchor = "w"
            elif col == "badge_number":
                anchor = "center"
            else:
                anchor = "w"
            self.tree.column(col, width=width, anchor=anchor, stretch=True)

    def _sort_tree(self, col, reverse):
        # Gather the data
        data_list = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        try:
            data_list.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            data_list.sort(key=lambda t: t[0].lower() if isinstance(t[0], str) else t[0], reverse=reverse)
        
        # Reorder the items
        for index, (val, k) in enumerate(data_list):
            self.tree.move(k, "", index)

        # Update headers to show arrow only on the sorted column
        for c in self.columns:
            header_text = "Badge" if c == "badge_number" else c.replace("_", " ").title()
            if c == col:
                arrow = " ▲" if not reverse else " ▼"
                self.tree.heading(c, text=header_text + arrow,
                                command=lambda c=c: self._sort_tree(c, not reverse))
            else:
                self.tree.heading(c, text=header_text,
                                command=lambda c=c: self._sort_tree(c, False))


    def populate_report(self):
        if self.tree is None:
            return
        self.tree.delete(*self.tree.get_children())

        selected_committee = getattr(self, "committee_var", tk.StringVar()).get()
        if not selected_committee:
            return

        if selected_committee == "Executive Committee":
            rows = database.get_executive_committee_members()
            for row in rows:
                badge = row.get("badge_number", "")
                name = f"{row.get('first_name','')} {row.get('last_name','')}".strip()
                role = row.get("roles", "")
                term = row.get("terms", "")
                notes = row.get("notes") or ""  # leave blank if no notes
                self.tree.insert("", "end", values=(badge, name, role, term, notes))
        else:
            rows = database.get_members_by_committee(selected_committee)
            for row in rows:
                badge_number = row.get("badge_number", "")
                name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
                notes = row.get("notes") or ""
                self.tree.insert("", "end", values=(badge_number, name, notes))

    def print_report(self):
        if self.tree is None:
            return
        items = self.tree.get_children()
        if not items:
            messagebox.showinfo("Print Report", "No data to print.")
            return

        org_name = "Dug Hill Rod & Gun Club"
        report_name = "Committee: " + self.committee_var.get() + " Roster"
        generation_dt = datetime.now().strftime("%m-%d-%Y %H:%M:%S")

        headers = [("Badge" if c == "badge_number" else c.replace("_", " ").title()) for c in self.columns]
        rows = [self.tree.item(item, "values") for item in items]

        page_width = 85
        num_cols = len(self.columns)
        raw_widths = [max(len(str(row[idx])) for row in rows) if rows else 5 for idx in range(num_cols)]
        raw_widths = [max(raw_widths[i], len(headers[i])) for i in range(num_cols)]
        total_raw = sum(raw_widths)
        col_widths = [max(3, int(w / total_raw * page_width)) for w in raw_widths]
        diff = page_width - sum(col_widths)
        if diff != 0:
            col_widths[-1] += diff

        def format_row(values):
            formatted = []
            for i in range(len(col_widths)):
                v = values[i] if i < len(values) else ""
                col_name = self.columns[i] if i < len(self.columns) else ""
                if col_name == "badge_number":
                    formatted.append(str(v).center(col_widths[i]))
                elif col_name == "role":
                    formatted.append(str(v).ljust(col_widths[i]))
                else:
                    formatted.append(str(v).ljust(col_widths[i]))
            return " ".join(formatted)


        lines_per_page = 40
        pages, current_lines = [], []

        def add_header():
            total_width = page_width
            current_lines.append(org_name.center(total_width))
            current_lines.append(report_name.center(total_width))
            current_lines.append("=" * total_width)
            current_lines.append(format_row(headers))
            current_lines.append("-" * total_width)

        add_header()
        row_count = 0
        for row in rows:
            row_vals = list(row)
            if self.exclude_names_var.get() and len(row_vals) > 1:
                row_vals[1] = "*****"
            current_lines.append(format_row(row_vals))
            row_count += 1
            if row_count >= lines_per_page - 6:
                pages.append(current_lines)
                current_lines = []
                row_count = 0
                add_header()
        if current_lines:
            pages.append(current_lines)

        total_pages = len(pages)
        for i, page_lines in enumerate(pages, start=1):
            page_lines.append("=" * page_width)
            page_lines.append(f"Generated: {generation_dt}".center(page_width))
            page_lines.append(f"Page {i} of {total_pages}".center(page_width))
            page_lines.append("End of Report".center(page_width))

        full_text = "\n\n".join("\n".join(p) for p in pages)

        def generate_pdf(path, full_text):
            c = canvas.Canvas(path, pagesize=letter)
            c.setFont("Courier", 10)
            width, height = letter
            margin = 50
            usable_width = width - 2 * margin
            char_width = c.stringWidth("M", "Courier", 10)
            max_chars = int(usable_width // char_width)
            y = height - margin
            line_height = 12
            for line in full_text.split("\n"):
                padded = line.ljust(max_chars)
                c.drawString(margin, y, padded)
                y -= line_height
                if y < margin:
                    c.showPage()
                    c.setFont("Courier", 10)
                    y = height - margin
            c.save()

        print_window = tk.Toplevel(self)
        print_window.title(f"{report_name} - Print Preview")
        center_window(print_window, width=725, height=600, parent=self.winfo_toplevel())
        print_window.transient()
        print_window.focus_set()
        frame = tk.Frame(print_window)
        frame.pack(fill="both", expand=True)

        text = tk.Text(frame, wrap="none", font=("Courier", 10))
        text.insert("1.0", full_text)
        text.config(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        hsb.grid(row=1, column=0, sticky="ew")
        text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        btn_frame = tk.Frame(print_window)
        btn_frame.pack(fill="x", pady=5)

        def save_as_pdf():
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf")])
            if path:
                generate_pdf(path, full_text)
                messagebox.showinfo("Save as PDF", f"PDF saved to {path}")

        def print_to_pdf():
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            generate_pdf(tmp.name, full_text)
            webbrowser.open_new(tmp.name)

        def export_csv():
            self.export_csv()

        tk.Button(btn_frame, text="Print", command=print_to_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save as PDF", command=save_as_pdf).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Export CSV", command=export_csv).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=print_window.destroy).pack(side="right", padx=5)


if __name__ == "__main__":
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()