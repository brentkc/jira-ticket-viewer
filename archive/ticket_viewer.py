"""
Main GUI class for Jira Ticket Viewer - Complete refactored version with all features
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading

# Import our modules
from config import (WINDOW_TITLE, WINDOW_GEOMETRY, THEME_COLORS, DEFAULT_EMAIL, 
                   TREE_COLUMNS, TICKET_FILTER_OPTIONS, ISSUE_TYPE_FILTER_OPTIONS,
                   UI_MESSAGES, ATTACHMENT_FILE_TYPES)
from jira_api import JiraAPIClient
from search_filter import SearchFilterManager
from ticket_operations import TicketOperationsManager
from comment_system import CommentSystemManager
from attachment_manager import AttachmentManager
from user_management import UserManagementSystem
from html_viewer import HTMLTicketViewer
from utils import load_quick_mentions


class JiraTicketViewer:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_GEOMETRY)
        
        # Initialize state
        self.all_tickets = []
        self.current_ticket = None
        self.html_viewer_window = None
        self.sort_reverse = {}
        
        # Configure dark mode
        self.setup_dark_mode()
        
        # Initialize API client
        self.api_client = JiraAPIClient(
            email_callback=self.get_user_email,
            status_callback=self.update_status
        )
        
        # Initialize specialized managers
        self.search_filter = SearchFilterManager(
            self.api_client, 
            None,  # tree_widget - will be set after UI setup
            self.update_status,
            self.update_ticket_list
        )
        
        self.ticket_ops = TicketOperationsManager(
            self.api_client,
            self.update_status,
            self.load_all_tickets_threaded
        )
        
        self.comment_system = CommentSystemManager(
            self.api_client,
            self.update_status
        )
        
        self.attachment_manager = AttachmentManager(
            self.api_client,
            self.update_status
        )
        
        self.user_management = UserManagementSystem(
            self.api_client,
            self.update_status
        )
        
        # HTML viewer will be initialized after UI setup
        self.html_viewer = None
        
        # Setup UI
        self.setup_ui()
        
        # Initialize cross-references after UI is set up
        self.setup_cross_references()
    
    def setup_dark_mode(self):
        """Configure modern dark mode for the application"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Get colors from config
        colors = THEME_COLORS
        
        # Configure main components
        style.configure('TFrame', background=colors['bg_primary'])
        style.configure('TLabel', background=colors['bg_primary'], foreground=colors['text_primary'])
        
        # Buttons
        style.configure('TButton', 
                       background=colors['bg_button'], 
                       foreground=colors['text_primary'],
                       borderwidth=0, 
                       focuscolor='none', 
                       relief='flat',
                       padding=(12, 8))
        style.map('TButton', 
                 background=[('active', colors['bg_button_hover']), ('pressed', colors['bg_button_hover'])])
        
        # Entry fields
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
        
        # Combobox
        style.configure('TCombobox', 
                       background=colors['bg_input'], 
                       foreground=colors['text_primary'],
                       borderwidth=1, 
                       arrowcolor=colors['text_primary'], 
                       relief='flat',
                       bordercolor=colors['border'],
                       fieldbackground=colors['bg_input'],
                       selectbackground=colors['bg_input'],
                       selectforeground=colors['text_primary'])
        style.map('TCombobox', 
                 background=[('readonly', colors['bg_input'])],
                 fieldbackground=[('readonly', colors['bg_input'])],
                 foreground=[('readonly', colors['text_primary'])],
                 bordercolor=[('focus', colors['accent'])])
        
        # Label frames
        style.configure('TLabelFrame', 
                       background=colors['bg_primary'], 
                       foreground=colors['text_primary'],
                       borderwidth=1, 
                       relief='solid', 
                       bordercolor=colors['border'])
        style.configure('TLabelFrame.Label', 
                       background=colors['bg_primary'], 
                       foreground=colors['text_primary'])
        
        # Checkbuttons
        style.configure('TCheckbutton', 
                       background=colors['bg_primary'], 
                       foreground=colors['text_primary'],
                       focuscolor='none')
        
        # Treeview
        style.configure('Treeview', 
                       background=colors['bg_surface'], 
                       foreground=colors['text_primary'],
                       fieldbackground=colors['bg_surface'], 
                       borderwidth=0, 
                       relief='flat')
        style.configure('Treeview.Heading', 
                       background=colors['bg_secondary'], 
                       foreground=colors['text_primary'],
                       borderwidth=1, 
                       relief='flat',
                       bordercolor=colors['border'])
        style.map('Treeview', 
                 background=[('selected', colors['accent'])],
                 foreground=[('selected', colors['text_primary'])])
        style.map('Treeview.Heading',
                 background=[('active', colors['bg_button'])])
        
        # Scrollbars
        style.configure('Vertical.TScrollbar', 
                       background=colors['bg_secondary'], 
                       troughcolor=colors['bg_primary'], 
                       borderwidth=0, 
                       arrowcolor=colors['text_secondary'])
        
        # Notebook
        style.configure('TNotebook', 
                       background=colors['bg_primary'], 
                       borderwidth=0)
        style.configure('TNotebook.Tab', 
                       background=colors['bg_secondary'], 
                       foreground=colors['text_primary'],
                       padding=[16, 10], 
                       borderwidth=0)
        style.map('TNotebook.Tab',
                 background=[('selected', colors['bg_button']), ('active', colors['bg_button_hover'])])
        
        self.root.configure(bg=colors['bg_primary'])
    
    def setup_ui(self):
        """Setup the main user interface with all components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Search frame at the top
        search_frame = ttk.LabelFrame(main_frame, text="Search Tickets", padding="5")
        search_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.search_entry = ttk.Entry(search_frame, width=50)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.search_entry.bind('<Return>', self.search_filter.search_tickets)
        
        self.search_btn = ttk.Button(search_frame, text="Search", command=self.search_filter.search_tickets)
        self.search_btn.grid(row=0, column=2, padx=(0, 5))
        
        self.clear_search_btn = ttk.Button(search_frame, text="Clear", command=self.search_filter.clear_search)
        self.clear_search_btn.grid(row=0, column=3)
        
        search_frame.columnconfigure(1, weight=1)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="5")
        config_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(config_frame, text="Email:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.email_entry = ttk.Entry(config_frame, width=30)
        self.email_entry.insert(0, DEFAULT_EMAIL)
        self.email_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.load_all_btn = ttk.Button(button_frame, text="Load All Tickets", 
                                      command=self.load_all_tickets_threaded)
        self.load_all_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.create_ticket_btn = ttk.Button(button_frame, text="Create New Ticket", 
                                           command=self.open_create_ticket_window)
        self.create_ticket_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.html_viewer_btn = ttk.Button(button_frame, text="HTML Viewer Window", 
                                         command=self.open_html_viewer)
        self.html_viewer_btn.grid(row=0, column=2, padx=(0, 5))
        
        self.dashboard_btn = ttk.Button(button_frame, text="📊 Dashboard", 
                                       command=self.api_client.open_dashboard)
        self.dashboard_btn.grid(row=0, column=3, padx=(0, 5))
        
        # Filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="5")
        filter_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filter_frame, text="Show Only:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.ticket_filter_var = tk.StringVar(value="My Tickets")
        self.ticket_filter_combo = ttk.Combobox(filter_frame, textvariable=self.ticket_filter_var, width=20,
                                               values=TICKET_FILTER_OPTIONS)
        self.ticket_filter_combo.grid(row=0, column=1, padx=(0, 10))
        self.ticket_filter_combo.bind("<<ComboboxSelected>>", self.search_filter.filter_tickets)
        
        ttk.Label(filter_frame, text="Issue Type:").grid(row=0, column=2, sticky=tk.W, padx=(10, 5))
        self.issue_type_var = tk.StringVar(value="All")
        self.issue_type_combo = ttk.Combobox(filter_frame, textvariable=self.issue_type_var, width=25,
                                           values=ISSUE_TYPE_FILTER_OPTIONS)
        self.issue_type_combo.grid(row=0, column=3, padx=(0, 10))
        self.issue_type_combo.bind("<<ComboboxSelected>>", self.search_filter.filter_tickets)
        
        # Hide completed tickets checkbox
        self.hide_completed_var = tk.BooleanVar(value=True)
        self.hide_completed_cb = ttk.Checkbutton(filter_frame, text="Hide Completed", 
                                               variable=self.hide_completed_var, 
                                               command=self.search_filter.filter_tickets)
        self.hide_completed_cb.grid(row=0, column=4, padx=(10, 0))
        
        # Tickets treeview
        tree_frame = ttk.Frame(main_frame)
        tree_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        columns = list(TREE_COLUMNS.keys())
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        for col, config in TREE_COLUMNS.items():
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_treeview(c, False))
            self.tree.column(col, width=config["width"], minwidth=config["minwidth"])
        
        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Right panel for ticket details and actions
        right_panel = ttk.Frame(main_frame)
        right_panel.grid(row=4, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Ticket details frame
        details_frame = ttk.LabelFrame(right_panel, text="Ticket Details", padding="5")
        details_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.details_text = scrolledtext.ScrolledText(details_frame, width=40, height=8, wrap=tk.WORD,
                                                    bg='#2d2d2d', fg='#ffffff', insertbackground='#ffffff',
                                                    font=('Segoe UI', 10))
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu for details text
        self.comment_system.create_text_context_menu(self.details_text)
        
        # Add drag-drop zone for file attachments
        drop_frame = ttk.LabelFrame(right_panel, text="Drag & Drop Files Here to Attach", padding="5")
        drop_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.drop_label = ttk.Label(drop_frame, text="📎 Drop files here or click to browse", 
                                   font=('Segoe UI', 10), cursor="hand2")
        self.drop_label.pack(pady=10)
        
        # Bind drag and drop events
        self.drop_label.bind("<Button-1>", self.attachment_manager.browse_files_to_attach)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(right_panel, text="Ticket Actions", padding="5")
        actions_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Action buttons
        button_row = ttk.Frame(actions_frame)
        button_row.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.close_btn = ttk.Button(button_row, text="Close Ticket", 
                                   command=self.ticket_ops.close_ticket, state="disabled")
        self.close_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.resolve_btn = ttk.Button(button_row, text="Resolve", 
                                     command=self.ticket_ops.resolve_ticket, state="disabled")
        self.resolve_btn.grid(row=0, column=1, padx=(0, 5))
        
        self.view_attachments_btn = ttk.Button(button_row, text="View Images", 
                                              command=self.view_attachments, state="disabled")
        self.view_attachments_btn.grid(row=0, column=2, padx=(5, 0))
        
        self.paste_screenshot_btn = ttk.Button(button_row, text="Paste Screenshot", 
                                              command=self.ticket_ops.paste_screenshot, state="disabled")
        self.paste_screenshot_btn.grid(row=0, column=3, padx=(5, 0))
        
        self.assign_to_me_btn = ttk.Button(button_row, text="Assign to Me", 
                                          command=self.ticket_ops.assign_to_me, state="disabled")
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
        self.comment_text.bind('<KeyRelease>', self.comment_system.on_comment_key_release)
        
        # Autocomplete listbox (initially hidden)
        self.autocomplete_frame = tk.Frame(actions_frame, bg='#2d2d2d', highlightthickness=1, 
                                         highlightbackground='#404040')
        self.autocomplete_listbox = tk.Listbox(self.autocomplete_frame, bg='#2d2d2d', fg='#ffffff', 
                                              selectbackground='#0d7377', height=5)
        self.autocomplete_listbox.pack(fill=tk.BOTH, expand=True)
        self.autocomplete_listbox.bind('<Double-1>', self.comment_system.on_autocomplete_select)
        self.autocomplete_listbox.bind('<Return>', self.comment_system.on_autocomplete_select)
        self.autocomplete_frame.grid_forget()  # Hide initially
        
        # Quick mention buttons
        mention_frame = ttk.LabelFrame(actions_frame, text="Quick Mentions", padding="5")
        mention_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Control buttons row
        control_row = ttk.Frame(mention_frame)
        control_row.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.manage_mentions_btn = ttk.Button(control_row, text="➕ Add/Remove", 
                                             command=self.user_management.manage_quick_mentions)
        self.manage_mentions_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.get_users_btn = ttk.Button(control_row, text="Get Team List", 
                                       command=self.user_management.get_team_members)
        self.get_users_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Frame for dynamic quick mention buttons
        self.quick_mentions_frame = ttk.Frame(mention_frame)
        self.quick_mentions_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Submit button
        self.submit_btn = ttk.Button(actions_frame, text="Add Comment", 
                                    command=self.comment_system.add_comment, state="disabled")
        self.submit_btn.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        
        # Comments history
        comments_frame = ttk.LabelFrame(right_panel, text="Recent Comments", padding="5")
        comments_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.comments_text = scrolledtext.ScrolledText(comments_frame, width=40, height=6,
                                                     bg='#3c3c3c', fg='#ffffff', insertbackground='#ffffff')
        self.comments_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add right-click context menu for comments text
        self.comment_system.create_text_context_menu(self.comments_text)
        
        # Bind treeview events
        self.tree.bind("<<TreeviewSelect>>", self.on_ticket_select)
        self.tree.bind("<Double-1>", self.on_ticket_double_click)
        self.tree.bind("<Button-3>", self.on_right_click)
        
        # Create context menu for right-click
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Assign to Me", command=self.ticket_ops.assign_to_me)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Ticket URL", command=self.search_filter.copy_ticket_url)
        self.context_menu.add_command(label="Open in Browser", command=self.search_filter.open_ticket_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Copy Ticket Key", command=self.search_filter.copy_ticket_key)
        
        # Status label
        self.status_label = ttk.Label(main_frame, text=UI_MESSAGES['ready'])
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=2)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)
        right_panel.rowconfigure(3, weight=1)
        details_frame.columnconfigure(0, weight=1)
        details_frame.rowconfigure(0, weight=1)
        actions_frame.columnconfigure(0, weight=1)
        comments_frame.columnconfigure(0, weight=1)
        comments_frame.rowconfigure(0, weight=1)
    
    def setup_cross_references(self):
        """Setup cross-references between modules after UI initialization"""
        # Set UI references for search/filter
        self.search_filter.set_ui_references(
            self.search_entry,
            self.ticket_filter_var,
            self.issue_type_var,
            self.hide_completed_var,
            self.get_user_email
        )
        
        # Set tree reference for search/filter
        self.search_filter.tree = self.tree
        
        # Set email callback for ticket operations
        self.ticket_ops.set_email_callback(self.get_user_email)
        
        # Set UI references for comment system
        self.comment_system.set_ui_references(self.comment_text, self.comments_text)
        self.comment_system.set_autocomplete_references(self.autocomplete_frame, self.autocomplete_listbox)
        
        # Set root window references
        self.attachment_manager.set_root_window(self.root)
        self.user_management.set_root_window(self.root)
        self.user_management.set_quick_mentions_frame(self.quick_mentions_frame)
        
        # Setup attachment drag and drop
        self.attachment_manager.setup_drag_drop()
        
        # Initialize HTML viewer
        self.html_viewer = HTMLTicketViewer(
            self.api_client,
            self.root,
            self.ticket_ops,
            self.comment_system
        )
        
        # Setup user management callbacks
        self.user_management.set_mention_callback(self.comment_system.add_mention)
        
        # Load and refresh quick mentions
        self.user_management.load_quick_mentions()
        self.user_management.refresh_quick_mention_buttons()
        
        # Load available users for autocomplete
        self.comment_system.load_available_users()
    
    def get_user_email(self):
        """Get user email for API client"""
        return self.email_entry.get()
    
    def update_status(self, message):
        """Update status label"""
        self.status_label.config(text=message)
    
    def load_all_tickets_threaded(self):
        """Load tickets in background thread"""
        self.load_all_btn.config(state="disabled")
        self.update_status(UI_MESSAGES['loading'])
        threading.Thread(target=self.load_all_tickets, daemon=True).start()
    
    def load_all_tickets(self):
        """Load all tickets using API client"""
        data = self.api_client.load_all_tickets()
        
        if data and 'issues' in data:
            self.root.after(0, self.update_ticket_list, data['issues'])
            self.root.after(0, lambda: self.update_status(f"Loaded {len(data['issues'])} tickets"))
            # Apply default filter after loading
            self.root.after(100, self.search_filter.filter_tickets)
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
        self.search_filter.set_tickets(issues)
        
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
            created = fields.get('created', '')[:10] if fields.get('created') else ''
            
            self.tree.insert('', 'end', values=(key, issue_type, summary[:50], status, 
                                              priority, reporter, assignee, created))
    
    def on_ticket_select(self, event):
        """Handle ticket selection"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = selection[0]
        ticket_key = self.tree.item(item)['values'][0]
        
        # Find the ticket in our stored data
        for issue in self.all_tickets:
            if issue.get('key') == ticket_key:
                self.current_ticket = issue
                self.show_ticket_details_fast(issue)
                
                # Update all managers with current ticket
                self.ticket_ops.set_current_ticket(issue)
                self.comment_system.set_current_ticket(issue)
                self.attachment_manager.set_current_ticket(issue)
                
                # Enable buttons
                self.enable_ticket_actions()
                
                # Load full details and comments in background
                self.load_full_ticket_details(ticket_key)
                break
    
    def show_ticket_details_fast(self, issue):
        """Show basic ticket details immediately (fast display)"""
        fields = issue.get('fields', {})
        
        details = []
        details.append(f"Key: {issue.get('key', 'Unknown')}")
        details.append(f"Summary: {fields.get('summary', 'No summary')}")
        details.append(f"Status: {fields.get('status', {}).get('name', 'Unknown')}")
        details.append(f"Type: {fields.get('issuetype', {}).get('name', 'Unknown')}")
        
        priority = fields.get('priority')
        if priority:
            details.append(f"Priority: {priority.get('name', 'Not set')}")
        
        assignee = fields.get('assignee')
        if assignee:
            details.append(f"Assignee: {assignee.get('displayName', 'Unknown')}")
        else:
            details.append("Assignee: Unassigned")
        
        description = fields.get('description', '')
        if description:
            details.append(f"\nDescription:\n{description}")
        
        self.details_text.config(state='normal')
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(1.0, '\n'.join(details))
        self.details_text.config(state='disabled')
    
    def load_full_ticket_details(self, ticket_key):
        """Load full ticket details including comments in background"""
        def do_load():
            # Get full ticket details
            full_ticket = self.api_client.get_ticket_details(ticket_key)
            if full_ticket:
                self.current_ticket = full_ticket
                
                # Update all managers
                self.root.after(0, lambda: self.ticket_ops.set_current_ticket(full_ticket))
                self.root.after(0, lambda: self.comment_system.set_current_ticket(full_ticket))
                self.root.after(0, lambda: self.attachment_manager.set_current_ticket(full_ticket))
                
                # Update HTML viewer if open
                if self.html_viewer and self.html_viewer.is_open():
                    self.root.after(0, lambda: self.html_viewer.update_html_viewer(full_ticket))
            
            # Load comments
            self.comment_system.load_comments(ticket_key)
        
        threading.Thread(target=do_load, daemon=True).start()
    
    def enable_ticket_actions(self):
        """Enable ticket action buttons"""
        self.close_btn.config(state="normal")
        self.resolve_btn.config(state="normal")
        self.view_attachments_btn.config(state="normal")
        self.paste_screenshot_btn.config(state="normal")
        self.assign_to_me_btn.config(state="normal")
        self.submit_btn.config(state="normal")
    
    def on_ticket_double_click(self, event):
        """Handle double-click on ticket - open HTML viewer"""
        self.on_ticket_select(event)
        if self.current_ticket:
            self.open_html_viewer()
            if self.html_viewer:
                self.html_viewer.update_html_viewer(self.current_ticket)
    
    def on_right_click(self, event):
        """Handle right-click on ticket"""
        # Select the item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree.focus(item)
            # Show context menu
            self.context_menu.post(event.x_root, event.y_root)
    
    def view_attachments(self):
        """View attachments for current ticket"""
        self.attachment_manager.view_attachments(self.view_attachments_btn)
    
    def open_html_viewer(self):
        """Open HTML viewer window"""
        if self.html_viewer:
            self.html_viewer.open_html_viewer()
            if self.current_ticket:
                self.html_viewer.update_html_viewer(self.current_ticket)
    
    def open_create_ticket_window(self):
        """Open window for creating new tickets"""
        # This would implement ticket creation UI
        messagebox.showinfo("Create Ticket", "Ticket creation window would open here")
    
    def sort_treeview(self, col, reverse):
        """Sort treeview by column"""
        # Get current sort state
        current_reverse = self.sort_reverse.get(col, False)
        reverse = not current_reverse
        self.sort_reverse[col] = reverse
        
        # Get all items
        items = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        
        # Sort based on column type
        if col in ['Key', 'Created']:
            if col == 'Key':
                # Sort by ticket number
                items.sort(key=lambda x: int(x[0].split('-')[-1]) if '-' in x[0] else 0, reverse=reverse)
            else:
                # Sort by date
                items.sort(key=lambda x: x[0], reverse=reverse)
        else:
            # Sort alphabetically
            items.sort(key=lambda x: x[0].lower(), reverse=reverse)
        
        # Rearrange items
        for index, (val, child) in enumerate(items):
            self.tree.move(child, '', index)
        
        # Update column heading to show sort direction
        for column in TREE_COLUMNS:
            if column == col:
                direction = " ↓" if reverse else " ↑"
                self.tree.heading(column, text=f"{column}{direction}")
            else:
                self.tree.heading(column, text=column)