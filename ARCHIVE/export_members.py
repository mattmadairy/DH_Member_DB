import csv
import database
from datetime import datetime
import os
import platform
import subprocess
from tkinter import filedialog, Tk

def export_to_csv():
    members = database.get_all_members()

    # Create default filename with today's date
    today_str = datetime.now().strftime("%Y-%m-%d")
    default_filename = f"DHRGC_members_export_{today_str}.csv"

    # Hide the root Tkinter window for file dialog
    root = Tk()
    root.withdraw()

    # Ask user where to save file
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        initialfile=default_filename,
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if not filepath:  # User canceled
        return None

    headers = [
        "Badge Number", "Membership Type", "First Name", "Last Name",
        "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
        "Address", "City", "State", "Zip Code", "Join Date",
        "Sponsor", "Card/FOB Internal Number", "Card/FOB External Number"
    ]

    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for m in members:
            row = (
                m[1], m[2], m[3], m[4], m[5],
                m[6], m[13], m[7], m[8], m[9],
                m[10], m[11], m[12], m[14], m[15], m[16]
            )
            writer.writerow(row)

    # Open the CSV automatically
    open_file(filepath)

    return filepath

def open_file(filepath):
    """Open the file with the default program depending on OS."""
    try:
        if platform.system() == "Windows":
            os.startfile(filepath)  # Windows built-in
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", filepath])
        else:  # Linux and others
            subprocess.run(["xdg-open", filepath])
    except Exception as e:
        print(f"Could not open file automatically: {e}")
