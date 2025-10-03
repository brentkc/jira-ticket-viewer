"""
Main entry point for Jira Ticket Viewer application
"""

import tkinter as tk
from ticket_viewer import JiraTicketViewer


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = JiraTicketViewer(root)
    root.mainloop()


if __name__ == "__main__":
    main()