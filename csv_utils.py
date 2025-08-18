import csv
import database

# ----------------------------
# Export members to CSV
# ----------------------------
def export_members_to_csv(filename):
    members = database.get_all_members()
    headers = [
        "ID", "Badge Number", "Membership Type", "First Name", "Last Name",
        "Date of Birth", "Email Address", "Email Address 2", "Phone Number",
        "Address", "City", "State", "Zip Code", "Join Date",
        "Sponsor", "Card/Fob Internal Number", "Card/Fob External Number", "Deleted At"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for m in members:
            row = (
                m[0],   # ID
                m[1],   # Badge Number
                m[2],   # Membership Type
                m[3],   # First Name
                m[4],   # Last Name
                m[5],   # DOB
                m[6],   # Email
                m[13],  # Email2
                m[7],   # Phone
                m[8],   # Address
                m[9],   # City
                m[10],  # State
                m[11],  # Zip
                m[12],  # Join Date
                m[14],  # Sponsor
                m[15],  # Card Internal
                m[16],  # Card External
                m[17],  # Deleted At
            )
            writer.writerow(row)


# ----------------------------
# Import members from CSV (add new only)
# ----------------------------
def import_members_from_csv(filename):
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data = (
                row.get("Badge Number", ""),
                row.get("Membership Type", ""),
                row.get("First Name", ""),
                row.get("Last Name", ""),
                row.get("Date of Birth", ""),
                row.get("Email Address", ""),
                row.get("Phone Number", ""),
                row.get("Address", ""),
                row.get("City", ""),
                row.get("State", ""),
                row.get("Zip Code", ""),
                row.get("Join Date", ""),
                row.get("Email Address 2", ""),
                row.get("Sponsor", ""),
                row.get("Card/Fob Internal Number", ""),
                row.get("Card/Fob External Number", ""),
            )
            database.add_member(data)


# ----------------------------
# Import with overwrite/update by Badge Number
# ----------------------------
def import_members_from_csv_overwrite(filename):
    with open(filename, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            badge = row.get("Badge Number", "").strip()
            if not badge:
                continue  # skip rows with no badge number

            # Check if member exists by badge number
            conn = database.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT id FROM members WHERE badge_number = ?", (badge,))
            existing = cur.fetchone()
            conn.close()

            if existing:
                # Update existing
                member_id = existing[0]
                data = (
                    badge,
                    row.get("Membership Type", ""),
                    row.get("First Name", ""),
                    row.get("Last Name", ""),
                    row.get("Date of Birth", ""),
                    row.get("Email Address", ""),
                    row.get("Phone Number", ""),
                    row.get("Address", ""),
                    row.get("City", ""),
                    row.get("State", ""),
                    row.get("Zip Code", ""),
                    row.get("Join Date", ""),
                    row.get("Email Address 2", ""),
                    row.get("Sponsor", ""),
                    row.get("Card/Fob Internal Number", ""),
                    row.get("Card/Fob External Number", ""),
                )
                database.update_member(member_id, data)
            else:
                # Insert new
                data = (
                    badge,
                    row.get("Membership Type", ""),
                    row.get("First Name", ""),
                    row.get("Last Name", ""),
                    row.get("Date of Birth", ""),
                    row.get("Email Address", ""),
                    row.get("Phone Number", ""),
                    row.get("Address", ""),
                    row.get("City", ""),
                    row.get("State", ""),
                    row.get("Zip Code", ""),
                    row.get("Join Date", ""),
                    row.get("Email Address 2", ""),
                    row.get("Sponsor", ""),
                    row.get("Card/Fob Internal Number", ""),
                    row.get("Card/Fob External Number", ""),
                )
                database.add_member(data)
