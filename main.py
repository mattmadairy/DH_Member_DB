# main.py
import tkinter as tk
from gui import MemberApp

def main():
    root = tk.Tk()
    app = MemberApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
