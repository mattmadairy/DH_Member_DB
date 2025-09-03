import pandas as pd
from datetime import datetime
import database  # your database module

def add_meeting_records_from_excel(file_path, meeting_date=None, status="Present", notes_column=None):
    """
    Reads an Excel file and adds meeting attendance records for matching members.

    Args:
        file_path (str): Path to the Excel file.
        meeting_date (str | None): Date of the meeting in 'YYYY-MM-DD'. Defaults to today.
        status (str): Attendance status ('Present', 'Absent', etc.)
        notes_column (str | None): Name of the column in Excel to use as notes (optional)
    """
    if meeting_date is None:
        meeting_date = datetime.now().strftime("%Y-%m-%d")

    # Load Excel file
    df = pd.read_excel(file_path)

    if "Card/Fob Internal Number" not in df.columns:
        raise ValueError("Excel must have a 'Card/Fob Internal Number' column")

    added_count = 0
    skipped_count = 0

    for _, row in df.iterrows():
        card_number = str(row["Card/Fob Internal Number"]).strip()
        if not card_number:
            continue

        member = database.get_member_by_card_internal(card_number)
        if not member:
            print(f"No member found with Card/Fob Internal Number: {card_number}")
            continue

        member_id = member["id"]

        # Check if attendance for this date already exists
        existing = database.get_meeting_attendance(member_id, meeting_date)
        if existing:
            skipped_count += 1
            print(f"Skipped {member['first_name']} {member['last_name']} – already has attendance for {meeting_date}")
            continue

        # Extract notes if column is specified
        notes = str(row[notes_column]).strip() if notes_column and notes_column in df.columns else None

        database.add_meeting_attendance(member_id, meeting_date=meeting_date, status=status, notes=notes)
        added_count += 1
        print(f"Added attendance for {member['first_name']} {member['last_name']} ({card_number})")

    print(f"\nSummary: {added_count} records added, {skipped_count} skipped")
