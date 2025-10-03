"""
Main GUI class for Jira Ticket Viewer - Refactored version
"""

import tkinter as tk
from tkinter import ttk
from config import (WINDOW_TITLE, WINDOW_GEOMETRY, THEME_COLORS, DEFAULT_EMAIL, 
                   TREE_COLUMNS, TICKET_FILTER_OPTIONS, ISSUE_TYPE_FILTER_OPTIONS)
from jira_api import JiraAPIClient
from utils import load_quick_mentions, save_quick_mentions


class JiraTicketViewer:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_GEOMETRY)
        
        # Initialize state
        self.all_tickets = []
        self.current_ticket = None
        self.quick_mentions = load_quick_mentions()
        
        # Configure dark mode
        self.setup_dark_mode()
        
        # Initialize API client
        self.api_client = JiraAPIClient(
            email_callback=self.get_user_email,
            status_callback=self.update_status
        )
        
        # Setup UI
        self.setup_ui()
    
    def setup_dark_mode(self):
        """Configure modern dark mode for the application"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Get colors from config
        colors = THEME_COLORS
        
        # Configure components
        style.configure('TFrame', background=colors['bg_primary'])
        style.configure('TLabel', background=colors['bg_primary'], foreground=colors['text_primary'])
        
        style.configure('TButton', 
                       background=colors['bg_button'], 
                       foreground=colors['text_primary'],
                       borderwidth=0, 
                       focuscolor='none', 
                       relief='flat',
                       padding=(12, 8))
        style.map('TButton', 
                 background=[('active', colors['bg_button_hover']), ('pressed', colors['bg_button_hover'])])
        
        style.configure('TEntry', 
                       background=colors['bg_input'], 
                       foreground=colors['text_primary'],
                       borderwidth=1, 
                       insertcolor=colors['text_primary'], 
                       relief='flat',
                       bordercolor=colors['border'],
                       fieldbackground=colors['bg_input'])
        style.map('TEntry', 
                 bordercolor=[('focus', colors['accent'])],
                 fieldbackground=[('focus', colors['bg_input'])],
                 foreground=[('focus', colors['text_primary']), ('!focus', colors['text_primary'])])
        
        # Additional styling for other components...
        self.root.configure(bg=colors['bg_primary'])
    
    def setup_ui(self):
        """Setup the main user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Email configuration
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="5")
        config_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(config_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.email_entry = ttk.Entry(config_frame, width=30)
        self.email_entry.insert(0, DEFAULT_EMAIL)
        self.email_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.load_all_btn = ttk.Button(button_frame, text="Load All Tickets", 
                                      command=self.load_all_tickets_threaded)
        self.load_all_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.dashboard_btn = ttk.Button(button_frame, text="Dashboard", 
                                       command=self.open_dashboard)
        self.dashboard_btn.grid(row=0, column=1, padx=(0, 5))
        
        # Tickets treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        columns = list(TREE_COLUMNS.keys())
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        for col, config in TREE_COLUMNS.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=config["width"], minwidth=config["minwidth"])
        
        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready - Click 'Load All Tickets' to start")
        self.status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
    
    def get_user_email(self):
        """Get user email for API client"""
        return self.email_entry.get()
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
    
    def load_all_tickets_threaded(self):
        """Load tickets in background thread"""
        import threading
        self.load_all_btn.config(state="disabled")
        self.update_status("Loading tickets...")
        threading.Thread(target=self.load_all_tickets, daemon=True).start()
    
    def load_all_tickets(self):
        """Load all tickets using API client"""
        data = self.api_client.load_all_tickets()
        
        if data and 'issues' in data:
            self.root.after(0, self.update_ticket_list, data['issues'])
            self.root.after(0, lambda: self.update_status(f"Loaded {len(data['issues'])} tickets"))
        else:
            self.root.after(0, lambda: self.update_status("Failed to load tickets"))
        
        self.root.after(0, lambda: self.load_all_btn.config(state="normal"))
    
    def update_ticket_list(self, issues):
        """Update the treeview with ticket data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Store tickets
        self.all_tickets = issues
        
        # Add tickets to treeview
        for issue in issues:
            fields = issue.get('fields', {})
            
            # Extract data safely
            key = issue.get('key', '')
            issue_type = fields.get('issuetype', {}).get('name', '')
            summary = fields.get('summary', '')
            status = fields.get('status', {}).get('name', '')
            priority = fields.get('priority', {}).get('name', '') if fields.get('priority') else ''
            reporter = fields.get('reporter', {}).get('displayName', '') if fields.get('reporter') else ''
            assignee = fields.get('assignee', {}).get('displayName', '') if fields.get('assignee') else 'Unassigned'
            created = fields.get('created', '')[:10] if fields.get('created') else ''  # Just the date part
            
            self.tree.insert('', 'end', values=(key, issue_type, summary[:50], status, 
                                              priority, reporter, assignee, created))
    
    def open_dashboard(self):
        """Open Jira dashboard"""
        self.api_client.open_dashboard()