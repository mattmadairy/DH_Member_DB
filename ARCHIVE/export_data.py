import os
import csv
import datetime
import database
import subprocess
import sys


def export_members_to_csv():
    # Get all members from the database
    members = database.get_all_members()

    # Filter out deleted members (assuming deleted_at is last column in tuple)
    active_members = [m for m in members if len(m) < 18 or m[17] is None]

    # Define the Downloads folder
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    # Create filename with date & time
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"DHRGC_members_export_{timestamp}.csv"
    filepath = os.path.join(downloads_folder, filename)

    # Define the CSV headers
    headers = [
        "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
        "Date of Birth", "Email Address", "Phone Number", "Address", "City",
        "State", "Zip Code", "Join Date", "Email Address 2", "Sponsor",
        "Card/Fob Internal Number", "Card/Fob External Number"
    ]

    # Write the CSV file
    with open(filepath, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        for m in active_members:
            writer.writerow(m[:17])  # Exclude deleted_at

    # Automatically open the file after export
    try:
        if sys.platform.startswith("darwin"):  # macOS
            subprocess.call(("open", filepath))
        elif os.name == "nt":  # Windows
            os.startfile(filepath)
        elif os.name == "posix":  # Linux
            subprocess.call(("xdg-open", filepath))
    except Exception as e:
        print(f"Could not open the file automatically: {e}")

    return filepath


if __name__ == "__main__":
    path = export_members_to_csv()
    print(f"Data exported to {path}")
