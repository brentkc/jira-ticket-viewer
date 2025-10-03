import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import requests
import json
from requests.auth import HTTPBasicAuth
import threading
from datetime import datetime
import base64
import os
from PIL import Image, ImageTk
import io
import webbrowser
import re

class JiraTicketViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Jira Ticket Viewer")
        self.root.geometry("1800x1200")
        
        # Set minimum window size for better user experience
        self.root.minsize(1400, 900)
        
        # Initialize state variables
        self.selected_ticket = None
        self.context_toolbar_visible = False
        
        # Configure dark mode
        self.setup_dark_mode()
        
        # Jira configuration - EXACT values from discovery
        self.jira_url = "https://zsoftware.atlassian.net"
        self.api_token = ""  # SECURITY: Credentials removed - use JiraTicketGUI_enhanced.py instead
        self.project_key = "ITS"
        
        # VERIFIED issue types from discovery - FILTERED to only Incident and Service request
        self.issue_types = {
            "[System] Incident": "11395",
            "[System] Service request": "11396"
        }
        
        self.setup_ui()
        
        # Auto-load tickets on startup
        self.root.after(1000, self.load_all_tickets_threaded)
    
    def is_sla_missed(self, issue):
        """Check if a ticket has missed its SLA window"""
        fields = issue.get('fields', {})
        created = fields.get('created', '')
        status = fields.get('status', {})
        status_name = status.get('name', '').lower() if status else ''
        priority = fields.get('priority', {})
        priority_name = priority.get('name', '').lower() if priority else ''
        
        # Don't highlight completed tickets
        completed_statuses = ['done', 'closed', 'resolved', 'complete', 'completed', 'finished']
        if any(comp_status in status_name for comp_status in completed_statuses):
            return False
        
        if not created:
            return False
            
        try:
            created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
            now = datetime.now(created_dt.tzinfo)
            hours_since_created = (now - created_dt).total_seconds() / 3600
            
            # Define SLA windows based on priority (in hours)
            sla_windows = {
                'critical': 2,
                'high': 8,
                'medium': 24,
                'low': 72
            }
            
            # Default to 24 hours if priority not found
            sla_window = sla_windows.get(priority_name, 24)
            
            return hours_since_created > sla_window
        except:
            return False
        
    def setup_dark_mode(self):
        """Configure modern dark mode for the application"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern dark theme colors - Enhanced palette
        bg_primary = '#1a1a1a'
        bg_secondary = '#242424'
        bg_input = '#2d2d2d'
        bg_button = '#0078d4'
        bg_button_hover = '#106ebe'
        bg_surface = '#1f1f1f'
        border = '#404040'
        text_primary = '#ffffff'
        text_secondary = '#cccccc'
        accent = '#0078d4'
        success = '#107c10'
        warning = '#ff8c00'
        danger = '#d13438'
        
        # Configure components
        style.configure('TFrame', background=bg_primary)
        style.configure('TLabel', background=bg_primary, foreground=text_primary)
        
        style.configure('TButton', 
                       background=bg_button, 
                       foreground=text_primary,
                       borderwidth=0, 
                       focuscolor='none', 
                       relief='flat',
                       padding=(12, 8))
        style.map('TButton', 
                 background=[('active', bg_button_hover), ('pressed', bg_button_hover)])
        
        style.configure('TEntry', 
                       background=bg_input, 
                       foreground=text_primary,
                       borderwidth=1, 
                       insertcolor=text_primary, 
                       relief='flat',
                       bordercolor=border,
                       fieldbackground=bg_input)
        style.map('TEntry', 
                 bordercolor=[('focus', accent)],
                 fieldbackground=[('focus', bg_input)],
                 foreground=[('focus', text_primary), ('!focus', text_primary)])
        
        style.configure('TCombobox', 
                       background=bg_input, 
                       foreground=text_primary,
                       borderwidth=1, 
                       arrowcolor=text_primary, 
                       relief='flat',
                       bordercolor=border,
                       fieldbackground=bg_input,
                       selectbackground=bg_input,
                       selectforeground=text_primary)
        style.map('TCombobox', 
                 background=[('readonly', bg_input)],
                 fieldbackground=[('readonly', bg_input)],
                 foreground=[('readonly', text_primary)],
                 bordercolor=[('focus', accent)])
        
        style.configure('TLabelFrame', 
                       background=bg_primary, 
                       foreground=text_primary,
                       borderwidth=1, 
                       relief='solid', 
                       bordercolor=border)
        style.configure('TLabelFrame.Label', 
                       background=bg_primary, 
                       foreground=text_primary)
        
        style.configure('TCheckbutton', 
                       background=bg_primary, 
                       foreground=text_primary,
                       focuscolor='none')
        
        style.configure('Treeview', 
                       background=bg_surface, 
                       foreground=text_primary,
                       fieldbackground=bg_surface, 
                       borderwidth=0, 
                       relief='flat')
        style.configure('Treeview.Heading', 
                       background=bg_secondary, 
                       foreground=text_primary,
                       borderwidth=1, 
                       relief='flat',
                       bordercolor=border)
        style.map('Treeview', 
                 background=[('selected', accent)],
                 foreground=[('selected', text_primary)])
        style.map('Treeview.Heading',
                 background=[('active', bg_button)])
        
        style.configure('Vertical.TScrollbar', 
                       background=bg_secondary, 
                       troughcolor=bg_primary, 
                       borderwidth=0, 
                       arrowcolor=text_secondary)
        
        style.configure('TNotebook', 
                       background=bg_primary, 
                       borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background=bg_secondary, 
                       foreground=text_primary,
                       padding=[16, 10], 
                       borderwidth=0)
        style.map('TNotebook.Tab',
                 background=[('selected', bg_button), ('active', bg_button_hover)])
        
        self.root.configure(bg=bg_primary)
        
    def setup_ui(self):
        # Main container with minimal padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Top toolbar with primary actions
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Left side - Search (most common action)
        search_container = ttk.Frame(toolbar_frame)
        search_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.search_entry = ttk.Entry(search_container, width=40, font=('Segoe UI', 11))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<Return>', self.search_tickets)
        self.search_entry.insert(0, "🔍 Search tickets...")
        self.search_entry.bind('<FocusIn>', self.on_search_focus)
        self.search_entry.bind('<FocusOut>', self.on_search_unfocus)
        
        # Right side - Primary actions
        primary_actions = ttk.Frame(toolbar_frame)
        primary_actions.pack(side=tk.RIGHT)
        
        self.create_ticket_btn = ttk.Button(primary_actions, text="➕ New Ticket", command=self.open_create_ticket_window)
        self.create_ticket_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.dashboard_btn = ttk.Button(primary_actions, text="📊 Dashboard", command=self.open_dashboard)
        self.dashboard_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Smart filters bar (simplified)
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # User context (auto-detect)
        ttk.Label(filter_frame, text="Show:").pack(side=tk.LEFT, padx=(0, 5))
        self.ticket_filter_var = tk.StringVar(value="My Tickets")
        self.ticket_filter_combo = ttk.Combobox(filter_frame, textvariable=self.ticket_filter_var, width=15,
                                               values=["My Tickets", "All Open", "Unassigned", "All Tickets"])
        self.ticket_filter_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.ticket_filter_combo.bind("<<ComboboxSelected>>", self.filter_tickets)
        
        # Priority filter
        ttk.Label(filter_frame, text="Priority:").pack(side=tk.LEFT, padx=(0, 5))
        self.priority_filter_var = tk.StringVar(value="All")
        self.priority_filter_combo = ttk.Combobox(filter_frame, textvariable=self.priority_filter_var, width=12,
                                                values=["All", "Critical", "High", "Medium", "Low"])
        self.priority_filter_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.priority_filter_combo.bind("<<ComboboxSelected>>", self.filter_tickets)
        
        # Smart toggle
        self.hide_completed_var = tk.BooleanVar(value=True)
        self.hide_completed_cb = ttk.Checkbutton(filter_frame, text="Hide Completed", 
                                               variable=self.hide_completed_var, command=self.filter_tickets)
        self.hide_completed_cb.pack(side=tk.LEFT, padx=(15, 0))
        
        # Auto-fill user email
        self.user_email = "brent@medemgroup.com"
        
        # Status indicator (replaces multiple buttons)
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.status_label = ttk.Label(status_frame, text="Ready to load tickets...", font=('Segoe UI', 9))
        self.status_label.pack(side=tk.LEFT)
        
        self.refresh_btn = ttk.Button(status_frame, text="🔄", width=3, command=self.load_all_tickets_threaded)
        self.refresh_btn.pack(side=tk.RIGHT)
        
        # Main content area - two column layout
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        content_frame.columnconfigure(0, weight=2)  # Tickets list gets more space
        content_frame.columnconfigure(1, weight=1)  # Details panel
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - Tickets list (larger)
        tickets_frame = ttk.Frame(content_frame)
        tickets_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        tickets_frame.rowconfigure(0, weight=1)
        tickets_frame.columnconfigure(0, weight=1)
        
        # Optimized columns for better scanning
        columns = ("Key", "Priority", "Summary", "Status", "Assignee", "Age")
        self.tree = ttk.Treeview(tickets_frame, columns=columns, show="headings", height=20)
        
        # Configure column headings and widths
        self.tree.heading("Key", text="Key", command=lambda: self.sort_treeview("Key", False))
        self.tree.column("Key", width=80, minwidth=80)
        
        self.tree.heading("Type", text="Type")
        self.tree.column("Type", width=120, minwidth=100)
        
        self.tree.heading("Summary", text="Summary")
        self.tree.column("Summary", width=250, minwidth=200)
        
        self.tree.heading("Status", text="Status", command=lambda: self.sort_treeview("Status", False))
        self.tree.column("Status", width=100, minwidth=80)
        
        self.tree.heading("Priority", text="Priority")
        self.tree.column("Priority", width=80, minwidth=80)
        
        self.tree.heading("Reporter", text="Reporter")
        self.tree.column("Reporter", width=120, minwidth=100)
        
        self.tree.heading("Assignee", text="Assignee")
        self.tree.column("Assignee", width=120, minwidth=100)
        
        self.tree.heading("Created", text="Created", command=lambda: self.sort_treeview("Created", False))
        self.tree.column("Created", width=100, minwidth=100)
        
        # Track sort order for each column
        self.sort_reverse = {}
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure tags for SLA highlighting
        self.tree.tag_configure('sla_missed', background='#4a2828', foreground='#ff9999')
        
        # Right panel for ticket details and actions
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=4, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Ticket details frame with modern styling
        details_frame = ttk.LabelFrame(right_panel, text="📋 Ticket Details", padding="15")
        details_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.details_text = scrolledtext.ScrolledText(details_frame, width=40, height=8, wrap=tk.WORD,
                                                    bg='#2d2d2d', fg='#ffffff', insertbackground='#ffffff',
                                                    font=('Segoe UI', 10))
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu for details text
        self.create_text_context_menu(self.details_text)
        
        # Add drag-drop zone for file attachments with modern styling
        drop_frame = ttk.LabelFrame(right_panel, text="📎 Drag & Drop Files Here to Attach", padding="15")
        drop_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.drop_label = ttk.Label(drop_frame, text="📎 Drop files here or click to browse", 
                                   font=('Segoe UI', 10), cursor="hand2")
        self.drop_label.pack(pady=10)
        
        # Bind drag and drop events
        self.drop_label.bind("<Button-1>", self.browse_files_to_attach)
        
        # Enable drag and drop on the entire window for file attachments
        self.setup_drag_drop()
        
        # Actions frame
        actions_frame = ttk.LabelFrame(right_panel, text="\u26a1 Quick Actions", padding="15")
        actions_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Action buttons
        button_row = ttk.Frame(actions_frame)
        button_row.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.close_btn = ttk.Button(button_row, text="❌ Close Ticket", command=self.close_ticket, state="disabled")
        self.close_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.resolve_btn = ttk.Button(button_row, text="✅ Resolve", command=self.resolve_ticket, state="disabled")
        self.resolve_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.open_btn = ttk.Button(button_row, text="🔓 Mark Open", command=self.open_ticket, state="disabled")
        self.open_btn.grid(row=0, column=2, padx=(0, 5))
        
        self.view_attachments_btn = ttk.Button(button_row, text="🖼️ View Images", command=self.view_attachments, state="disabled")
        self.view_attachments_btn.grid(row=0, column=3, padx=(5, 0))
        
        self.paste_screenshot_btn = ttk.Button(button_row, text="Paste Screenshot", command=self.paste_screenshot, state="disabled")
        self.paste_screenshot_btn.grid(row=0, column=3, padx=(5, 0))
        
        self.assign_to_me_btn = ttk.Button(button_row, text="👤 Assign to Me", command=self.assign_to_me, state="disabled")
        self.assign_to_me_btn.grid(row=0, column=4, padx=(5, 0))
        
        # Comment section
        ttk.Label(actions_frame, text="Add Comment (use @username to tag people):").grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        
        # Frame for comment text and autocomplete
        comment_frame = ttk.Frame(actions_frame)
        comment_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.comment_text = scrolledtext.ScrolledText(comment_frame, width=40, height=4,
                                                    bg='#3c3c3c', fg='#ffffff', insertbackground='#ffffff')
        self.comment_text.pack(fill=tk.BOTH, expand=True)
        
        # Bind for @mention autocomplete
        self.comment_text.bind('<KeyRelease>', self.on_comment_key_release)
        
        # Autocomplete listbox (initially hidden)
        self.autocomplete_frame = tk.Frame(actions_frame, bg='#2d2d2d', highlightthickness=1, highlightbackground='#404040')
        self.autocomplete_listbox = tk.Listbox(self.autocomplete_frame, bg='#2d2d2d', fg='#ffffff', 
                                              selectbackground='#0d7377', height=5)
        self.autocomplete_listbox.pack(fill=tk.BOTH, expand=True)
        self.autocomplete_listbox.bind('<Double-1>', self.on_autocomplete_select)
        self.autocomplete_listbox.bind('<Return>', self.on_autocomplete_select)
        self.autocomplete_frame.grid_forget()  # Hide initially
        
        # Store for autocomplete
        self.available_users = []
        self.autocomplete_active = False
        self.mention_start_pos = None
        
        # Quick mention buttons
        mention_frame = ttk.LabelFrame(actions_frame, text="Quick Mentions", padding="5")
        mention_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Control buttons row
        control_row = ttk.Frame(mention_frame)
        control_row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.manage_mentions_btn = ttk.Button(control_row, text="➕ Add/Remove", 
                                             command=self.manage_quick_mentions)
        self.manage_mentions_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.get_users_btn = ttk.Button(control_row, text="Get Team List", command=self.get_team_members)
        self.get_users_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Frame for dynamic quick mention buttons
        self.quick_mentions_frame = ttk.Frame(mention_frame)
        self.quick_mentions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Default quick mentions (stored as list of tuples: (name, email))
        self.quick_mentions = [
            ("Will Sessions", "will.sessions@medemgroup.com"),
        ]
        
        # Load saved quick mentions from file if exists
        self.load_quick_mentions()
        
        # Create buttons for quick mentions
        self.refresh_quick_mention_buttons()
        
        # Submit button
        self.submit_btn = ttk.Button(actions_frame, text="💬 Add Comment", command=self.add_comment, state="disabled")
        self.submit_btn.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        # Comments history
        comments_frame = ttk.LabelFrame(right_panel, text="Recent Comments", padding="5")
        comments_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.comments_text = scrolledtext.ScrolledText(comments_frame, width=40, height=6,
                                                     bg='#3c3c3c', fg='#ffffff', insertbackground='#ffffff')
        self.comments_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu for comments text
        self.create_text_context_menu(self.comments_text)
        
        # Bind treeview selection and double-click
        self.tree.bind("<<TreeviewSelect>>", self.on_ticket_select)
        self.tree.bind("<Double-1>", self.on_ticket_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)  # Right-click for context menu
        
        # Create context menu for right-click
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Assign to Me", command=self.assign_to_me)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Ticket URL", command=self.copy_ticket_url)
        self.context_menu.add_command(label="Open in Browser", command=self.open_ticket_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Ticket Key", command=self.copy_ticket_key)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Ready - Click 'Load All Tickets' to start")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)  # Changed from 3 to 4
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(3, weight=1)  # Changed from 2 to 3
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        actions_frame.columnconfigure(0, weight=1)
        comments_frame.columnconfigure(0, weight=1)
        comments_frame.rowconfigure(0, weight=1)
        
        # Store all tickets for filtering
        self.all_tickets = []
        self.current_ticket = None
        self.html_viewer_window = None
        
        # Initialize quick mentions file path
        self.quick_mentions_file = "jira_quick_mentions.json"
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality for main window"""
        try:
            from tkinterdnd2 import DND_FILES
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop_files)
        except ImportError:
            # If tkinterdnd2 not available, use alternative method
            pass  # Will use browse button instead
    
    def browse_files_to_attach(self, event=None):
        """Browse for files to attach to current ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        file_paths = filedialog.askopenfilenames(
            title="Select files to attach",
            filetypes=[
                ("All files", "*.*"),
                ("Images", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Documents", "*.pdf *.doc *.docx *.txt"),
                ("Spreadsheets", "*.csv *.xlsx *.xls"),
                ("Archives", "*.zip *.rar *.7z")
            ]
        )
        
        for file_path in file_paths:
            self.attach_file_to_ticket(file_path)
        
    def make_jira_request(self, endpoint, method="GET", params=None, data=None, files=None):
        """Make authenticated request to Jira API - FIXED version"""
        if not self.email_entry.get().strip():
            messagebox.showerror("Error", "Please enter your email address")
            return None
            
        url = f"{self.jira_url}/rest/api/2/{endpoint}"
        auth = HTTPBasicAuth(self.email_entry.get().strip(), self.api_token)
        headers = {"Accept": "application/json"}
        
        if method in ["POST", "PUT"] and not files:
            headers["Content-Type"] = "application/json"
        
        try:
            # Make the request based on method
            if method == "GET":
                response = requests.get(url, auth=auth, headers=headers, params=params)
            elif method == "POST":
                if files:
                    response = requests.post(url, auth=auth, files=files, data=data)
                else:
                    response = requests.post(url, auth=auth, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, auth=auth, headers=headers, json=data)
            else:
                messagebox.showerror("Error", f"Unsupported HTTP method: {method}")
                return None
            
            # Check response
            response.raise_for_status()
            
            # Return JSON or success indicator
            if response.text.strip():
                return response.json()
            else:
                return {"success": True}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"API Error: {str(e)}"
            if 'response' in locals() and response:
                error_msg += f"\nStatus: {response.status_code}"
                if response.text:
                    error_msg += f"\nResponse: {response.text[:500]}"
            messagebox.showerror("API Error", error_msg)
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
            return None
    
    def open_dashboard(self):
        """Open the Jira Service Desk dashboard in browser"""
        dashboard_url = f"{self.jira_url}/jira/servicedesk/projects/{self.project_key}/summary"
        webbrowser.open(dashboard_url)
        self.status_label.config(text=f"Opened dashboard for project {self.project_key}")
    
    def load_all_tickets_threaded(self):
        """Load all project tickets in a separate thread"""
        self.load_all_btn.config(state="disabled")
        self.status_label.config(text="Loading all project tickets...")
        threading.Thread(target=self.load_all_tickets, daemon=True).start()
    
    def load_all_tickets(self):
        """Load all tickets in the project - using VERIFIED working approach"""
        # Build JQL to filter only Incident and Service request tickets
        issue_type_ids = list(self.issue_types.values())  # ["11395", "11396"]
        jql = f'project = ITS AND issuetype in ({",".join(issue_type_ids)})'
        
        params = {
            'jql': jql,
            'maxResults': 100,
            'startAt': 0
            # NO fields parameter - get everything by default
        }
        
        data = self.make_jira_request("search", params=params)
        
        if data and 'issues' in data:
            self.root.after(0, self.update_ticket_list, data['issues'])
            self.root.after(0, lambda: self.status_label.config(text=f"Loaded {len(data['issues'])} tickets (Incidents & Service Requests only)"))
        else:
            self.root.after(0, lambda: self.status_label.config(text="Failed to load tickets"))
        
        self.root.after(0, lambda: self.load_all_btn.config(state="normal"))
        
        # Apply default filter after loading
        self.root.after(100, self.filter_tickets)
    
    def update_ticket_list(self, issues):
        """Update the treeview with ticket data"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Store tickets for filtering
        self.all_tickets = issues
        
        # Add tickets to treeview
        for issue in issues:
            fields = issue.get('fields', {})
            
            # Extract data safely - handle missing fields
            key = issue.get('key', 'Unknown')
            
            issue_type = fields.get('issuetype', {})
            type_name = issue_type.get('name', 'Unknown') if issue_type else 'Unknown'
            
            summary = fields.get('summary', 'No summary')
            
            status = fields.get('status', {})
            status_name = status.get('name', 'Unknown') if status else 'Unknown'
            
            priority = fields.get('priority', {})
            priority_name = priority.get('name', 'Unknown') if priority else 'Unknown'
            
            reporter = fields.get('reporter')
            reporter_name = reporter.get('displayName', 'Unknown') if reporter else 'Unknown'
            
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            
            # Format created date
            created = fields.get('created', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    created_str = dt.strftime('%Y-%m-%d')
                except:
                    created_str = created[:10] if len(created) >= 10 else created
            else:
                created_str = 'Unknown'
            
            values = (key, type_name, summary, status_name, priority_name, reporter_name, assignee_name, created_str)
            # Determine tags for this ticket
            tags = [key]
            if self.is_sla_missed(issue):
                tags.append('sla_missed')
            
            self.tree.insert("", "end", values=values, tags=tags)
    
    def filter_tickets(self, event=None):
        """Filter tickets based on selected criteria - with persistent hide completed"""
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        ticket_filter = self.ticket_filter_var.get()
        issue_type_filter = self.issue_type_var.get()
        hide_completed = self.hide_completed_var.get()
        user_email = self.email_entry.get().strip()
        
        # Define completed status names
        completed_statuses = ['done', 'closed', 'resolved', 'complete', 'completed', 'finished']
        
        tickets_to_show = []
        for issue in self.all_tickets:
            fields = issue.get('fields', {})
            
            # Filter by ticket ownership
            if ticket_filter == "My Tickets":
                # Check if user is reporter OR assignee
                reporter = fields.get('reporter')
                reporter_email = reporter.get('emailAddress', '') if reporter else ''
                
                assignee = fields.get('assignee')
                assignee_email = assignee.get('emailAddress', '') if assignee else ''
                
                if user_email not in [reporter_email, assignee_email]:
                    continue
            elif ticket_filter == "Unassigned":
                assignee = fields.get('assignee')
                if assignee:  # Skip if has assignee
                    continue
            
            # Check issue type filter
            if issue_type_filter != "All":
                issue_type = fields.get('issuetype', {})
                type_name = issue_type.get('name', '') if issue_type else ''
                if type_name != issue_type_filter:
                    continue
            
            # Check completed status filter - PERSISTENT - FIXED LOGIC
            if hide_completed:
                status = fields.get('status', {})
                status_name = status.get('name', '').lower() if status else ''
                # Fix: Check if any completed status is IN the status name
                is_completed = any(completed_status in status_name for completed_status in completed_statuses)
                if is_completed:
                    continue
            
            tickets_to_show.append(issue)
        
        # Update display with filtered results
        self.update_ticket_list(tickets_to_show)
        
        # Update status message
        filter_text = f" ({ticket_filter})" if ticket_filter != "All Tickets" else ""
        type_text = f" ({issue_type_filter})" if issue_type_filter != "All" else ""
        completed_text = " (hiding completed)" if hide_completed else ""
        self.status_label.config(text=f"Showing {len(tickets_to_show)} tickets{filter_text}{type_text}{completed_text}")
        
        # Store filtered tickets for HTML viewer
        self.filtered_tickets = tickets_to_show
    
    def on_ticket_select(self, event):
        """Handle ticket selection in treeview - OPTIMIZED"""
        selection = self.tree.selection()
        if not selection:
            self.current_ticket = None
            self.close_btn.config(state="disabled")
            self.resolve_btn.config(state="disabled")
            self.open_btn.config(state="disabled")
            self.submit_btn.config(state="disabled")
            self.view_attachments_btn.config(state="disabled")
            self.paste_screenshot_btn.config(state="disabled")
            self.assign_to_me_btn.config(state="disabled")
            return
            
        item = selection[0]
        ticket_key = self.tree.item(item)['values'][0]
        
        # Find the full ticket data
        for issue in self.all_tickets:
            if issue.get('key') == ticket_key:
                self.current_ticket = issue
                # Show details immediately with cached data
                self.show_ticket_details_fast(issue)
                # Load full details in background
                threading.Thread(target=self.load_full_ticket_details, args=(ticket_key,), daemon=True).start()
                break
    
    def show_ticket_details_fast(self, issue):
        """Show ticket details immediately using cached data"""
        fields = issue.get('fields', {})
        
        # Build details string safely - same as before but faster
        details = f"Key: {issue.get('key', 'Unknown')}\n"
        
        issue_type = fields.get('issuetype', {})
        details += f"Type: {issue_type.get('name', 'Unknown') if issue_type else 'Unknown'}\n"
        
        details += f"Summary: {fields.get('summary', 'No summary')}\n"
        
        status = fields.get('status', {})
        status_name = status.get('name', 'Unknown') if status else 'Unknown'
        details += f"Status: {status_name}\n"
        
        priority = fields.get('priority', {})
        details += f"Priority: {priority.get('name', 'Unknown') if priority else 'Unknown'}\n"
        
        reporter = fields.get('reporter')
        details += f"Reporter: {reporter.get('displayName', 'Unknown') if reporter else 'Unknown'}\n"
        
        assignee = fields.get('assignee')
        details += f"Assignee: {assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'}\n"
        
        created = fields.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                details += f"Created: {dt.strftime('%Y-%m-%d %H:%M')}\n"
            except:
                details += f"Created: {created}\n"
        
        # Add attachment count
        attachments = fields.get('attachment', [])
        if attachments:
            details += f"\n📎 Attachments: {len(attachments)} file(s)\n"
            for att in attachments[:5]:  # Show first 5 attachments
                details += f"  • {att.get('filename', 'Unknown')}\n"
            if len(attachments) > 5:
                details += f"  ... and {len(attachments) - 5} more\n"
        
        details += f"\nDescription:\n"
        description = fields.get('description', 'No description')
        details += description if description else 'No description'
        
        # Update details text widget immediately
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
        
        # Update attachment button text
        if attachments:
            self.view_attachments_btn.config(text=f"View Files ({len(attachments)})")
        else:
            self.view_attachments_btn.config(text="View Images")
        
        # Show "Loading comments..." in comments section
        self.comments_text.delete(1.0, tk.END)
        self.comments_text.insert(1.0, "Loading comments...")
        
        # Enable contextual actions
        self.enable_all_actions()
    
    def load_full_ticket_details(self, ticket_key):
        """Load comments and update HTML viewer in background"""
        # Load comments
        comments_data = self.make_jira_request(f"issue/{ticket_key}/comment")
        
        # Update comments on UI thread
        def update_comments():
            self.comments_text.delete(1.0, tk.END)
            
            if comments_data and 'comments' in comments_data:
                comments = comments_data['comments'][-5:]  # Last 5 comments
                
                if comments:
                    for comment in comments:
                        author = comment.get('author', {})
                        author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                        created = comment.get('created', '')
                        body = comment.get('body', 'No content')
                        
                        try:
                            dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            created_str = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            created_str = created[:16] if len(created) >= 16 else created
                        
                        self.comments_text.insert(tk.END, f"[{created_str}] {author_name}:\n{body}\n\n")
                else:
                    self.comments_text.insert(tk.END, "No comments yet.")
            else:
                self.comments_text.insert(tk.END, "No comments yet.")
            
            # Update HTML viewer if open
            if self.html_viewer_window and self.html_viewer_window.winfo_exists():
                self.update_html_viewer(self.current_ticket)
        
        self.root.after(0, update_comments)
    
    def show_ticket_details(self, issue):
        """Show detailed information about selected ticket"""
        fields = issue.get('fields', {})
        
        # Build details string safely
        details = f"Key: {issue.get('key', 'Unknown')}\n"
        
        issue_type = fields.get('issuetype', {})
        details += f"Type: {issue_type.get('name', 'Unknown') if issue_type else 'Unknown'}\n"
        
        details += f"Summary: {fields.get('summary', 'No summary')}\n"
        
        status = fields.get('status', {})
        status_name = status.get('name', 'Unknown') if status else 'Unknown'
        details += f"Status: {status_name}\n"
        
        priority = fields.get('priority', {})
        details += f"Priority: {priority.get('name', 'Unknown') if priority else 'Unknown'}\n"
        
        reporter = fields.get('reporter')
        details += f"Reporter: {reporter.get('displayName', 'Unknown') if reporter else 'Unknown'}\n"
        
        assignee = fields.get('assignee')
        details += f"Assignee: {assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'}\n"
        
        created = fields.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                details += f"Created: {dt.strftime('%Y-%m-%d %H:%M')}\n"
            except:
                details += f"Created: {created}\n"
        
        details += f"\nDescription:\n"
        description = fields.get('description', 'No description')
        details += description if description else 'No description'
        
        # Update details text widget
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, details)
        
        # Load comments
        self.load_comments(issue.get('key'))
        
        # Update HTML viewer if open
        if self.html_viewer_window and self.html_viewer_window.winfo_exists():
            self.update_html_viewer(issue)
        
        # Enable contextual actions
        self.enable_all_actions()
    
    def assign_to_me(self):
        """Assign the current ticket to myself - FIXED FOR JIRA CLOUD"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        ticket_key = self.current_ticket.get('key')
        my_email = self.email_entry.get().strip()
        
        def assign_ticket():
            # Get account ID for the user - REQUIRED for Jira Cloud
            user_search = self.make_jira_request("user/search", params={"query": my_email})
            
            if user_search and len(user_search) > 0:
                account_id = user_search[0].get('accountId')
                
                # Use accountId for assignment
                update_data = {
                    "fields": {
                        "assignee": {"accountId": account_id}
                    }
                }
                
                result = self.make_jira_request(f"issue/{ticket_key}", method="PUT", data=update_data)
                
                # Check if successful (empty response is OK for PUT)
                if result is not None:
                    self.root.after(0, lambda: messagebox.showinfo("Success", f"Ticket {ticket_key} assigned to you!"))
                    self.root.after(0, self.refresh_current_ticket)
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to assign ticket {ticket_key}"))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", f"User not found: {my_email}\nMake sure the email is correct and has Jira access."))
        
        # Run assignment in background thread
        threading.Thread(target=assign_ticket, daemon=True).start()
    
    def on_ticket_double_click(self, event):
        """Handle double-click on ticket - open in web browser"""
        # First select the ticket (in case it wasn't selected)
        self.on_ticket_select(event)
        
        # Open ticket in browser
        self.open_ticket_in_browser()
    
    def load_comments(self, ticket_key):
        """Load comments for the selected ticket"""
        if not ticket_key:
            return
            
        comments_data = self.make_jira_request(f"issue/{ticket_key}/comment")
        
        self.comments_text.delete(1.0, tk.END)
        
        if comments_data and 'comments' in comments_data:
            comments = comments_data['comments'][-5:]  # Last 5 comments
            
            if comments:
                for comment in comments:
                    author = comment.get('author', {})
                    author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                    created = comment.get('created', '')
                    body = comment.get('body', 'No content')
                    
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        created_str = created[:16] if len(created) >= 16 else created
                    
                    self.comments_text.insert(tk.END, f"[{created_str}] {author_name}:\n{body}\n\n")
            else:
                self.comments_text.insert(tk.END, "No comments yet.")
        else:
            self.comments_text.insert(tk.END, "No comments yet.")
    
    def close_ticket(self):
        """Close the selected ticket"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        # Get available transitions
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data or 'transitions' not in transitions_data:
            messagebox.showerror("Error", "Could not get available transitions for this ticket")
            return
        
        # Look for close/done transitions
        close_transitions = []
        for transition in transitions_data['transitions']:
            trans_name = transition['name'].lower()
            if any(keyword in trans_name for keyword in ['close', 'done', 'complete', 'resolve']):
                close_transitions.append(transition)
        
        if not close_transitions:
            available = [t['name'] for t in transitions_data['transitions']]
            messagebox.showwarning("Warning", f"No close transition available. Available transitions: {', '.join(available)}")
            return
        
        # If multiple close transitions, let user choose
        if len(close_transitions) > 1:
            transition_names = [t['name'] for t in close_transitions]
            choice = messagebox.askyesnocancel("Choose Transition", 
                f"Multiple close options available: {', '.join(transition_names)}. Use the first one ({transition_names[0]})?")
            if not choice:
                return
        
        selected_transition = close_transitions[0]
        
        # Perform the transition
        transition_data = {
            "transition": {"id": selected_transition['id']}
        }
        
        result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
        
        if result is not None:
            messagebox.showinfo("Success", f"Ticket {ticket_key} closed successfully!")
            # Refresh the ticket list
            self.load_all_tickets_threaded()
        else:
            messagebox.showerror("Error", "Failed to close ticket")
    
    def resolve_ticket(self):
        """Resolve the selected ticket"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        # Get available transitions
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data or 'transitions' not in transitions_data:
            messagebox.showerror("Error", "Could not get available transitions for this ticket")
            return
        
        # Look for resolve transitions
        resolve_transitions = []
        for transition in transitions_data['transitions']:
            trans_name = transition['name'].lower()
            if 'resolve' in trans_name:
                resolve_transitions.append(transition)
        
        if not resolve_transitions:
            available = [t['name'] for t in transitions_data['transitions']]
            messagebox.showwarning("Warning", f"No resolve transition available. Available transitions: {', '.join(available)}")
            return
        
        selected_transition = resolve_transitions[0]
        
        # Perform the transition
        transition_data = {
            "transition": {"id": selected_transition['id']}
        }
        
        result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
        
        if result is not None:
            messagebox.showinfo("Success", f"Ticket {ticket_key} resolved successfully!")
            # Refresh the ticket list
            self.load_all_tickets_threaded()
        else:
            messagebox.showerror("Error", "Failed to resolve ticket")
    
    def open_ticket(self):
        """Set the selected ticket to open status"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        # Get available transitions
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data or 'transitions' not in transitions_data:
            messagebox.showerror("Error", "Could not get available transitions for this ticket")
            return
        
        # Look for open/reopen transitions
        open_transitions = []
        for transition in transitions_data['transitions']:
            trans_name = transition['name'].lower()
            if any(keyword in trans_name for keyword in ['open', 'reopen', 'in progress', 'start']):
                open_transitions.append(transition)
        
        if not open_transitions:
            available = [t['name'] for t in transitions_data['transitions']]
            messagebox.showwarning("Warning", f"No open transition available. Available transitions: {', '.join(available)}")
            return
        
        # If multiple open transitions, let user choose
        if len(open_transitions) > 1:
            transition_names = [t['name'] for t in open_transitions]
            choice = messagebox.askyesnocancel("Choose Transition", 
                f"Multiple open options available: {', '.join(transition_names)}. Use the first one ({transition_names[0]})?")
            if not choice:
                return
        
        selected_transition = open_transitions[0]
        
        # Perform the transition
        transition_data = {
            "transition": {"id": selected_transition['id']}
        }
        
        result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
        
        if result is not None:
            messagebox.showinfo("Success", f"Ticket {ticket_key} marked as open successfully!")
            # Refresh the ticket list
            self.load_all_tickets_threaded()
        else:
            messagebox.showerror("Error", "Failed to open ticket")
    
    def view_attachments(self):
        """View images/attachments for the selected ticket with count"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        # Get attachments - first check if we already have them in current ticket data
        fields = self.current_ticket.get('fields', {})
        attachments = fields.get('attachment', [])
        
        # If no attachment field, fetch fresh data
        if not fields.get('attachment'):
            attachments_data = self.make_jira_request(f"issue/{ticket_key}")
            if attachments_data:
                attachments = attachments_data.get('fields', {}).get('attachment', [])
        
        if not attachments:
            messagebox.showinfo("No Attachments", f"Ticket {ticket_key} has no attachments")
            return
        
        # Update button text with count
        self.view_attachments_btn.config(text=f"View Files ({len(attachments)})")
        
        # Filter for image attachments
        image_attachments = []
        other_attachments = []
        
        for attachment in attachments:
            content_type = attachment.get('mimeType', '').lower()
            if content_type.startswith('image/'):
                image_attachments.append(attachment)
            else:
                other_attachments.append(attachment)
        
        # Create attachments window
        self.show_attachments_window(image_attachments, other_attachments)
    
    def show_attachments_window(self, image_attachments, other_attachments):
        """Show attachments in a new window"""
        attach_window = tk.Toplevel(self.root)
        attach_window.title("Ticket Attachments")
        attach_window.geometry("800x600")
        attach_window.configure(bg='#1e1e1e')
        attach_window.transient(self.root)
        
        main_frame = ttk.Frame(attach_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # Images tab
        if image_attachments:
            images_frame = ttk.Frame(notebook)
            notebook.add(images_frame, text=f"Images ({len(image_attachments)})")
            
            # Scrollable frame for images
            canvas = tk.Canvas(images_frame, bg='#2d2d2d', highlightthickness=0)
            scrollbar = ttk.Scrollbar(images_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Load and display images
            for i, attachment in enumerate(image_attachments):
                self.add_image_to_frame(scrollable_frame, attachment, i)
        
        # Other files tab
        if other_attachments:
            files_frame = ttk.Frame(notebook)
            notebook.add(files_frame, text=f"Files ({len(other_attachments)})")
            
            files_text = scrolledtext.ScrolledText(files_frame, wrap=tk.WORD, 
                                                 bg='#3c3c3c', fg='#ffffff', insertbackground='#ffffff')
            files_text.pack(fill=tk.BOTH, expand=True)
            
            for attachment in other_attachments:
                filename = attachment.get('filename', 'Unknown')
                size = attachment.get('size', 0)
                content_type = attachment.get('mimeType', 'Unknown')
                created = attachment.get('created', '')
                
                files_text.insert(tk.END, f"📎 {filename}\n")
                files_text.insert(tk.END, f"   Size: {self.format_file_size(size)}\n")
                files_text.insert(tk.END, f"   Type: {content_type}\n")
                files_text.insert(tk.END, f"   Date: {created[:10] if created else 'Unknown'}\n")
                files_text.insert(tk.END, f"   URL: {attachment.get('content', 'N/A')}\n\n")
        
        if not image_attachments and not other_attachments:
            no_attach_frame = ttk.Frame(notebook)
            notebook.add(no_attach_frame, text="No Attachments")
            
            ttk.Label(no_attach_frame, text="This ticket has no attachments", 
                     font=('Segoe UI', 12)).pack(expand=True)
    
    def add_image_to_frame(self, parent, attachment, index):
        """Add an image to the attachments frame"""
        image_frame = ttk.Frame(parent)
        image_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Image info
        filename = attachment.get('filename', f'Image {index+1}')
        size = attachment.get('size', 0)
        content_url = attachment.get('content', '')
        
        info_label = ttk.Label(image_frame, text=f"📷 {filename} ({self.format_file_size(size)})")
        info_label.pack(anchor=tk.W)
        
        # Download and display image button
        view_btn = ttk.Button(image_frame, text="View Image", 
                             command=lambda url=content_url: self.open_image_url(url))
        view_btn.pack(anchor=tk.W, pady=(5, 0))
        
        # Try to load thumbnail if possible
        if content_url:
            threading.Thread(target=self.load_image_thumbnail, 
                           args=(image_frame, content_url, filename), daemon=True).start()
    
    def load_image_thumbnail(self, parent, url, filename):
        """Load and display image thumbnail"""
        try:
            response = requests.get(url, auth=HTTPBasicAuth(self.email_entry.get().strip(), self.api_token))
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                
                # Create thumbnail
                image.thumbnail((300, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                # Display thumbnail
                def update_thumbnail():
                    thumbnail_label = tk.Label(parent, image=photo, bg='#2d2d2d')
                    thumbnail_label.image = photo  # Keep a reference
                    thumbnail_label.pack(pady=(5, 0))
                
                self.root.after(0, update_thumbnail)
        except Exception as e:
            print(f"Failed to load thumbnail for {filename}: {e}")
    
    def open_image_url(self, url):
        """Open image URL in default browser"""
        if url:
            webbrowser.open(url)
        else:
            messagebox.showwarning("Warning", "No URL available for this image")
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def add_comment(self):
        """Add comment to the selected ticket"""
        if not self.current_ticket:
            return
        
        comment_text = self.comment_text.get(1.0, tk.END).strip()
        
        if not comment_text:
            messagebox.showwarning("Warning", "Please enter a comment")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        comment_data = {"body": comment_text}
        result = self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data)
        
        if result:
            messagebox.showinfo("Success", "Comment added successfully!")
            self.comment_text.delete(1.0, tk.END)
            # Reload comments
            self.load_comments(ticket_key)
        else:
            messagebox.showerror("Error", "Failed to add comment")
    
    def open_create_ticket_window(self):
        """Open window for creating new tickets"""
        create_window = tk.Toplevel(self.root)
        create_window.title("Create New Ticket")
        create_window.geometry("600x700")
        create_window.configure(bg='#1e1e1e')
        create_window.transient(self.root)
        create_window.grab_set()
        
        main_frame = ttk.Frame(create_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Issue Type - DEFAULT TO INCIDENT
        ttk.Label(main_frame, text="Issue Type:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.new_issue_type = tk.StringVar(value="[System] Incident")  # DEFAULT TO INCIDENT
        issue_type_combo = ttk.Combobox(main_frame, textvariable=self.new_issue_type, width=40,
                                       values=list(self.issue_types.keys()))
        issue_type_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Summary
        ttk.Label(main_frame, text="Summary:").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        self.new_summary = ttk.Entry(main_frame, width=50)
        self.new_summary.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Reporter field
        ttk.Label(main_frame, text="Reporter Email:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        self.new_reporter = ttk.Entry(main_frame, width=50)
        self.new_reporter.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        self.new_reporter.insert(0, self.email_entry.get())  # Default to current user
        
        # Assignee field
        ttk.Label(main_frame, text="Assign To (email):").grid(row=3, column=0, sticky=tk.W, pady=(0, 5))
        self.new_assignee = ttk.Entry(main_frame, width=50)
        self.new_assignee.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(0, 5))
        self.new_assignee.insert(0, self.email_entry.get())  # Default to current user
        
        # Description
        ttk.Label(main_frame, text="Description:").grid(row=4, column=0, sticky=(tk.NW, tk.W), pady=(0, 5))
        self.new_description = scrolledtext.ScrolledText(main_frame, width=50, height=10, wrap=tk.WORD,
                                                       bg='#3c3c3c', fg='#ffffff', insertbackground='#ffffff')
        self.new_description.grid(row=4, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # File attachments section
        attach_frame = ttk.LabelFrame(main_frame, text="Attachments", padding="5")
        attach_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Store attachments for new ticket
        self.new_ticket_attachments = []
        
        # Attachment list
        self.attach_listbox = tk.Listbox(attach_frame, height=3, bg='#2d2d2d', fg='#ffffff', 
                                        selectbackground='#0d7377')
        self.attach_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        # Attachment buttons
        attach_btn_frame = ttk.Frame(attach_frame)
        attach_btn_frame.pack(fill=tk.X)
        
        add_file_btn = ttk.Button(attach_btn_frame, text="Add Files", 
                                 command=lambda: self.add_files_to_new_ticket())
        add_file_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        remove_file_btn = ttk.Button(attach_btn_frame, text="Remove Selected", 
                                    command=lambda: self.remove_file_from_new_ticket())
        remove_file_btn.pack(side=tk.LEFT)
        
        ttk.Label(attach_frame, text="Or drag & drop files onto this window", 
                 font=('Segoe UI', 9)).pack(pady=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
        create_btn = ttk.Button(button_frame, text="Create Ticket", command=lambda: self.create_ticket(create_window))
        create_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=create_window.destroy)
        cancel_btn.pack(side=tk.LEFT)
        
        # Configure grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Enable drag-drop for the create window
        self.setup_drag_drop_for_window(create_window)
        
        # Focus on summary
        self.new_summary.focus()
    
    def create_ticket(self, window):
        """Create a new ticket with reporter, assignee, and file attachments"""
        if not self.new_summary.get().strip():
            messagebox.showerror("Error", "Summary is required")
            return
        
        issue_type_name = self.new_issue_type.get()
        issue_type_id = self.issue_types.get(issue_type_name)
        
        if not issue_type_id:
            messagebox.showerror("Error", f"Invalid issue type: {issue_type_name}")
            return
        
        reporter_email = self.new_reporter.get().strip()
        assignee_email = self.new_assignee.get().strip()
        
        # Get account IDs for reporter and assignee
        reporter_account_id = None
        assignee_account_id = None
        
        # Get reporter account ID
        if reporter_email:
            user_search = self.make_jira_request("user/search", params={"query": reporter_email})
            if user_search and len(user_search) > 0:
                reporter_account_id = user_search[0].get('accountId')
            else:
                messagebox.showwarning("Warning", f"Reporter '{reporter_email}' not found. Using current user.")
                reporter_email = self.email_entry.get().strip()
                user_search = self.make_jira_request("user/search", params={"query": reporter_email})
                if user_search and len(user_search) > 0:
                    reporter_account_id = user_search[0].get('accountId')
        
        # Get assignee account ID if specified
        if assignee_email:
            user_search = self.make_jira_request("user/search", params={"query": assignee_email})
            if user_search and len(user_search) > 0:
                assignee_account_id = user_search[0].get('accountId')
            else:
                response = messagebox.askyesno("User Not Found", 
                    f"Assignee '{assignee_email}' not found.\nCreate ticket unassigned?")
                if not response:
                    return
        
        # Create ticket data
        ticket_data = {
            "fields": {
                "project": {"key": "ITS"},
                "summary": self.new_summary.get().strip(),
                "description": self.new_description.get(1.0, tk.END).strip() or "No description provided",
                "issuetype": {"id": issue_type_id}
            }
        }
        
        # Add reporter if we have the account ID
        if reporter_account_id:
            ticket_data["fields"]["reporter"] = {"accountId": reporter_account_id}
        
        # Add assignee if we have the account ID
        if assignee_account_id:
            ticket_data["fields"]["assignee"] = {"accountId": assignee_account_id}
        
        result = self.make_jira_request("issue", method="POST", data=ticket_data)
        
        if result:
            ticket_key = result.get('key', 'Unknown')
            
            # Upload attachments if any
            if self.new_ticket_attachments:
                successful_uploads = 0
                failed_uploads = []
                
                url = f"{self.jira_url}/rest/api/2/issue/{ticket_key}/attachments"
                auth = HTTPBasicAuth(self.email_entry.get().strip(), self.api_token)
                headers = {'X-Atlassian-Token': 'no-check'}
                
                for file_path, file_name in self.new_ticket_attachments:
                    try:
                        with open(file_path, 'rb') as f:
                            files = {'file': (file_name, f, self.get_mime_type(file_name))}
                            response = requests.post(url, auth=auth, files=files, headers=headers)
                        
                        if response.status_code == 200:
                            successful_uploads += 1
                        else:
                            failed_uploads.append(file_name)
                    except Exception as e:
                        failed_uploads.append(file_name)
                
                # Build success message
                msg = f"Ticket {ticket_key} created successfully!\n"
                if reporter_email:
                    msg += f"Reporter: {reporter_email}\n"
                if assignee_account_id:
                    msg += f"Assigned to: {assignee_email}\n"
                elif assignee_email:
                    msg += "Note: Could not assign to specified user\n"
                else:
                    msg += "Unassigned\n"
                
                if successful_uploads > 0:
                    msg += f"\nAttached {successful_uploads} file(s)"
                if failed_uploads:
                    msg += f"\nFailed to attach: {', '.join(failed_uploads)}"
                
                messagebox.showinfo("Success", msg)
            else:
                # No attachments, simple message
                msg = f"Ticket {ticket_key} created successfully!\n"
                if reporter_email:
                    msg += f"Reporter: {reporter_email}\n"
                if assignee_account_id:
                    msg += f"Assigned to: {assignee_email}"
                elif assignee_email:
                    msg += "Note: Could not assign to specified user"
                else:
                    msg += "Unassigned"
                
                messagebox.showinfo("Success", msg)
            
            window.destroy()
            self.load_all_tickets_threaded()
        else:
            messagebox.showerror("Error", "Failed to create ticket")
    
    def open_html_viewer(self):
        """Open HTML viewer window for tickets with editing capability"""
        if self.html_viewer_window and self.html_viewer_window.winfo_exists():
            self.html_viewer_window.lift()
            return
        
        self.html_viewer_window = tk.Toplevel(self.root)
        self.html_viewer_window.title("Jira Ticket HTML Viewer & Editor")
        self.html_viewer_window.geometry("1000x800")
        self.html_viewer_window.configure(bg='#1e1e1e')
        
        main_frame = ttk.Frame(self.html_viewer_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title and controls frame
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.html_title_label = ttk.Label(title_frame, text="Select a ticket to view", 
                                         font=('Segoe UI', 14, 'bold'))
        self.html_title_label.pack(side=tk.LEFT)
        
        # Quick action buttons in HTML viewer
        self.html_close_btn = ttk.Button(title_frame, text="Close Ticket", 
                                        command=self.close_ticket_from_html, state="disabled")
        self.html_close_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.html_resolve_btn = ttk.Button(title_frame, text="Resolve", 
                                          command=self.resolve_ticket_from_html, state="disabled")
        self.html_resolve_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Create notebook for different views
        self.html_notebook = ttk.Notebook(main_frame)
        self.html_notebook.pack(fill=tk.BOTH, expand=True)
        
        # View tab - read-only formatted view
        self.view_frame = ttk.Frame(self.html_notebook)
        self.html_notebook.add(self.view_frame, text="View")
        
        self.html_content = scrolledtext.ScrolledText(self.view_frame, wrap=tk.WORD, 
                                                    bg='#2d2d2d', fg='#ffffff', 
                                                    insertbackground='#ffffff',
                                                    font=('Segoe UI', 11),
                                                    state='disabled')
        self.html_content.pack(fill=tk.BOTH, expand=True)
        
        # Edit tab - editable description and comments
        self.edit_frame = ttk.Frame(self.html_notebook)
        self.html_notebook.add(self.edit_frame, text="Edit")
        
        # Edit controls frame
        edit_controls = ttk.Frame(self.edit_frame)
        edit_controls.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(edit_controls, text="Edit Description:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        # Description editor
        self.html_description_editor = scrolledtext.ScrolledText(self.edit_frame, wrap=tk.WORD, 
                                                               bg='#3c3c3c', fg='#ffffff', 
                                                               insertbackground='#ffffff',
                                                               font=('Segoe UI', 11), height=8)
        self.html_description_editor.pack(fill=tk.X, pady=(0, 10))
        
        # Save description button
        self.save_desc_btn = ttk.Button(self.edit_frame, text="Save Description", 
                                       command=self.save_description, state="disabled")
        self.save_desc_btn.pack(pady=(0, 20))
        
        # Add comment section
        ttk.Label(self.edit_frame, text="Add New Comment:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
        
        self.html_comment_editor = scrolledtext.ScrolledText(self.edit_frame, wrap=tk.WORD, 
                                                           bg='#3c3c3c', fg='#ffffff', 
                                                           insertbackground='#ffffff',
                                                           font=('Segoe UI', 11), height=4)
        self.html_comment_editor.pack(fill=tk.X, pady=(5, 10))
        
        # Add comment button
        self.html_add_comment_btn = ttk.Button(self.edit_frame, text="Add Comment", 
                                             command=self.add_comment_from_html, state="disabled")
        self.html_add_comment_btn.pack()
        
        # If a ticket is already selected, show it
        if self.current_ticket:
            self.update_html_viewer(self.current_ticket)
        
        # Handle window closing
        self.html_viewer_window.protocol("WM_DELETE_WINDOW", self.on_html_viewer_close)
    
    def on_html_viewer_close(self):
        """Handle HTML viewer window closing"""
        self.html_viewer_window.destroy()
        self.html_viewer_window = None
    
    def update_html_viewer(self, issue):
        """Update the HTML viewer with ticket content"""
        if not self.html_viewer_window or not self.html_viewer_window.winfo_exists():
            return
        
        fields = issue.get('fields', {})
        ticket_key = issue.get('key', 'Unknown')
        
        # Update HTML viewer with comments
        summary = fields.get('summary', 'No summary')
        self.html_title_label.config(text=f"{ticket_key}: {summary}")
        
        # Update view tab
        content = self.build_ticket_html_content(issue)
        self.html_content.config(state='normal')
        self.html_content.delete(1.0, tk.END)
        self.html_content.insert(1.0, content)
        self.html_content.config(state='disabled')
        
        # Update edit tab
        description = fields.get('description', '')
        self.html_description_editor.delete(1.0, tk.END)
        self.html_description_editor.insert(1.0, description if description else '')
        
        # Enable edit buttons
        self.save_desc_btn.config(state="normal")
        self.html_add_comment_btn.config(state="normal")
        self.html_close_btn.config(state="normal")
        self.html_resolve_btn.config(state="normal")
    
    def build_ticket_html_content(self, issue):
        """Build detailed HTML-like content for the ticket"""
        fields = issue.get('fields', {})
        ticket_key = issue.get('key', 'Unknown')
        
        content = f"TICKET: {ticket_key}\n"
        content += "=" * 50 + "\n\n"
        
        # Basic info
        issue_type = fields.get('issuetype', {})
        content += f"Type: {issue_type.get('name', 'Unknown') if issue_type else 'Unknown'}\n"
        
        content += f"Summary: {fields.get('summary', 'No summary')}\n\n"
        
        status = fields.get('status', {})
        status_name = status.get('name', 'Unknown') if status else 'Unknown'
        content += f"Status: {status_name}\n"
        
        priority = fields.get('priority', {})
        content += f"Priority: {priority.get('name', 'Unknown') if priority else 'Unknown'}\n\n"
        
        # People
        reporter = fields.get('reporter')
        content += f"Reporter: {reporter.get('displayName', 'Unknown') if reporter else 'Unknown'}\n"
        
        assignee = fields.get('assignee')
        content += f"Assignee: {assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'}\n\n"
        
        # Dates
        created = fields.get('created', '')
        if created:
            try:
                dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                content += f"Created: {dt.strftime('%Y-%m-%d %H:%M')}\n"
            except:
                content += f"Created: {created}\n"
        
        updated = fields.get('updated', '')
        if updated:
            try:
                dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                content += f"Updated: {dt.strftime('%Y-%m-%d %H:%M')}\n"
            except:
                content += f"Updated: {updated}\n"
        
        content += "\n" + "=" * 50 + "\n"
        content += "DESCRIPTION:\n"
        content += "-" * 20 + "\n"
        description = fields.get('description', 'No description')
        content += description if description else 'No description'
        content += "\n\n"
        
        # Attachments
        attachments = fields.get('attachment', [])
        if attachments:
            content += "=" * 50 + "\n"
            content += f"ATTACHMENTS ({len(attachments)}):\n"
            content += "-" * 20 + "\n"
            for attachment in attachments:
                filename = attachment.get('filename', 'Unknown')
                size = self.format_file_size(attachment.get('size', 0))
                content_type = attachment.get('mimeType', 'Unknown')
                content += f"{filename} ({size}) - {content_type}\n"
            content += "\n"
        
        # Comments
        content += "=" * 50 + "\n"
        content += "LOADING COMMENTS...\n"
        content += "-" * 20 + "\n"
        
        # Load comments asynchronously
        threading.Thread(target=self.load_comments_for_html_viewer, 
                        args=(ticket_key,), daemon=True).start()
        
        return content
    
    def load_comments_for_html_viewer(self, ticket_key):
        """Load comments for the HTML viewer"""
        comments_data = self.make_jira_request(f"issue/{ticket_key}/comment")
        
        if comments_data and 'comments' in comments_data:
            comments = comments_data['comments']
            
            # Build comments content
            comments_content = "COMMENTS:\n" + "-" * 20 + "\n"
            
            if comments:
                for comment in comments:
                    author = comment.get('author', {})
                    author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                    created = comment.get('created', '')
                    body = comment.get('body', 'No content')
                    
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created_str = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        created_str = created[:16] if len(created) >= 16 else created
                    
                    comments_content += f"[{created_str}] {author_name}:\n{body}\n\n"
            else:
                comments_content += "No comments yet.\n"
            
            # Update HTML viewer with comments
            def update_comments():
                if (self.html_viewer_window and self.html_viewer_window.winfo_exists() and 
                    self.current_ticket and self.current_ticket.get('key') == ticket_key):
                    
                    current_content = self.html_content.get(1.0, tk.END)
                    # Replace the "LOADING COMMENTS..." section
                    if "LOADING COMMENTS..." in current_content:
                        new_content = current_content.replace(
                            "LOADING COMMENTS...\n" + "-" * 20 + "\n",
                            comments_content
                        )
                        self.html_content.config(state='normal')
                        self.html_content.delete(1.0, tk.END)
                        self.html_content.insert(1.0, new_content)
                        self.html_content.config(state='disabled')
            
            self.root.after(0, update_comments)
    
    def save_description(self):
        """Save edited description back to Jira"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        new_description = self.html_description_editor.get(1.0, tk.END).strip()
        
        # Update ticket description
        update_data = {
            "fields": {
                "description": new_description
            }
        }
        
        result = self.make_jira_request(f"issue/{ticket_key}", method="PUT", data=update_data)
        
        if result is not None:
            messagebox.showinfo("Success", "Description updated successfully!")
            # Refresh current ticket data
            self.refresh_current_ticket()
        else:
            messagebox.showerror("Error", "Failed to update description")
    
    def add_comment_from_html(self):
        """Add comment from HTML viewer"""
        if not self.current_ticket:
            return
        
        comment_text = self.html_comment_editor.get(1.0, tk.END).strip()
        
        if not comment_text:
            messagebox.showwarning("Warning", "Please enter a comment")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        comment_data = {"body": comment_text}
        result = self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data)
        
        if result:
            messagebox.showinfo("Success", "Comment added successfully!")
            self.html_comment_editor.delete(1.0, tk.END)
            # Refresh current ticket data
            self.refresh_current_ticket()
        else:
            messagebox.showerror("Error", "Failed to add comment")
    
    def close_ticket_from_html(self):
        """Close ticket from HTML viewer"""
        self.close_ticket()
    
    def resolve_ticket_from_html(self):
        """Resolve ticket from HTML viewer"""
        self.resolve_ticket()
    
    def refresh_current_ticket(self):
        """Refresh current ticket data after editing"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        # Get updated ticket data
        updated_ticket = self.make_jira_request(f"issue/{ticket_key}")
        
        if updated_ticket:
            self.current_ticket = updated_ticket
            
            # Update main details panel
            self.show_ticket_details(updated_ticket)
            
            # Update HTML viewer if open
            if self.html_viewer_window and self.html_viewer_window.winfo_exists():
                self.update_html_viewer(updated_ticket)
            
            # Refresh ticket list to show any status changes
            self.load_all_tickets_threaded()
    
    def paste_screenshot(self):
        """Paste screenshot from clipboard and attach to current ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        try:
            ticket_key = self.current_ticket.get('key')
            
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            
            if img is not None:
                # Convert to bytes
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_data = img_buffer.getvalue()
                
                # Create filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'screenshot_{timestamp}.png'
                
                # Upload to Jira
                url = f"{self.jira_url}/rest/api/2/issue/{ticket_key}/attachments"
                auth = HTTPBasicAuth(self.email_entry.get().strip(), self.api_token)
                
                files = {'file': (filename, img_data, 'image/png')}
                headers = {'X-Atlassian-Token': 'no-check'}  # Required for Jira file uploads
                
                response = requests.post(url, auth=auth, files=files, headers=headers)
                
                if response.status_code == 200:
                    messagebox.showinfo("Success", f"Screenshot attached to {ticket_key}!")
                    # Refresh ticket details to show new attachment
                    self.refresh_current_ticket()
                else:
                    messagebox.showerror("Error", f"Failed to attach screenshot. Status: {response.status_code}")
            else:
                messagebox.showwarning("Warning", "No image found in clipboard.\n\nTo copy a screenshot:\n• Windows: Press Print Screen or use Snipping Tool\n• Take screenshot and copy it (Ctrl+C)\n• Then try pasting here")
                
        except ImportError as e:
            messagebox.showerror("Error", f"PIL (Pillow) library not available: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to paste screenshot: {str(e)}")
    
    def add_mention(self, email):
        """Add @mention to the current comment"""
        current_text = self.comment_text.get(1.0, tk.END).strip()
        if current_text:
            self.comment_text.insert(tk.END, f" @{email}")
        else:
            self.comment_text.insert(tk.END, f"@{email} ")
        
        # Focus back to comment text
        self.comment_text.focus()
    
    def get_team_members(self):
        """Get list of team members from multiple projects for mentions"""
        users_window = tk.Toplevel(self.root)
        users_window.title("Select Team Members")
        users_window.geometry("500x600")
        users_window.configure(bg='#1e1e1e')
        users_window.transient(self.root)
        users_window.grab_set()
        
        main_frame = ttk.Frame(users_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Project selection
        project_frame = ttk.Frame(main_frame)
        project_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(project_frame, text="Select Project/Team:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))
        
        # Get available projects
        self.project_var = tk.StringVar(value="ITS")
        project_combo = ttk.Combobox(project_frame, textvariable=self.project_var, width=20)
        project_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Try to get all projects
        projects_data = self.make_jira_request("project")
        if projects_data:
            project_keys = [p.get('key', '') for p in projects_data]
            project_combo['values'] = project_keys
        else:
            project_combo['values'] = ["ITS"]  # Default to ITS if can't get projects
        
        load_btn = ttk.Button(project_frame, text="Load Users", 
                             command=lambda: self.load_project_users(users_window))
        load_btn.pack(side=tk.LEFT)
        
        search_btn = ttk.Button(project_frame, text="Search All Users", 
                               command=lambda: self.search_all_users(users_window))
        search_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Label(main_frame, text="Click to add @mention:", font=('Segoe UI', 10)).pack(pady=(10, 10))
        
        # Create scrollable user list
        user_frame = ttk.Frame(main_frame)
        user_frame.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(user_frame, bg='#2d2d2d', highlightthickness=0)
        scrollbar = ttk.Scrollbar(user_frame, orient="vertical", command=canvas.yview)
        self.users_scrollable_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=self.users_scrollable_frame, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load initial users from ITS
        self.load_project_users(users_window)
    
    def load_project_users(self, parent_window):
        """Load users from selected project"""
        project = self.project_var.get()
        
        # Clear existing users
        for widget in self.users_scrollable_frame.winfo_children():
            widget.destroy()
        
        # Get users for this project
        users_data = self.make_jira_request("user/assignable/search", params={
            'project': project,
            'maxResults': 100
        })
        
        if users_data:
            ttk.Label(self.users_scrollable_frame, 
                     text=f"Users from {project} project ({len(users_data)} found):",
                     font=('Segoe UI', 10, 'bold')).pack(pady=(0, 10))
            
            for user in users_data:
                display_name = user.get('displayName', 'Unknown')
                email_address = user.get('emailAddress', user.get('name', ''))
                
                user_btn = ttk.Button(self.users_scrollable_frame, 
                                    text=f"{display_name} ({email_address})",
                                    command=lambda e=email_address, w=parent_window: self.select_user_mention(e, w))
                user_btn.pack(fill=tk.X, pady=2, padx=5)
        else:
            ttk.Label(self.users_scrollable_frame, 
                     text=f"No users found for project {project}").pack()
    
    def search_all_users(self, parent_window):
        """Search all users in Jira"""
        search_window = tk.Toplevel(parent_window)
        search_window.title("Search All Users")
        search_window.geometry("400x150")
        search_window.configure(bg='#1e1e1e')
        search_window.transient(parent_window)
        
        frame = ttk.Frame(search_window, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Search for user:", font=('Segoe UI', 10)).pack(pady=(0, 10))
        
        search_entry = ttk.Entry(frame, width=40)
        search_entry.pack(pady=(0, 10))
        
        def do_search():
            query = search_entry.get().strip()
            if query:
                # Search for users
                users_data = self.make_jira_request("user/search", params={
                    'query': query,
                    'maxResults': 50
                })
                
                if users_data:
                    # Clear and update the main user list
                    for widget in self.users_scrollable_frame.winfo_children():
                        widget.destroy()
                    
                    ttk.Label(self.users_scrollable_frame, 
                             text=f"Search results for '{query}' ({len(users_data)} found):",
                             font=('Segoe UI', 10, 'bold')).pack(pady=(0, 10))
                    
                    for user in users_data:
                        display_name = user.get('displayName', 'Unknown')
                        email_address = user.get('emailAddress', user.get('name', ''))
                        
                        user_btn = ttk.Button(self.users_scrollable_frame, 
                                            text=f"{display_name} ({email_address})",
                                            command=lambda e=email_address, w=parent_window: self.select_user_mention(e, w))
                        user_btn.pack(fill=tk.X, pady=2, padx=5)
                    
                    search_window.destroy()
                else:
                    messagebox.showinfo("No Results", f"No users found matching '{query}'")
        
        ttk.Button(frame, text="Search", command=do_search).pack()
        
        # Allow Enter key to search
        search_entry.bind('<Return>', lambda e: do_search())
        search_entry.focus()
    
    def select_user_mention(self, email, window):
        """Add selected user mention and close window"""
        self.add_mention(email)
        window.destroy()
    
    def search_tickets(self, event=None):\n        \"\"\"Enhanced search with smart filtering\"\"\"\n        search_term = self.search_entry.get().strip()\n        if search_term == \"🔍 Search tickets...\" or not search_term:\n            # Show all tickets if no search term\n            self.filter_tickets()\n            return\n            \n        # Filter current tickets based on search\n        if not hasattr(self, 'all_tickets') or not self.all_tickets:\n            return\n            \n        # Clear current display\n        for item in self.tree.get_children():\n            self.tree.delete(item)\n            \n        matching_tickets = []\n        search_lower = search_term.lower()\n        \n        for issue in self.all_tickets:\n            fields = issue.get('fields', {})\n            key = issue.get('key', '').lower()\n            summary = fields.get('summary', '').lower()\n            description = fields.get('description', '')\n            desc_text = description if isinstance(description, str) else ''\n            \n            # Search in key, summary, and description\n            if (search_lower in key or \n                search_lower in summary or \n                search_lower in desc_text.lower()):\n                matching_tickets.append(issue)\n                \n        self.update_ticket_list(matching_tickets)\n        self.status_label.config(text=f\"Found {len(matching_tickets)} tickets matching '{search_term}'\")\n        \n    def original_search_tickets(self, event=None):
        """Search tickets based on text content"""
        search_text = self.search_entry.get().strip()
        
        if not search_text:
            messagebox.showwarning("Warning", "Please enter search text")
            return
        
        # Build JQL for search
        jql = f'project = ITS AND text ~ "{search_text}"'
        
        params = {
            'jql': jql,
            'maxResults': 100,
            'startAt': 0
        }
        
        self.status_label.config(text=f"Searching for: {search_text}...")
        
        def do_search():
            data = self.make_jira_request("search", params=params)
            
            if data and 'issues' in data:
                self.root.after(0, self.update_ticket_list, data['issues'])
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Found {len(data['issues'])} tickets matching '{search_text}'"))
                # Store search results
                self.all_tickets = data['issues']
            else:
                self.root.after(0, lambda: self.status_label.config(
                    text=f"No tickets found matching '{search_text}'"))
        
        threading.Thread(target=do_search, daemon=True).start()
    
    def clear_search(self):
        """Clear search and reload all tickets"""
        self.search_entry.delete(0, tk.END)
        self.load_all_tickets_threaded()
    
    def on_right_click(self, event):
        """Handle right-click on ticket"""
        # Select the item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree.focus(item)
            # Show context menu
            self.context_menu.post(event.x_root, event.y_root)
    
    def copy_ticket_url(self):
        """Copy ticket URL to clipboard"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            url = f"{self.jira_url}/browse/{ticket_key}"
            
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.status_label.config(text=f"Copied URL for {ticket_key} to clipboard")
    
    def open_ticket_in_browser(self):
        """Open ticket in browser"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            url = f"{self.jira_url}/browse/{ticket_key}"
            webbrowser.open(url)
    
    def copy_ticket_key(self):
        """Copy ticket key to clipboard"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            
            self.root.clipboard_clear()
            self.root.clipboard_append(ticket_key)
            self.status_label.config(text=f"Copied {ticket_key} to clipboard")
    
    def on_comment_key_release(self, event):
        """Handle key release in comment box for @mention autocomplete"""
        current_pos = self.comment_text.index(tk.INSERT)
        current_text = self.comment_text.get("1.0", current_pos)
        
        # Check if we're typing an @mention
        if '@' in current_text:
            # Find the last @ symbol
            last_at = current_text.rfind('@')
            text_after_at = current_text[last_at + 1:]
            
            # Check if we're in the middle of typing a mention
            if last_at >= 0 and (not text_after_at or not text_after_at.endswith(' ')):
                self.mention_start_pos = f"1.0 + {last_at} chars"
                self.show_autocomplete(text_after_at)
            else:
                self.hide_autocomplete()
        else:
            self.hide_autocomplete()
    
    def show_autocomplete(self, search_text):
        """Show autocomplete suggestions for @mentions"""
        if not self.available_users:
            # Load users if not already loaded
            self.load_available_users()
            return
        
        # Filter users based on search text
        filtered_users = []
        search_lower = search_text.lower()
        
        for user in self.available_users:
            display_name = user.get('displayName', '').lower()
            email = user.get('emailAddress', '').lower()
            
            if search_lower in display_name or search_lower in email:
                filtered_users.append(user)
        
        if filtered_users:
            # Update listbox
            self.autocomplete_listbox.delete(0, tk.END)
            
            for user in filtered_users[:10]:  # Show max 10 suggestions
                display_name = user.get('displayName', 'Unknown')
                email = user.get('emailAddress', '')
                self.autocomplete_listbox.insert(tk.END, f"{display_name} ({email})")
            
            # Position and show the autocomplete frame
            if not self.autocomplete_active:
                self.autocomplete_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
                self.autocomplete_active = True
        else:
            self.hide_autocomplete()
    
    def hide_autocomplete(self):
        """Hide autocomplete suggestions"""
        if self.autocomplete_active:
            self.autocomplete_frame.grid_forget()
            self.autocomplete_active = False
    
    def on_autocomplete_select(self, event=None):
        """Handle selection from autocomplete list"""
        selection = self.autocomplete_listbox.curselection()
        if selection:
            selected_text = self.autocomplete_listbox.get(selection[0])
            # Extract email from the format "Name (email)"
            email = selected_text.split('(')[1].rstrip(')')
            
            # Replace the partial mention with the full email
            current_pos = self.comment_text.index(tk.INSERT)
            # Delete from @ to current position
            self.comment_text.delete(self.mention_start_pos, current_pos)
            # Insert the full mention
            self.comment_text.insert(self.mention_start_pos, f"@{email} ")
            
            self.hide_autocomplete()
            self.comment_text.focus()
    
    def load_available_users(self):
        """Load available users for @mention autocomplete"""
        def load_users():
            users_data = self.make_jira_request("user/assignable/search", params={
                'project': 'ITS',
                'maxResults': 100
            })
            
            if users_data:
                self.available_users = users_data
                # Try showing autocomplete again with loaded users
                current_pos = self.comment_text.index(tk.INSERT)
                current_text = self.comment_text.get("1.0", current_pos)
                if '@' in current_text:
                    last_at = current_text.rfind('@')
                    text_after_at = current_text[last_at + 1:]
                    if last_at >= 0 and (not text_after_at or not text_after_at.endswith(' ')):
                        self.root.after(0, lambda: self.show_autocomplete(text_after_at))
        
        threading.Thread(target=load_users, daemon=True).start()
    
    def create_text_context_menu(self, text_widget):
        """Create right-click context menu for text widgets"""
        context_menu = tk.Menu(text_widget, tearoff=0)
        
        def copy_text():
            try:
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
            except tk.TclError:
                pass  # No selection
        
        def copy_all():
            all_text = text_widget.get(1.0, tk.END).strip()
            if all_text:
                self.root.clipboard_clear()
                self.root.clipboard_append(all_text)
        
        def paste_text():
            try:
                # Check if widget is editable
                if str(text_widget.cget('state')) != 'disabled':
                    text = self.root.clipboard_get()
                    text_widget.insert(tk.INSERT, text)
            except tk.TclError:
                pass  # No clipboard content
        
        def select_all():
            text_widget.tag_add(tk.SEL, "1.0", tk.END)
            text_widget.mark_set(tk.INSERT, "1.0")
            text_widget.see(tk.INSERT)
        
        context_menu.add_command(label="Copy", command=copy_text)
        context_menu.add_command(label="Copy All", command=copy_all)
        context_menu.add_command(label="Paste", command=paste_text)
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=select_all)
        
        def show_context_menu(event):
            context_menu.post(event.x_root, event.y_root)
        
        text_widget.bind("<Button-3>", show_context_menu)
        
        # Also bind standard keyboard shortcuts
        text_widget.bind("<Control-c>", lambda e: copy_text())
        text_widget.bind("<Control-a>", lambda e: select_all())
        text_widget.bind("<Control-v>", lambda e: paste_text())
    
    def load_quick_mentions(self):
        """Load quick mentions from file"""
        try:
            if os.path.exists(self.quick_mentions_file):
                with open(self.quick_mentions_file, 'r') as f:
                    self.quick_mentions = json.load(f)
        except Exception as e:
            print(f"Could not load quick mentions: {e}")
            # Keep default if load fails
    
    def save_quick_mentions(self):
        """Save quick mentions to file"""
        try:
            with open(self.quick_mentions_file, 'w') as f:
                json.dump(self.quick_mentions, f)
        except Exception as e:
            print(f"Could not save quick mentions: {e}")
    
    def refresh_quick_mention_buttons(self):
        """Refresh the quick mention buttons with remove option"""
        # Clear existing buttons
        for widget in self.quick_mentions_frame.winfo_children():
            widget.destroy()
        
        # Create frame for each mention with button and remove option
        for i, (name, email) in enumerate(self.quick_mentions):
            btn_frame = ttk.Frame(self.quick_mentions_frame)
            btn_frame.grid(row=i // 3, column=i % 3, padx=(0, 5), pady=(0, 5), sticky=tk.W)
            
            # Mention button
            btn = ttk.Button(btn_frame, 
                           text=f"@{name}", 
                           command=lambda e=email: self.add_mention(e))
            btn.pack(side=tk.LEFT)
            
            # Remove button (X)
            remove_btn = ttk.Button(btn_frame, 
                                  text="✕", 
                                  width=3,
                                  command=lambda idx=i: self.remove_quick_mention(idx))
            remove_btn.pack(side=tk.LEFT, padx=(2, 0))
    
    def remove_quick_mention(self, index):
        """Remove a quick mention by index"""
        if 0 <= index < len(self.quick_mentions):
            name, email = self.quick_mentions[index]
            response = messagebox.askyesno("Remove Quick Mention", 
                                          f"Remove @{name} from quick mentions?")
            if response:
                del self.quick_mentions[index]
                self.save_quick_mentions()
                self.refresh_quick_mention_buttons()
    
    def sort_treeview(self, col, reverse):
        """Sort treeview by column when header is clicked"""
        # Get all data from treeview
        data = []
        for child in self.tree.get_children():
            values = self.tree.item(child)['values']
            data.append((child, values))
        
        # Get column index
        col_index = self.tree['columns'].index(col)
        
        # Special sorting for different columns
        if col == "Key":
            # Sort by ticket number (extract number from ITS-XXX)
            def key_sort(item):
                key_value = item[1][col_index]
                try:
                    # Extract number from format like "ITS-123"
                    parts = str(key_value).split('-')
                    if len(parts) > 1:
                        return int(parts[-1])
                    return 0
                except:
                    return 0
            data.sort(key=key_sort, reverse=reverse)
            
        elif col == "Created":
            # Sort by date
            def date_sort(item):
                date_value = item[1][col_index]
                try:
                    # Parse date from YYYY-MM-DD format
                    from datetime import datetime
                    return datetime.strptime(str(date_value), '%Y-%m-%d')
                except:
                    return datetime.min
            data.sort(key=date_sort, reverse=reverse)
            
        elif col == "Status":
            # Sort alphabetically but with custom priority
            status_priority = {
                'open': 1,
                'in progress': 2,
                'pending': 3,
                'waiting': 4,
                'resolved': 5,
                'closed': 6,
                'done': 7
            }
            def status_sort(item):
                status_value = str(item[1][col_index]).lower()
                # Check for priority status
                for key, priority in status_priority.items():
                    if key in status_value:
                        return (priority, status_value)
                return (999, status_value)  # Unknown statuses go last
            data.sort(key=status_sort, reverse=reverse)
        else:
            # Default alphabetical sort
            data.sort(key=lambda x: str(x[1][col_index]), reverse=reverse)
        
        # Rearrange items in treeview
        for index, (child, values) in enumerate(data):
            self.tree.move(child, '', index)
        
        # Toggle sort order for next click
        self.sort_reverse[col] = not reverse
        
        # Update column heading to show sort direction
        for column in self.tree['columns']:
            if column == col:
                if reverse:
                    self.tree.heading(column, text=f"{column} ↓", 
                                    command=lambda c=column: self.sort_treeview(c, self.sort_reverse.get(c, False)))
                else:
                    self.tree.heading(column, text=f"{column} ↑", 
                                    command=lambda c=column: self.sort_treeview(c, self.sort_reverse.get(c, False)))
            elif column in ["Key", "Status", "Created"]:
                # Reset other sortable columns
                self.tree.heading(column, text=column, 
                                command=lambda c=column: self.sort_treeview(c, False))
    
    def manage_quick_mentions(self):
        """Open window to manage quick mentions"""
        manage_window = tk.Toplevel(self.root)
        manage_window.title("Manage Quick Mentions")
        manage_window.geometry("500x400")
        manage_window.configure(bg='#1e1e1e')
        manage_window.transient(self.root)
        manage_window.grab_set()
        
        main_frame = ttk.Frame(manage_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Quick Mention List:", font=('Segoe UI', 12, 'bold')).pack(pady=(0, 10))
        
        # Listbox to show current quick mentions
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.mentions_listbox = tk.Listbox(list_frame, 
                                          bg='#2d2d2d', fg='#ffffff',
                                          selectbackground='#0d7377',
                                          yscrollcommand=scrollbar.set)
        self.mentions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.mentions_listbox.yview)
        
        # Populate listbox
        for name, email in self.quick_mentions:
            self.mentions_listbox.insert(tk.END, f"{name} - {email}")
        
        # Add/Edit frame
        add_frame = ttk.LabelFrame(main_frame, text="Add/Edit Quick Mention", padding="5")
        add_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        name_entry = ttk.Entry(add_frame, width=20)
        name_entry.grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(add_frame, text="Email:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        email_entry = ttk.Entry(add_frame, width=30)
        email_entry.grid(row=0, column=3)
        
        def add_mention():
            name = name_entry.get().strip()
            email = email_entry.get().strip()
            if name and email:
                self.quick_mentions.append((name, email))
                self.mentions_listbox.insert(tk.END, f"{name} - {email}")
                name_entry.delete(0, tk.END)
                email_entry.delete(0, tk.END)
                self.save_quick_mentions()
                self.refresh_quick_mention_buttons()
        
        def remove_mention():
            selection = self.mentions_listbox.curselection()
            if selection:
                index = selection[0]
                self.mentions_listbox.delete(index)
                del self.quick_mentions[index]
                self.save_quick_mentions()
                self.refresh_quick_mention_buttons()
        
        def load_from_team():
            """Load team members and let user select"""
            users_data = self.make_jira_request("user/assignable/search", params={
                'project': 'ITS',
                'maxResults': 100
            })
            
            if users_data:
                select_window = tk.Toplevel(manage_window)
                select_window.title("Select Team Members")
                select_window.geometry("400x500")
                select_window.configure(bg='#1e1e1e')
                
                frame = ttk.Frame(select_window, padding="10")
                frame.pack(fill=tk.BOTH, expand=True)
                
                ttk.Label(frame, text="Select users to add:", font=('Segoe UI', 10, 'bold')).pack(pady=(0, 10))
                
                # Listbox with checkboxes
                users_frame = ttk.Frame(frame)
                users_frame.pack(fill=tk.BOTH, expand=True)
                
                canvas = tk.Canvas(users_frame, bg='#2d2d2d', highlightthickness=0)
                scrollbar = ttk.Scrollbar(users_frame, orient="vertical", command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                canvas.configure(yscrollcommand=scrollbar.set)
                canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                checkboxes = []
                for user in users_data:
                    display_name = user.get('displayName', 'Unknown')
                    email_address = user.get('emailAddress', user.get('name', ''))
                    
                    var = tk.BooleanVar()
                    cb = ttk.Checkbutton(scrollable_frame, 
                                        text=f"{display_name} ({email_address})",
                                        variable=var)
                    cb.pack(anchor=tk.W, pady=2)
                    checkboxes.append((var, display_name, email_address))
                
                def add_selected():
                    for var, name, email in checkboxes:
                        if var.get() and email:
                            # Check if not already in list
                            if not any(em == email for _, em in self.quick_mentions):
                                self.quick_mentions.append((name, email))
                                self.mentions_listbox.insert(tk.END, f"{name} - {email}")
                    self.save_quick_mentions()
                    self.refresh_quick_mention_buttons()
                    select_window.destroy()
                
                ttk.Button(frame, text="Add Selected", command=add_selected).pack(pady=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Add", command=add_mention).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Remove Selected", command=remove_mention).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Add from Team", command=load_from_team).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Close", command=manage_window.destroy).pack(side=tk.LEFT)


def main():
    root = tk.Tk()
    app = JiraTicketViewer(root)
    root.mainloop()

if __name__ == "__main__":
    main()


    