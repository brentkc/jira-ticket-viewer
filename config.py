"""
Configuration constants and settings for Jira Ticket Viewer
"""

# Jira Configuration - Credentials now stored securely in Windows Credential Manager
JIRA_URL = "https://zsoftware.atlassian.net"
API_TOKEN = ""  # Loaded from secure storage
PROJECT_KEY = "ITS"

# Issue Types - VERIFIED from discovery
ISSUE_TYPES = {
    "[System] Incident": "11395",
    "[System] Service request": "11396"
}

# Default User Configuration - Email now loaded from secure settings
DEFAULT_EMAIL = ""  # Loaded from secure storage

# Default Quick Mentions (name, email tuples)
DEFAULT_QUICK_MENTIONS = [
    ("Will Sessions", "will.sessions@medemgroup.com"),
]

# File Configuration
QUICK_MENTIONS_FILE = "jira_quick_mentions.json"

# UI Configuration
WINDOW_GEOMETRY = "1400x900"
WINDOW_TITLE = "Jira Ticket Viewer"

# Dark Mode Theme Colors
THEME_COLORS = {
    'bg_primary': '#1e1e1e',
    'bg_secondary': '#2d2d2d', 
    'bg_input': '#3c3c3c',
    'bg_button': '#0d7377',
    'bg_button_hover': '#14a085',
    'bg_surface': '#252526',
    'border': '#404040',
    'text_primary': '#ffffff',
    'text_secondary': '#cccccc',
    'accent': '#00d4aa'
}

# Tree View Columns Configuration
TREE_COLUMNS = {
    "Key": {"width": 80, "minwidth": 80},
    "Type": {"width": 120, "minwidth": 100},
    "Summary": {"width": 250, "minwidth": 200},
    "Status": {"width": 100, "minwidth": 80},
    "Priority": {"width": 80, "minwidth": 80},
    "Reporter": {"width": 120, "minwidth": 100},
    "Assignee": {"width": 120, "minwidth": 100},
    "Created": {"width": 100, "minwidth": 100}
}

# Filter Options
TICKET_FILTER_OPTIONS = ["All Tickets", "My Tickets", "Unassigned"]
ISSUE_TYPE_FILTER_OPTIONS = ["All"] + list(ISSUE_TYPES.keys())

# File Types for Attachments
ATTACHMENT_FILE_TYPES = [
    ("All files", "*.*"),
    ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
    ("Documents", "*.pdf *.doc *.docx *.txt"),
    ("Spreadsheets", "*.csv *.xlsx *.xls"),
    ("Archives", "*.zip *.rar *.7z")
]

# UI Messages
UI_MESSAGES = {
    'ready': "Ready - Click 'Load All Tickets' to start",
    'loading': "Loading tickets...",
    'no_ticket_selected': "Please select a ticket first",
    'email_required': "Please enter your email address"
}

# Button Styling
BUTTON_PADDING = (12, 8)
BUTTON_EMOJIS = {
    'dashboard': "📊",
    'attachment': "📎"
}