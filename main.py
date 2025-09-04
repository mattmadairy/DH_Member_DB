import tkinter as tk
from gui import MemberApp
import os

def main():
    root = tk.Tk()

    # Path to multi-size .ico
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "Club_logo.ico")

    # Set taskbar icon before anything else
    try:
        root.iconbitmap(ico_path)
    except Exception as e:
        print(f"Failed to set .ico icon: {e}")

    app = MemberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

