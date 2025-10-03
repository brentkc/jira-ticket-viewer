import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
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
import time
import keyring
import logging
from license_validator import LicenseValidator
from reminder_manager import ReminderManager
from ai_summary_dialog import show_ai_summary
from ai_settings_dialog import show_ai_settings
from comment_monitor import CommentMonitor

# Setup logging for enhanced version
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'jira_debug.log')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)

class JiraTicketViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Jira Ticket Viewer - Enhanced Edition")
        
        # Maximize window to full screen
        self.root.state('zoomed')  # Windows maximization
        
        # Alternative for other platforms
        try:
            self.root.attributes('-zoomed', True)  # Linux
        except:
            try:
                self.root.attributes('-fullscreen', False)  # macOS
            except:
                self.root.geometry("1920x1080")  # Fallback
        
        # Set minimum size
        self.root.minsize(1200, 800)

        # Maximize window on startup
        try:
            # For Windows
            self.root.state('zoomed')
        except:
            try:
                # For Linux
                self.root.attributes('-zoomed', True)
            except:
                # Fallback - set to large size
                self.root.geometry("1600x900")
        
        # Initialize state variables
        self.selected_ticket = None
        self.context_toolbar_visible = False
        self.current_ticket = None
        
        # Default Jira configuration (will be overridden by settings)
        self.jira_url = ""
        self.api_token = ""
        self.project_key = ""
        self.user_email = ""
        
        # Issue types
        self.issue_types = {
            "[System] Incident": "11395",
            "[System] Service request": "11396"
        }
        
        # Initialize license validator (customer version - cannot generate licenses)
        self.license_manager = LicenseValidator()
        
        # Initialize reminder manager - TEMPORARILY DISABLED
        # self.reminder_manager = ReminderManager(parent_app=self)
        self.reminder_manager = None  # Disabled to stop alerts

        # Initialize comment monitor (temporarily disabled to prevent UI lockup)
        # self.comment_monitor = CommentMonitor(self)
        self.comment_monitor = None

        # Load user settings
        self.load_user_settings()

        # Configure dark mode and setup UI
        self.setup_dark_mode()
        self.setup_ui()

        # Check license status after UI is ready
        self.root.after(100, self.check_license_on_startup)

        # Auto-load tickets on startup
        self.root.after(1000, self.load_all_tickets_threaded)

        # Start comment monitoring after tickets are loaded (disabled)
        # self.root.after(5000, self.comment_monitor.start_monitoring)
    
    def show_copyable_error(self, title, message):
        """Show error dialog with copyable text"""
        error_window = tk.Toplevel(self.root)
        error_window.title(title)
        error_window.geometry("600x400")
        error_window.resizable(True, True)
        
        # Center the window
        error_window.transient(self.root)
        error_window.grab_set()
        
        # Error message text
        text_frame = ttk.Frame(error_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        error_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD, font=('Consolas', 10))
        error_text.pack(fill=tk.BOTH, expand=True)
        error_text.insert(tk.END, message)
        error_text.config(state=tk.DISABLED)
        
        # Buttons
        button_frame = ttk.Frame(error_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        def copy_to_clipboard():
            error_window.clipboard_clear()
            error_window.clipboard_append(message)
            messagebox.showinfo("Copied", "Error message copied to clipboard!")
        
        def select_all():
            error_text.config(state=tk.NORMAL)
            error_text.tag_add(tk.SEL, "1.0", tk.END)
            error_text.mark_set(tk.INSERT, "1.0")
            error_text.see(tk.INSERT)
            error_text.config(state=tk.DISABLED)
        
        ttk.Button(button_frame, text="Copy to Clipboard", command=copy_to_clipboard).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Close", command=error_window.destroy).pack(side=tk.RIGHT)
    
    def load_user_settings(self):
        """Load user settings from Windows Credential Manager (secure)"""
        try:
            # Load non-sensitive settings from basic storage
            basic_settings = self._load_basic_settings()
            self.jira_url = basic_settings.get('jira_url', self.jira_url)
            self.project_key = basic_settings.get('project_key', self.project_key)
            self.user_email = basic_settings.get('user_email', self.user_email)
            
            # Load sensitive API token from Windows Credential Manager
            if self.user_email:
                try:
                    stored_token = keyring.get_password("JiraTicketViewer", self.user_email)
                    if stored_token:
                        self.api_token = stored_token
                except Exception as e:
                    print(f"Could not load stored token: {e}")
                    
        except Exception as e:
            print(f"Error loading settings: {e}")

    def _load_basic_settings(self):
        """Load non-sensitive settings from file"""
        import json
        import os
        
        # Use user's AppData directory so settings persist across different app locations
        app_data = os.path.expanduser("~/.jira_ticket_viewer")
        if not os.path.exists(app_data):
            os.makedirs(app_data, exist_ok=True)
        
        settings_file = os.path.join(app_data, 'jira_basic_settings.json')
        
        # Try new location first, then fallback to old location for migration
        if not os.path.exists(settings_file):
            old_settings_file = os.path.join(os.path.dirname(__file__), 'jira_basic_settings.json')
            if os.path.exists(old_settings_file):
                # Migrate old settings to new location
                try:
                    with open(old_settings_file, 'r') as f:
                        data = json.load(f)
                    with open(settings_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    print(f"Migrated settings to: {settings_file}")
                except Exception as e:
                    print(f"Error migrating settings: {e}")
        
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading basic settings: {e}")
        return {}
            
    def save_user_settings(self):
        """Save user settings securely"""
        try:
            # Save non-sensitive settings to file
            basic_settings = {
                'jira_url': self.jira_url,
                'project_key': self.project_key,
                'user_email': self.user_email
            }
            
            # Use user's AppData directory so settings persist across different app locations
            app_data = os.path.expanduser("~/.jira_ticket_viewer")
            if not os.path.exists(app_data):
                os.makedirs(app_data, exist_ok=True)
            
            settings_file = os.path.join(app_data, 'jira_basic_settings.json')
            with open(settings_file, 'w') as f:
                json.dump(basic_settings, f, indent=2)
                
            print(f"Settings saved to: {settings_file}")
            
            # Save sensitive API token to Windows Credential Manager
            if self.user_email and self.api_token:
                keyring.set_password("JiraTicketViewer", self.user_email, self.api_token)
                
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            return False
    
    def setup_dark_mode(self):
        """Configure modern dark mode"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern colors
        bg_primary = '#1a1a1a'
        bg_button = '#0078d4'
        bg_button_hover = '#106ebe'
        text_primary = '#ffffff'
        
        style.configure('TFrame', background=bg_primary)
        style.configure('TLabel', background=bg_primary, foreground=text_primary)
        style.configure('TButton', background=bg_button, foreground=text_primary, borderwidth=0, 
                       focuscolor='none', relief='flat', padding=(12, 8))
        style.map('TButton', background=[('active', bg_button_hover)])
        
        self.root.configure(bg=bg_primary)

    def setup_ui(self):
        """Setup enhanced UI with all features"""
        # Configure root grid weights first for proper expansion
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main container - reduced padding for more space
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure main_frame grid weights for proper content expansion
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Row 3 is the content_frame
        
        # Top toolbar
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Search on left
        search_container = ttk.Frame(toolbar_frame)
        search_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.search_entry = ttk.Entry(search_container, width=40, font=('Segoe UI', 11))
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.search_entry.bind('<Return>', self.search_tickets)
        self.search_entry.insert(0, "🔍 Search tickets...")
        self.search_entry.bind('<FocusIn>', self.on_search_focus)
        self.search_entry.bind('<FocusOut>', self.on_search_unfocus)
        
        # New Ticket button - prominent position on left
        self.new_ticket_btn = ttk.Button(search_container, text="➕ New Ticket", command=self.create_new_ticket)
        self.new_ticket_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh button
        self.refresh_btn = ttk.Button(search_container, text="🔄 Refresh", command=self.refresh_tickets)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reminders button - TEMPORARILY DISABLED
        # self.reminders_btn = ttk.Button(search_container, text="📅 Reminders", command=self.show_reminders)
        # self.reminders_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Actions on right
        primary_actions = ttk.Frame(toolbar_frame)
        primary_actions.pack(side=tk.RIGHT)
        
        self.knowledge_btn = ttk.Button(primary_actions, text="📚 Knowledge Base", command=self.open_knowledge_editor)
        self.knowledge_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.ai_settings_btn = ttk.Button(primary_actions, text="🤖 AI Settings", command=self.open_ai_settings)
        self.ai_settings_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.settings_btn = ttk.Button(primary_actions, text="⚙️ Settings", command=self.open_settings)
        self.settings_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.debug_btn = ttk.Button(primary_actions, text="🔍 Debug Log", command=self.show_debug_log)
        self.debug_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.dashboard_btn = ttk.Button(primary_actions, text="📊 Dashboard", command=self.open_dashboard)
        self.dashboard_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Filters bar
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(filter_frame, text="Show:").pack(side=tk.LEFT, padx=(0, 5))
        self.ticket_filter_var = tk.StringVar(value="My Tickets")
        self.ticket_filter_combo = ttk.Combobox(filter_frame, textvariable=self.ticket_filter_var, width=15,
                                               values=["My Tickets", "All Open", "Unassigned", "All Tickets"])
        self.ticket_filter_combo.pack(side=tk.LEFT, padx=(0, 15))
        self.ticket_filter_combo.bind("<<ComboboxSelected>>", self.filter_tickets)
        
        self.hide_completed_var = tk.BooleanVar(value=True)
        self.hide_completed_cb = ttk.Checkbutton(filter_frame, text="Hide Completed", 
                                               variable=self.hide_completed_var, command=self.filter_tickets)
        self.hide_completed_cb.pack(side=tk.LEFT, padx=(15, 0))
        
        # User info
        user_info = ttk.Frame(filter_frame)
        user_info.pack(side=tk.RIGHT)
        self.user_info_label = ttk.Label(user_info, text=f"User: {self.user_email}", font=('Segoe UI', 9))
        self.user_info_label.pack(side=tk.RIGHT, padx=(15, 0))
        
        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.status_label = ttk.Label(status_frame, text="Ready to load tickets...", font=('Segoe UI', 9))
        self.status_label.pack(side=tk.LEFT)
        
        self.refresh_btn = ttk.Button(status_frame, text="🔄", width=3, command=self.load_all_tickets_threaded)
        self.refresh_btn.pack(side=tk.RIGHT)
        
        # Main content
        content_frame = ttk.Frame(main_frame)
        content_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        content_frame.columnconfigure(0, weight=2)
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        # Left panel - Tickets list
        tickets_frame = ttk.Frame(content_frame)
        tickets_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        tickets_frame.rowconfigure(0, weight=1)
        tickets_frame.columnconfigure(0, weight=1)
        
        # Ticket tree - remove fixed height to allow full expansion
        columns = ("Key", "Priority", "Summary", "Status", "Assignee", "Reporter", "Age")
        self.tree = ttk.Treeview(tickets_frame, columns=columns, show="headings")
        
        # Column configuration
        self.tree.heading("Key", text="ID")
        self.tree.column("Key", width=70, minwidth=70)
        
        self.tree.heading("Priority", text="⚡")
        self.tree.column("Priority", width=40, minwidth=40)
        
        self.tree.heading("Summary", text="Summary")
        self.tree.column("Summary", width=600, minwidth=400)  # Wider for larger screens
        
        self.tree.heading("Status", text="Status")
        self.tree.column("Status", width=100, minwidth=80)
        
        self.tree.heading("Assignee", text="Assignee")
        self.tree.column("Assignee", width=120, minwidth=100)
        
        self.tree.heading("Reporter", text="Reporter")
        self.tree.column("Reporter", width=120, minwidth=100)
        
        self.tree.heading("Age", text="Age")
        self.tree.column("Age", width=60, minwidth=60)
        
        # Add sorting functionality to all columns
        for col in columns:
            self.tree.heading(col, command=lambda c=col: self.sort_treeview(c))
        
        # Scrollbar
        tree_scrollbar = ttk.Scrollbar(tickets_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Visual tags
        self.tree.tag_configure('sla_missed', background='#4a2828', foreground='#ff9999')
        self.tree.tag_configure('critical', background='#3d1a1a', foreground='#ff6b6b')
        self.tree.tag_configure('high', background='#3d2a1a', foreground='#ffa726')
        
        # Right panel
        right_panel = ttk.Frame(content_frame)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.rowconfigure(1, weight=1)
        
        # Context toolbar (hidden initially)
        self.context_toolbar = ttk.Frame(right_panel)
        self.context_toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.context_toolbar.grid_remove()
        
        # Quick actions
        self.quick_resolve_btn = ttk.Button(self.context_toolbar, text="✅ Resolve", command=self.resolve_ticket, state="disabled")
        self.quick_resolve_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.quick_assign_btn = ttk.Button(self.context_toolbar, text="👤 Assign to Me", command=self.assign_to_me, state="disabled")
        self.quick_assign_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.assign_will_btn = ttk.Button(self.context_toolbar, text="👤 Assign to Will", command=self.assign_to_will, state="disabled")
        self.assign_will_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.ai_summary_btn = ttk.Button(self.context_toolbar, text="🤖 AI Summary", command=self.ai_summarize_ticket, state="disabled")
        self.ai_summary_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.view_comments_btn = ttk.Button(self.context_toolbar, text="💬 View Comments", command=self.view_comments, state="disabled")
        self.view_comments_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Details panel
        details_frame = ttk.LabelFrame(right_panel, text="📋 Details", padding="10")
        details_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        details_frame.rowconfigure(0, weight=1)
        details_frame.columnconfigure(0, weight=1)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, width=40, height=15, wrap=tk.WORD,
                                                    bg='#2d2d2d', fg='#ffffff', font=('Segoe UI', 10), state='disabled')
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Comment area
        comment_frame = ttk.LabelFrame(right_panel, text="💬 Quick Comment", padding="10")
        comment_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        comment_frame.columnconfigure(0, weight=1)
        
        self.comment_entry = scrolledtext.ScrolledText(comment_frame, height=4, wrap=tk.WORD,
                                                     bg='#2d2d2d', fg='#ffffff', font=('Segoe UI', 10))
        self.comment_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        comment_buttons = ttk.Frame(comment_frame)
        comment_buttons.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.submit_btn = ttk.Button(comment_buttons, text="💬 Add Comment", command=self.add_comment, state="disabled")
        self.submit_btn.pack(side=tk.RIGHT)
        
        # Advanced actions
        advanced_frame = ttk.LabelFrame(right_panel, text="⚡ More Actions", padding="10")
        advanced_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        advanced_row1 = ttk.Frame(advanced_frame)
        advanced_row1.pack(fill=tk.X, pady=(0, 5))
        
        self.close_btn = ttk.Button(advanced_row1, text="❌ Close", command=self.close_ticket, state="disabled")
        self.close_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.open_btn = ttk.Button(advanced_row1, text="🔓 Reopen", command=self.open_ticket, state="disabled")
        self.open_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.browser_btn = ttk.Button(advanced_row1, text="🌐 Browser", command=self.open_ticket_in_browser, state="disabled")
        self.browser_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.status_btn = ttk.Button(advanced_row1, text="🔄 Status", command=self.change_ticket_status, state="disabled")
        self.status_btn.pack(side=tk.LEFT)
        
        # Store action buttons
        self.all_action_buttons = [
            self.quick_resolve_btn, self.quick_assign_btn, self.assign_will_btn, self.ai_summary_btn, self.view_comments_btn,
            self.submit_btn, self.close_btn, self.open_btn, self.browser_btn, self.status_btn
        ]

        # Setup events and bindings
        self.tree.bind('<<TreeviewSelect>>', self.on_ticket_select)
        self.tree.bind('<Double-1>', self.on_ticket_double_click)
        self.tree.bind('<Button-3>', self.on_ticket_right_click)

        # Setup context menu
        self.setup_context_menu()

        # Keyboard shortcuts
        self.setup_keyboard_shortcuts()

        # Aliases for compatibility
        self.comment_text = self.comment_entry
        self.comments_text = self.details_text

    def view_comments(self):
        """Load and display comments for current ticket"""
        if self.current_ticket:
            self.load_ticket_details(load_comments=True)

    def setup_events(self):
        """Setup events"""
        self.tree.bind('<<TreeviewSelect>>', self.on_ticket_select)
        self.tree.bind('<Double-1>', self.on_ticket_double_click)
        self.tree.bind('<Button-3>', self.on_ticket_right_click)
        
        # Setup context menu
        self.setup_context_menu()
        
        # Grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        
        # Keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Aliases for compatibility
        self.comment_text = self.comment_entry
        self.comments_text = self.details_text

    def setup_context_menu(self):
        """Setup right-click context menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="➕ New Ticket", command=self.create_new_ticket)
        self.context_menu.add_separator()
        # self.context_menu.add_command(label="📅 Create Reminders", command=self.create_reminders_from_current_ticket)  # DISABLED
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🌐 Open in Browser", command=self.open_ticket_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="👤 Assign to Me", command=self.assign_to_me)
        self.context_menu.add_command(label="👤 Assign to Will", command=self.assign_to_will)
        self.context_menu.add_command(label="✅ Resolve", command=self.resolve_ticket)
        self.context_menu.add_command(label="🔓 Reopen", command=self.open_ticket)
        self.context_menu.add_command(label="🔄 Change Status", command=self.change_ticket_status)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Duplicate Ticket", command=self.duplicate_ticket)
        self.context_menu.add_command(label="🤖 AI Summarize", command=self.ai_summarize_ticket)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📎 Copy URL", command=self.copy_ticket_url)
        self.context_menu.add_command(label="🔑 Copy Key", command=self.copy_ticket_key)

    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts"""
        self.root.bind('<Control-r>', lambda e: self.load_all_tickets_threaded())
        self.root.bind('<F5>', lambda e: self.load_all_tickets_threaded())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())

    def on_search_focus(self, event):
        """Clear placeholder on focus"""
        if self.search_entry.get() == "🔍 Search tickets...":
            self.search_entry.delete(0, tk.END)
            
    def on_search_unfocus(self, event):
        """Restore placeholder if empty"""
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, "🔍 Search tickets...")

    def show_context_toolbar(self):
        """Show contextual toolbar"""
        self.context_toolbar.grid()
        
    def hide_context_toolbar(self):
        """Hide contextual toolbar"""
        self.context_toolbar.grid_remove()
        
    def enable_all_actions(self):
        """Enable action buttons"""
        for btn in self.all_action_buttons:
            btn.config(state="normal")
            
    def disable_all_actions(self):
        """Disable action buttons"""
        for btn in self.all_action_buttons:
            btn.config(state="disabled")

    def is_sla_missed(self, issue):
        """Check if ticket missed SLA"""
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
            
            # 4 days = 96 hours for all priorities
            sla_window = 96
            
            return hours_since_created > sla_window
        except:
            return False

    # API Methods
    def make_jira_request(self, endpoint, method="GET", params=None, data=None, files=None):
        """Make authenticated request to Jira API with timeout and retry logic"""
        url = f"{self.jira_url}/rest/api/3/{endpoint}"
        auth = HTTPBasicAuth(self.user_email, self.api_token)
        headers = {"Accept": "application/json"}
        
        if method in ["POST", "PUT"] and not files:
            headers["Content-Type"] = "application/json"
        
        # Debug logging
        print(f"[DEBUG] Making {method} request to: {url}")
        if data:
            print(f"[DEBUG] Request data: {data}")
        
        # Retry logic for server errors
        max_retries = 3
        timeout = 30  # 30 second timeout
        
        for attempt in range(max_retries):
            try:
                if method == "GET":
                    response = requests.get(url, auth=auth, headers=headers, params=params, timeout=timeout)
                elif method == "POST":
                    if files:
                        response = requests.post(url, auth=auth, files=files, data=data, timeout=timeout)
                    else:
                        response = requests.post(url, auth=auth, headers=headers, json=data, timeout=timeout)
                elif method == "PUT":
                    response = requests.put(url, auth=auth, headers=headers, json=data, timeout=timeout)
                else:
                    return None
                
                # Debug response
                print(f"[DEBUG] Response status: {response.status_code}")
                try:
                    print(f"[DEBUG] Response text length: {len(response.text)} characters")
                    # Only print first 500 chars to avoid encoding issues
                    if len(response.text) > 500:
                        print(f"[DEBUG] Response text (truncated): {response.text[:500]}...")
                    else:
                        print(f"[DEBUG] Response text: {response.text}")
                except UnicodeEncodeError:
                    print("[DEBUG] Response contains characters that cannot be displayed")
                
                response.raise_for_status()
                
                if response.text.strip():
                    return response.json()
                else:
                    return {"success": True}
                    
            except requests.exceptions.Timeout:
                print(f"[DEBUG] Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    error_msg = f"Request timed out after {max_retries} attempts (timeout: {timeout}s)"
                    print(f"[DEBUG] {error_msg}")
                    self.show_copyable_error("Timeout Error", error_msg)
                    return None
                time.sleep(2)  # Wait before retry
                continue
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    print(f"[DEBUG] Server error {e.response.status_code} on attempt {attempt + 1}/{max_retries}, retrying...")
                    time.sleep(2)  # Wait before retry
                    continue
                else:
                    error_msg = f"API Error: {str(e)}"
                    if hasattr(e, 'response') and e.response is not None:
                        error_msg += f"\nStatus Code: {e.response.status_code}"
                        error_msg += f"\nResponse: {e.response.text}"
                        error_msg += f"\nURL: {url}"
                        error_msg += f"\nMethod: {method}"
                        if data:
                            error_msg += f"\nRequest Data: {json.dumps(data, indent=2)}"
                    print(f"[DEBUG] {error_msg}")
                    self.show_copyable_error("API Error", error_msg)
                    return None
                    
            except requests.exceptions.RequestException as e:
                error_msg = f"API Error: {str(e)}"
                if hasattr(e, 'response') and e.response is not None:
                    error_msg += f"\nStatus Code: {e.response.status_code}"
                    error_msg += f"\nResponse: {e.response.text}"
                    error_msg += f"\nURL: {url}"
                    error_msg += f"\nMethod: {method}"
                    if data:
                        error_msg += f"\nRequest Data: {json.dumps(data, indent=2)}"
                print(f"[DEBUG] {error_msg}")
                self.show_copyable_error("API Error", error_msg)
                return None
                
            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                print(f"[DEBUG] {error_msg}")
                self.show_copyable_error("Error", error_msg)
                return None

    def load_all_tickets_threaded(self):
        """Load tickets in background thread"""
        self.refresh_btn.config(state="disabled")
        self.status_label.config(text="Loading tickets...")
        threading.Thread(target=self.load_all_tickets, daemon=True).start()
        
    def load_all_tickets(self):
        """Load all tickets from Jira"""
        try:
            issue_type_ids = list(self.issue_types.values())
            jql = f'project = {self.project_key} AND issuetype in ({",".join(issue_type_ids)})'
            
            # API v3 requires explicit field specification
            fields = "summary,status,priority,assignee,reporter,created,description"
            params = {
                'jql': jql, 
                'maxResults': 100, 
                'startAt': 0,
                'fields': fields
            }
            data = self.make_jira_request("search/jql", params=params)
            
            if data and 'issues' in data:
                self.root.after(0, self.update_ticket_list, data['issues'])
                self.root.after(0, lambda: self.status_label.config(text=f"Loaded {len(data['issues'])} tickets"))
            else:
                self.root.after(0, lambda: self.status_label.config(text="Failed to load tickets"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state="normal"))
            self.root.after(100, self.filter_tickets)

    def refresh_tickets(self):
        """Refresh ticket list by reloading from Jira"""
        self.load_all_tickets_threaded()

    def update_ticket_list(self, issues):
        """Update treeview with tickets"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.all_tickets = issues
        
        for issue in issues:
            fields = issue.get('fields', {})
            
            key = issue.get('key', 'Unknown')
            
            priority = fields.get('priority', {})
            priority_name = priority.get('name', 'Unknown') if priority else 'Unknown'
            priority_symbol = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}.get(priority_name.lower(), '⚪')
            
            summary = fields.get('summary', 'No summary')
            
            status = fields.get('status', {})
            status_name = status.get('name', 'Unknown') if status else 'Unknown'
            
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            
            reporter = fields.get('reporter')
            reporter_name = reporter.get('displayName', 'Unknown') if reporter else 'Unknown'
            
            # Calculate age
            created = fields.get('created', '')
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    now = datetime.now(created_dt.tzinfo)
                    age_hours = (now - created_dt).total_seconds() / 3600
                    if age_hours < 24:
                        age_str = f"{int(age_hours)}h"
                    elif age_hours < 168:
                        age_str = f"{int(age_hours/24)}d"
                    else:
                        age_str = f"{int(age_hours/168)}w"
                except:
                    age_str = "?"
            else:
                age_str = "?"
            
            values = (key, priority_symbol, summary, status_name, assignee_name, reporter_name, age_str)
            
            # Tags
            tags = [key]
            if self.is_sla_missed(issue):
                tags.append('sla_missed')
            elif priority_name.lower() == 'critical':
                tags.append('critical')
            elif priority_name.lower() == 'high':
                tags.append('high')
            
            self.tree.insert("", "end", values=values, tags=tags)

    def filter_tickets(self, event=None):
        """Filter tickets based on criteria"""
        if not hasattr(self, 'all_tickets') or not self.all_tickets:
            return
            
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        ticket_filter = self.ticket_filter_var.get()
        hide_completed = self.hide_completed_var.get()
        user_email = self.user_email
        
        completed_statuses = ['done', 'closed', 'resolved', 'complete', 'completed', 'finished']
        
        tickets_to_show = []
        for issue in self.all_tickets:
            fields = issue.get('fields', {})
            
            # Apply main filter first
            if ticket_filter == "My Tickets":
                reporter = fields.get('reporter')
                reporter_email = reporter.get('emailAddress', '') if reporter else ''
                assignee = fields.get('assignee')
                assignee_email = assignee.get('emailAddress', '') if assignee else ''
                
                if user_email not in [reporter_email, assignee_email]:
                    continue
                    
            elif ticket_filter == "All Open":
                status = fields.get('status', {})
                status_name = status.get('name', '').lower() if status else ''
                is_completed = any(completed_status in status_name for completed_status in completed_statuses)
                if is_completed:
                    continue
                    
            elif ticket_filter == "Unassigned":
                assignee = fields.get('assignee')
                # Skip tickets that HAVE an assignee (we want unassigned ones)
                if assignee is not None:
                    continue
            
            # Apply completed filter (unless we're already filtering for open tickets)
            if hide_completed and ticket_filter != "All Open":
                status = fields.get('status', {})
                status_name = status.get('name', '').lower() if status else ''
                is_completed = any(completed_status in status_name for completed_status in completed_statuses)
                if is_completed:
                    continue
            
            tickets_to_show.append(issue)
        
        # Store filtered tickets for reference
        self.filtered_tickets = tickets_to_show
        
        # Update display with filtered results - call the actual update method
        self.display_filtered_tickets(tickets_to_show)
        
        # Update status message
        filter_text = f" ({ticket_filter})" if ticket_filter != "All Tickets" else ""
        completed_text = " (hiding completed)" if hide_completed and ticket_filter != "All Open" else ""
        self.status_label.config(text=f"Showing {len(tickets_to_show)} tickets{filter_text}{completed_text}")
    
    def display_filtered_tickets(self, tickets_to_show):
        """Display the filtered tickets in the tree"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add filtered tickets to treeview
        for issue in tickets_to_show:
            fields = issue.get('fields', {})
            
            key = issue.get('key', 'Unknown')
            
            priority = fields.get('priority', {})
            priority_name = priority.get('name', 'Unknown') if priority else 'Unknown'
            priority_symbol = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}.get(priority_name.lower(), '⚪')
            
            summary = fields.get('summary', 'No summary')
            
            status = fields.get('status', {})
            status_name = status.get('name', 'Unknown') if status else 'Unknown'
            
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            
            reporter = fields.get('reporter')
            reporter_name = reporter.get('displayName', 'Unknown') if reporter else 'Unknown'
            
            # Calculate age
            created = fields.get('created', '')
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    now = datetime.now(created_dt.tzinfo)
                    age_hours = (now - created_dt).total_seconds() / 3600
                    if age_hours < 24:
                        age_str = f"{int(age_hours)}h"
                    elif age_hours < 168:
                        age_str = f"{int(age_hours/24)}d"
                    else:
                        age_str = f"{int(age_hours/168)}w"
                except:
                    age_str = "?"
            else:
                age_str = "?"
            
            values = (key, priority_symbol, summary, status_name, assignee_name, reporter_name, age_str)
            
            # Tags for visual styling
            tags = [key]
            if self.is_sla_missed(issue):
                tags.append('sla_missed')
            elif priority_name.lower() == 'critical':
                tags.append('critical')
            elif priority_name.lower() == 'high':
                tags.append('high')
            
            self.tree.insert("", "end", values=values, tags=tags)

    def search_tickets(self, event=None):
        """Enhanced search functionality"""
        search_term = self.search_entry.get().strip()
        if search_term == "🔍 Search tickets..." or not search_term:
            self.filter_tickets()
            return
            
        if not hasattr(self, 'all_tickets') or not self.all_tickets:
            return
            
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        matching_tickets = []
        search_lower = search_term.lower()
        
        for issue in self.all_tickets:
            fields = issue.get('fields', {})
            key = issue.get('key', '').lower()
            summary = fields.get('summary', '').lower()
            
            if search_lower in key or search_lower in summary:
                matching_tickets.append(issue)
                
        self.update_ticket_list(matching_tickets)
        self.status_label.config(text=f"Found {len(matching_tickets)} tickets matching '{search_term}'")

    # Event Handlers
    def on_ticket_select(self, event):
        """Handle ticket selection"""
        print(f"[DEBUG] on_ticket_select called")
        selection = self.tree.selection()
        if not selection:
            print("[DEBUG] No selection")
            self.current_ticket = None
            self.hide_context_toolbar()
            self.disable_all_actions()
            return

        item = selection[0]
        ticket_key = self.tree.item(item)['values'][0]
        print(f"[DEBUG] Selected ticket: {ticket_key}")
        
        # Find the ticket in all_tickets OR in the currently filtered list
        self.current_ticket = None
        if hasattr(self, 'all_tickets'):
            for issue in self.all_tickets:
                if issue.get('key') == ticket_key:
                    self.current_ticket = issue
                    break
        
        # If not found in all_tickets, try the currently displayed filtered list
        if not self.current_ticket and hasattr(self, 'filtered_tickets'):
            for issue in self.filtered_tickets:
                if issue.get('key') == ticket_key:
                    self.current_ticket = issue
                    break
                    
        # If still not found, try to fetch from API
        if not self.current_ticket:
            self.current_ticket = self.fetch_ticket_details(ticket_key)
        
        if self.current_ticket:
            self.show_context_toolbar()
            self.enable_all_actions()
            self.load_ticket_details(load_comments=False)  # Don't auto-load comments for speed
        else:
            self.hide_context_toolbar()
            self.disable_all_actions()
    
    def fetch_ticket_details(self, ticket_key):
        """Fetch ticket details from Jira API"""
        try:
            ticket_data = self.make_jira_request(f"issue/{ticket_key}")
            return ticket_data
        except Exception as e:
            print(f"Error fetching ticket {ticket_key}: {e}")
            return None

    def load_ticket_details(self, refresh_from_api=False, load_comments=False):
        """Load ticket details into panel"""
        print(f"[DEBUG] load_ticket_details called, current_ticket: {self.current_ticket.get('key') if self.current_ticket else 'None'}")

        if not self.current_ticket:
            print("[DEBUG] No current ticket, returning")
            return

        ticket_key = self.current_ticket.get('key')
        print(f"[DEBUG] Loading details for: {ticket_key}")

        # Optionally refresh from API to get latest comments
        if refresh_from_api:
            self.current_ticket = self.fetch_ticket_details(ticket_key)
            if not self.current_ticket:
                return

        fields = self.current_ticket.get('fields', {})
        print(f"[DEBUG] Got fields, building details text...")

        details = f"**{ticket_key}**: {fields.get('summary', 'No summary')}\n\n"

        status = fields.get('status', {})
        priority = fields.get('priority', {})
        details += f"Status: {status.get('name', 'Unknown')}\n"
        details += f"Priority: {priority.get('name', 'Unknown')}\n\n"

        reporter = fields.get('reporter', {})
        assignee = fields.get('assignee')
        details += f"Reporter: {reporter.get('displayName', 'Unknown') if reporter else 'Unknown'}\n"
        details += f"Assignee: {assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'}\n\n"

        description = fields.get('description', '')
        if description:
            if isinstance(description, dict):
                details += "Description:\n" + self.extract_text_from_adf(description) + "\n\n"
            else:
                details += f"Description:\n{description}\n\n"

        # Only fetch comments if explicitly requested or when refreshing
        if load_comments or refresh_from_api:
            details += "=" * 50 + "\n"
            details += "Loading comments...\n"
            details += "=" * 50 + "\n"

            self.details_text.config(state='normal')
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, details)
            self.details_text.config(state='disabled')

            # Load comments in background thread
            def load_comments_async():
                comments_data = self.make_jira_request(f"issue/{ticket_key}/comment")
                if comments_data and 'comments' in comments_data:
                    comments = comments_data['comments']
                    if comments:
                        comment_text = "\n" + "=" * 50 + "\n"
                        comment_text += f"COMMENTS ({len(comments)}):\n"
                        comment_text += "=" * 50 + "\n\n"

                        for comment in comments:
                            author = comment.get('author', {}).get('displayName', 'Unknown')
                            created = comment.get('created', '')
                            if created:
                                try:
                                    created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
                                    created = created_date.strftime('%Y-%m-%d %H:%M')
                                except:
                                    pass

                            body = comment.get('body', '')
                            if isinstance(body, dict):
                                body = self.extract_text_from_adf(body)

                            comment_text += f"[{created}] {author}:\n"
                            comment_text += f"{body}\n"
                            comment_text += "-" * 50 + "\n\n"

                        # Update UI in main thread
                        def update_ui():
                            current_details = self.details_text.get(1.0, tk.END)
                            # Replace "Loading comments..." with actual comments
                            if "Loading comments..." in current_details:
                                self.details_text.config(state='normal')
                                self.details_text.delete(1.0, tk.END)
                                new_details = details + comment_text
                                self.details_text.insert(1.0, new_details)
                                self.details_text.config(state='disabled')

                        self.root.after(0, update_ui)

            threading.Thread(target=load_comments_async, daemon=True).start()
        else:
            # Show button to load comments on demand
            details += "\n" + "=" * 50 + "\n"
            details += "Click 'View Comments' button to load comments\n"
            details += "=" * 50 + "\n"

            self.details_text.config(state='normal')
            self.details_text.delete(1.0, tk.END)
            self.details_text.insert(1.0, details)
            self.details_text.config(state='disabled')

    def extract_text_from_adf(self, adf_content):
        """Extract text from Atlassian Document Format"""
        if not isinstance(adf_content, dict):
            return str(adf_content)
            
        text_parts = []
        
        def extract_text(node):
            if isinstance(node, dict):
                if 'text' in node:
                    text_parts.append(node['text'])
                elif 'content' in node:
                    for child in node['content']:
                        extract_text(child)
            elif isinstance(node, list):
                for item in node:
                    extract_text(item)
                    
        extract_text(adf_content)
        return '\n'.join(text_parts) if text_parts else 'No description'

    def sort_treeview(self, col):
        """Sort treeview by column"""
        # Get all data from tree
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        
        # Sort data
        try:
            # Try numeric sort for priority and age columns
            if col in ['Priority', 'Age']:
                # For Priority, sort by symbol but maintain original order
                if col == 'Priority':
                    priority_order = {'🔴': 0, '🟠': 1, '🟡': 2, '🔵': 3, '⚪': 4}
                    data.sort(key=lambda x: priority_order.get(x[0], 5))
                elif col == 'Age':
                    # Sort by age - convert to hours for proper numeric sort
                    def age_to_hours(age_str):
                        if age_str == '?':
                            return 999999
                        try:
                            if age_str.endswith('h'):
                                return int(age_str[:-1])
                            elif age_str.endswith('d'):
                                return int(age_str[:-1]) * 24
                            elif age_str.endswith('w'):
                                return int(age_str[:-1]) * 168
                        except:
                            return 999999
                        return 999999
                    data.sort(key=lambda x: age_to_hours(x[0]))
            else:
                # Text sort for other columns
                data.sort(key=lambda x: x[0].lower())
        except:
            # Fallback to text sort
            data.sort(key=lambda x: str(x[0]).lower())
        
        # Check if we need to reverse (toggle sort direction)
        if hasattr(self, '_last_sort_col') and self._last_sort_col == col:
            if hasattr(self, '_sort_reverse'):
                self._sort_reverse = not self._sort_reverse
            else:
                self._sort_reverse = True
        else:
            self._sort_reverse = False
            
        if self._sort_reverse:
            data.reverse()
            
        self._last_sort_col = col
        
        # Rearrange items in sorted order
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

    def on_ticket_double_click(self, event):
        """Handle double-click - open ticket details dialog"""
        self.on_ticket_select(event)
        self.load_ticket_details()

    def on_ticket_right_click(self, event):
        """Handle right-click context menu"""
        item = self.tree.identify_row(event.y)
        if item:
            # Select the ticket first
            self.tree.selection_set(item)
            self.tree.focus(item)
            
            # Trigger selection event to load ticket data
            self.on_ticket_select(event)
            
            # Small delay to ensure ticket is loaded, then show menu
            self.root.after(50, lambda: self.show_context_menu(event.x_root, event.y_root))
    
    def show_context_menu(self, x, y):
        """Show context menu at specified coordinates"""
        if self.current_ticket:
            try:
                self.context_menu.post(x, y)
            finally:
                self.context_menu.grab_release()
        else:
            messagebox.showwarning("Warning", "Please select a ticket first")

    # Knowledge Base Editor
    def open_knowledge_editor(self):
        """Open knowledge base editor"""
        import os
        knowledge_file = os.path.join(os.path.dirname(__file__), 'company_knowledge.txt')

        editor_window = tk.Toplevel(self.root)
        editor_window.title("Company Knowledge Base Editor")
        editor_window.geometry("900x700")
        editor_window.configure(bg='#1a1a1a')

        main_frame = ttk.Frame(editor_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Company Knowledge Base",
                 font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(main_frame, text="Edit subscriptions, org chart, and company information that AI will use for ticket triage:",
                 font=('Segoe UI', 9)).pack(anchor=tk.W, pady=(0, 10))

        # Text editor
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        knowledge_text = scrolledtext.ScrolledText(
            text_frame,
            width=100,
            height=30,
            bg='#ffffff',
            fg='#000000',
            insertbackground='#000000',
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        knowledge_text.pack(fill=tk.BOTH, expand=True)

        # Load existing content
        try:
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    knowledge_text.insert(tk.END, f.read())
        except Exception as e:
            messagebox.showerror("Error", f"Could not load knowledge base: {e}")

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        def save_knowledge():
            try:
                content = knowledge_text.get(1.0, tk.END)
                with open(knowledge_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Saved", "Knowledge base updated successfully!\n\nChanges will be used for new AI analyses.")
                editor_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Could not save knowledge base: {e}")

        ttk.Button(button_frame, text="Save", command=save_knowledge).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=editor_window.destroy).pack(side=tk.LEFT)

    # AI Settings
    def open_ai_settings(self):
        """Open AI Assistant settings dialog"""
        show_ai_settings(self.root)

    # Settings
    def open_settings(self):
        """Open settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Jira Settings")
        settings_window.geometry("500x450")
        settings_window.configure(bg='#1a1a1a')
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        main_frame = ttk.Frame(settings_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Jira Configuration", font=('Segoe UI', 14, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        # Jira URL
        ttk.Label(main_frame, text="Jira URL:").pack(anchor=tk.W, pady=(0, 5))
        jira_url_entry = ttk.Entry(main_frame, width=60, font=('Segoe UI', 10))
        jira_url_entry.pack(fill=tk.X, pady=(0, 5))
        jira_url_entry.insert(0, self.jira_url)
        ttk.Label(main_frame, text="Example: https://yourcompany.atlassian.net", 
                 font=('Segoe UI', 8), foreground='#888888').pack(anchor=tk.W, pady=(0, 15))
        
        # User Email
        ttk.Label(main_frame, text="Your Email Address:").pack(anchor=tk.W, pady=(0, 5))
        email_entry = ttk.Entry(main_frame, width=60, font=('Segoe UI', 10))
        email_entry.pack(fill=tk.X, pady=(0, 5))
        email_entry.insert(0, self.user_email)
        ttk.Label(main_frame, text="Example: john.doe@yourcompany.com", 
                 font=('Segoe UI', 8), foreground='#888888').pack(anchor=tk.W, pady=(0, 15))
        
        # Project Key
        ttk.Label(main_frame, text="Project Key:").pack(anchor=tk.W, pady=(0, 5))
        project_entry = ttk.Entry(main_frame, width=20, font=('Segoe UI', 10))
        project_entry.pack(anchor=tk.W, pady=(0, 5))
        project_entry.insert(0, self.project_key)
        ttk.Label(main_frame, text="Example: ITS, PROJ, DEV (usually 2-4 uppercase letters)", 
                 font=('Segoe UI', 8), foreground='#888888').pack(anchor=tk.W, pady=(0, 15))
        
        # API Token
        ttk.Label(main_frame, text="API Token:").pack(anchor=tk.W, pady=(0, 5))
        token_frame = ttk.Frame(main_frame)
        token_frame.pack(fill=tk.X, pady=(0, 15))
        
        api_token_entry = ttk.Entry(token_frame, width=50, font=('Segoe UI', 10), show="*")
        api_token_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        api_token_entry.insert(0, self.api_token)
        
        ttk.Label(main_frame, text="Example: ATATT3xFfGF0... (long string from Jira Account Settings)", 
                 font=('Segoe UI', 8), foreground='#888888').pack(anchor=tk.W, pady=(0, 10))
        
        # Security Notice
        security_frame = ttk.Frame(main_frame)
        security_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(security_frame, text="🔐", font=('Segoe UI', 12)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(security_frame, text="Your API token is stored securely in Windows Credential Manager", 
                 font=('Segoe UI', 9), foreground='#00ff00').pack(side=tk.LEFT)
        
        # Help
        help_text = ttk.Label(main_frame, text="💡 Generate API token: Jira → Profile → Personal Access Tokens → Create Token", 
                             font=('Segoe UI', 9), foreground='#cccccc')
        help_text.pack(anchor=tk.W, pady=(0, 20))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_settings():
            old_email = self.user_email
            self.jira_url = jira_url_entry.get().strip().rstrip('/')
            self.user_email = email_entry.get().strip()
            self.project_key = project_entry.get().strip()
            self.api_token = api_token_entry.get().strip()
            
            if not all([self.jira_url, self.user_email, self.project_key, self.api_token]):
                messagebox.showerror("Error", "Please fill in all fields")
                return
                
            if self.save_user_settings():
                if old_email != self.user_email:
                    self.user_info_label.config(text=f"User: {self.user_email}")
                
                messagebox.showinfo("Success", "Settings saved successfully!")
                settings_window.destroy()
                
                if messagebox.askyesno("Reload", "Settings updated. Reload tickets?"):
                    self.load_all_tickets_threaded()
        
        def test_connection():
            old_settings = (self.jira_url, self.user_email, self.api_token)
            
            self.jira_url = jira_url_entry.get().strip().rstrip('/')
            self.user_email = email_entry.get().strip()
            self.api_token = api_token_entry.get().strip()
            
            try:
                result = self.make_jira_request("myself")
                if result:
                    messagebox.showinfo("Success", f"Connection successful!\\nConnected as: {result.get('displayName', 'Unknown')}")
                else:
                    messagebox.showerror("Error", "Connection failed. Check your credentials.")
            finally:
                self.jira_url, self.user_email, self.api_token = old_settings
        
        ttk.Button(button_frame, text="Test Connection", command=test_connection).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Save Settings", command=save_settings).pack(side=tk.RIGHT)

    # Ticket Actions (stub function removed - using create_new_ticket instead)
        
    def open_dashboard(self):
        """Open Jira dashboard"""
        dashboard_url = f"{self.jira_url}/jira/servicedesk/projects/{self.project_key}/summary"
        webbrowser.open(dashboard_url)
        
    def resolve_ticket(self):
        """Resolve selected ticket"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data:
            messagebox.showerror("Error", "Could not get transitions")
            return
        
        resolve_transitions = [t for t in transitions_data['transitions'] 
                              if 'resolve' in t['name'].lower() or 'done' in t['name'].lower()]
        
        if not resolve_transitions:
            # If no resolve transition, open the status change dialog
            messagebox.showinfo("No Resolve Transition", "No resolve transition available. Opening status change dialog...")
            self.change_ticket_status()
            return
        
        transition_data = {"transition": {"id": resolve_transitions[0]['id']}}
        result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
        
        if result is not None:
            messagebox.showinfo("Success", f"Ticket {ticket_key} resolved!")
            self.load_all_tickets_threaded()
    
    def change_ticket_status(self):
        """Show dialog to manually change ticket status"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        
        # Get available transitions
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data or 'transitions' not in transitions_data:
            messagebox.showerror("Error", "Could not get available transitions for this ticket")
            return
        
        transitions = transitions_data['transitions']
        
        if not transitions:
            messagebox.showinfo("No Transitions", "No status transitions are available for this ticket.")
            return
        
        # Create status change dialog
        status_window = tk.Toplevel(self.root)
        status_window.title(f"Change Status - {ticket_key}")
        status_window.geometry("500x400")
        status_window.configure(bg='#1a1a1a')
        status_window.transient(self.root)
        status_window.grab_set()
        
        main_frame = ttk.Frame(status_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        current_status = self.current_ticket.get('fields', {}).get('status', {}).get('name', 'Unknown')
        ttk.Label(main_frame, text=f"Current Status: {current_status}", 
                 font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 20))
        
        ttk.Label(main_frame, text="Select New Status:", 
                 font=('Segoe UI', 10)).pack(anchor=tk.W, pady=(0, 10))
        
        # Listbox for transitions
        listbox_frame = ttk.Frame(main_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        listbox = tk.Listbox(listbox_frame, height=10, font=('Segoe UI', 10),
                           bg='#2d2d2d', fg='#ffffff', selectbackground='#0078d4')
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate transitions with descriptions
        transition_map = {}
        for i, transition in enumerate(transitions):
            transition_name = transition['name']
            to_status = transition.get('to', {}).get('name', 'Unknown')
            display_text = f"{transition_name} → {to_status}"
            
            listbox.insert(tk.END, display_text)
            transition_map[i] = transition
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def apply_transition():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a status transition")
                return
            
            selected_transition = transition_map[selection[0]]
            transition_name = selected_transition['name']
            to_status = selected_transition.get('to', {}).get('name', 'new status')
            
            # Confirm the change
            if not messagebox.askyesno("Confirm Status Change", 
                                     f"Change ticket status to '{to_status}' using '{transition_name}'?"):
                return
            
            # Apply the transition
            transition_data = {"transition": {"id": selected_transition['id']}}
            
            result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
            
            if result is not None:
                messagebox.showinfo("Success", f"Ticket {ticket_key} status changed to '{to_status}'!")
                status_window.destroy()
                self.load_all_tickets_threaded()
            else:
                messagebox.showerror("Error", "Failed to change ticket status")
        
        def show_transition_details():
            """Show details about the selected transition"""
            selection = listbox.curselection()
            if not selection:
                return
            
            selected_transition = transition_map[selection[0]]
            
            details = f"""Transition: {selected_transition['name']}

From: {current_status}
To: {selected_transition.get('to', {}).get('name', 'Unknown')}

This will change the ticket status."""
            
            messagebox.showinfo("Transition Details", details)
        
        # Double-click to see details
        listbox.bind('<Double-Button-1>', lambda e: show_transition_details())
        
        ttk.Button(button_frame, text="📋 Details", command=show_transition_details).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=status_window.destroy).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="✅ Apply Change", command=apply_transition).pack(side=tk.RIGHT)
        
        # Select first item by default
        if transitions:
            listbox.selection_set(0)
        
    def assign_to_me(self):
        """Assign ticket to current user"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "No ticket selected")
            return
            
        ticket_key = self.current_ticket.get('key')
        print(f"[DEBUG] Attempting to assign ticket: {ticket_key}")
        try:
            print(f"[DEBUG] Current ticket data keys: {list(self.current_ticket.keys())}")
        except:
            print("[DEBUG] Current ticket data contains non-printable characters")
        
        # Get current user info
        print("[DEBUG] Getting current user info...")
        user_data = self.make_jira_request("myself")
        
        if not user_data:
            messagebox.showerror("Error", "Failed to get user information")
            return
            
        account_id = user_data.get('accountId')
        display_name = user_data.get('displayName', 'You')
        
        print(f"[DEBUG] User account_id: {account_id}, display_name: {display_name}")
        
        if not account_id:
            messagebox.showerror("Error", "Could not get your account ID")
            return
        
        # Show assignment confirmation
        current_assignee = self.current_ticket.get('fields', {}).get('assignee')
        current_name = current_assignee.get('displayName', 'Unassigned') if current_assignee else 'Unassigned'
        
        # Skip confirmation dialog for faster workflow
        
        # Try multiple assignment methods
        print(f"[DEBUG] Trying assignment methods...")
        
        # Method 1: Direct assignee API with just accountId
        assign_data_1 = {"accountId": account_id}
        print(f"[DEBUG] Method 1 - Assignment data: {assign_data_1}")
        result = self.make_jira_request(f"issue/{ticket_key}/assignee", method="PUT", data=assign_data_1)
        
        if result is None:
            print("[DEBUG] Method 1 failed, trying Method 2...")
            
            # Method 2: Issue update API 
            assign_data_2 = {
                "fields": {
                    "assignee": {"accountId": account_id}
                }
            }
            print(f"[DEBUG] Method 2 - Assignment data: {assign_data_2}")
            result = self.make_jira_request(f"issue/{ticket_key}", method="PUT", data=assign_data_2)
            
        if result is None:
            print("[DEBUG] Method 2 failed, trying Method 3...")
            
            # Method 3: Different assignee format
            assign_data_3 = {"name": account_id}
            print(f"[DEBUG] Method 3 - Assignment data: {assign_data_3}")
            result = self.make_jira_request(f"issue/{ticket_key}/assignee", method="PUT", data=assign_data_3)
        
        print(f"[DEBUG] Assignment result: {result}")
        
        if result is not None:
            # Update the current ticket data
            if self.current_ticket:
                self.current_ticket['fields']['assignee'] = {
                    'accountId': account_id,
                    'displayName': display_name
                }
                # Refresh the ticket details display
                self.load_ticket_details()
                
                # Update the tree view item immediately
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    if values and values[0] == ticket_key:
                        new_values = list(values)
                        new_values[4] = display_name  # Assignee is at index 4
                        self.tree.item(item, values=new_values)
                        break
            
            # Automatically refresh all tickets in background for data consistency
            self.load_all_tickets_threaded()
        else:
            messagebox.showerror("Error", "Failed to assign ticket. Check the debug output for details.")

    def assign_to_will(self):
        """Assign ticket to Will Sessions"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "No ticket selected")
            return

        ticket_key = self.current_ticket.get('key')
        print(f"[DEBUG] Attempting to assign ticket {ticket_key} to Will Sessions")

        # Will Sessions account ID - we need to look this up
        # First, try to search for Will Sessions
        will_account_id = "712020:c8e4842e-f5d4-48ae-8f27-d4e84e61b62c"  # This is a placeholder
        will_display_name = "Will Sessions"

        # Try to get Will's actual account ID by searching
        try:
            search_result = self.make_jira_request("user/search?query=Will Sessions")
            if search_result and len(search_result) > 0:
                # Find exact match
                for user in search_result:
                    if user.get('displayName') == 'Will Sessions':
                        will_account_id = user.get('accountId')
                        print(f"[DEBUG] Found Will Sessions with accountId: {will_account_id}")
                        break
        except Exception as e:
            print(f"[DEBUG] Could not search for user: {e}")
            messagebox.showerror("Error", "Could not find Will Sessions in Jira users")
            return

        # Try assignment methods
        print(f"[DEBUG] Trying assignment methods for Will...")

        # Method 1: Direct assignee API with just accountId
        assign_data_1 = {"accountId": will_account_id}
        print(f"[DEBUG] Method 1 - Assignment data: {assign_data_1}")
        result = self.make_jira_request(f"issue/{ticket_key}/assignee", method="PUT", data=assign_data_1)

        if result is None:
            print("[DEBUG] Method 1 failed, trying Method 2...")

            # Method 2: Issue update API
            assign_data_2 = {
                "fields": {
                    "assignee": {"accountId": will_account_id}
                }
            }
            print(f"[DEBUG] Method 2 - Assignment data: {assign_data_2}")
            result = self.make_jira_request(f"issue/{ticket_key}", method="PUT", data=assign_data_2)

        if result is None:
            print("[DEBUG] Method 2 failed, trying Method 3...")

            # Method 3: Different assignee format
            assign_data_3 = {"name": will_account_id}
            print(f"[DEBUG] Method 3 - Assignment data: {assign_data_3}")
            result = self.make_jira_request(f"issue/{ticket_key}/assignee", method="PUT", data=assign_data_3)

        print(f"[DEBUG] Assignment result: {result}")

        if result is not None:
            # Update the current ticket data
            if self.current_ticket:
                self.current_ticket['fields']['assignee'] = {
                    'accountId': will_account_id,
                    'displayName': will_display_name
                }
                # Refresh the ticket details display
                self.load_ticket_details()

                # Update the tree view item immediately
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    if values and values[0] == ticket_key:
                        new_values = list(values)
                        new_values[4] = will_display_name  # Assignee is at index 4
                        self.tree.item(item, values=new_values)
                        break

            # Automatically refresh all tickets in background for data consistency
            self.load_all_tickets_threaded()
        else:
            messagebox.showerror("Error", "Failed to assign ticket to Will. Check the debug output for details.")

    def add_comment_to_ticket(self, ticket_key, comment_text):
        """Add comment to a specific ticket (can be called from other dialogs)"""
        if not comment_text:
            return False
        
        # Try multiple comment formats
        print(f"[DEBUG] Adding comment to ticket: {ticket_key}")
        print(f"[DEBUG] Comment text: {comment_text}")
        
        # Method 1: ADF format (required for API v3)
        comment_data_1 = {
            "body": {
                "content": [
                    {
                        "content": [
                            {
                                "text": comment_text,
                                "type": "text"
                            }
                        ],
                        "type": "paragraph"
                    }
                ],
                "type": "doc",
                "version": 1
            }
        }
        print(f"[DEBUG] Method 1 - ADF Comment data: {comment_data_1}")
        result = self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data_1)
        
        if result is None:
            print("[DEBUG] Method 1 failed, trying Method 2...")
            
            # Method 2: ADF format with simpler structure
            comment_data_2 = {
                "body": {
                    "content": [
                        {
                            "content": [
                                {
                                    "text": comment_text,
                                    "type": "text"
                                }
                            ],
                            "type": "paragraph"
                        }
                    ],
                    "type": "doc",
                    "version": 1
                }
            }
            print(f"[DEBUG] Method 2 - Comment data: {comment_data_2}")
            result = self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data_2)
            
        if result is None:
            print("[DEBUG] Method 2 failed, trying Method 3...")
            
            # Method 3: Legacy text format
            comment_data_3 = {
                "body": {
                    "type": "text",
                    "text": comment_text
                }
            }
            print(f"[DEBUG] Method 3 - Comment data: {comment_data_3}")
            result = self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data_3)
        
        print(f"[DEBUG] Comment result: {result}")

        return result is not None

    def add_comment(self):
        """Add comment to ticket from the comment entry field"""
        if not self.current_ticket:
            return

        comment_text = self.comment_entry.get(1.0, tk.END).strip()
        if not comment_text:
            messagebox.showwarning("Warning", "Please enter a comment")
            return

        ticket_key = self.current_ticket.get('key')

        success = self.add_comment_to_ticket(ticket_key, comment_text)

        if success:
            messagebox.showinfo("Success", "Comment added!")
            self.comment_entry.delete(1.0, tk.END)
        else:
            messagebox.showerror("Error", "Failed to add comment. Check the debug output for details.")
        
    def close_ticket(self):
        """Close selected ticket"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data:
            return
        
        close_transitions = [t for t in transitions_data['transitions'] 
                            if any(k in t['name'].lower() for k in ['close', 'done', 'complete'])]
        
        if close_transitions:
            transition_data = {"transition": {"id": close_transitions[0]['id']}}
            result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
            
            if result is not None:
                messagebox.showinfo("Success", f"Ticket {ticket_key} closed!")
                self.load_all_tickets_threaded()
        
    def open_ticket(self):
        """Reopen selected ticket"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        transitions_data = self.make_jira_request(f"issue/{ticket_key}/transitions")
        
        if not transitions_data:
            return
        
        open_transitions = [t for t in transitions_data['transitions'] 
                           if any(k in t['name'].lower() for k in ['open', 'reopen', 'start'])]
        
        if open_transitions:
            transition_data = {"transition": {"id": open_transitions[0]['id']}}
            result = self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
            
            if result is not None:
                messagebox.showinfo("Success", f"Ticket {ticket_key} reopened!")
                self.load_all_tickets_threaded()
    
    def create_new_ticket(self):
        """Create a new Jira ticket with screenshot support"""
        print("[DEBUG] Opening New Ticket dialog")
        # Create new ticket dialog
        ticket_window = tk.Toplevel(self.root)
        ticket_window.title("Create New Ticket")
        ticket_window.geometry("800x700")
        ticket_window.resizable(True, True)
        ticket_window.transient(self.root)
        ticket_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(ticket_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Summary
        ttk.Label(main_frame, text="Summary:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        summary_entry = ttk.Entry(main_frame, width=80, font=('Segoe UI', 10))
        summary_entry.pack(fill=tk.X, pady=(0, 10))
        summary_entry.focus()
        
        # Description
        ttk.Label(main_frame, text="Description:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        description_text = scrolledtext.ScrolledText(desc_frame, height=12, wrap=tk.WORD, font=('Segoe UI', 10))
        description_text.pack(fill=tk.BOTH, expand=True)
        
        # Reporter section
        reporter_frame = ttk.LabelFrame(main_frame, text="👤 Reporter", padding="10")
        reporter_frame.pack(fill=tk.X, pady=(0, 10))
        
        reporter_var = tk.StringVar()
        
        # Reporter entry with auto-complete
        reporter_entry_frame = ttk.Frame(reporter_frame)
        reporter_entry_frame.pack(fill=tk.X)
        
        ttk.Label(reporter_entry_frame, text="Reporter Email:").pack(side=tk.LEFT)
        reporter_entry = ttk.Entry(reporter_entry_frame, textvariable=reporter_var, width=40)
        reporter_entry.pack(side=tk.LEFT, padx=(10, 5), fill=tk.X, expand=True)
        
        # Auto-complete dropdown (initially hidden)
        autocomplete_frame = ttk.Frame(reporter_frame)
        autocomplete_listbox = tk.Listbox(autocomplete_frame, height=6, font=('Segoe UI', 9))
        autocomplete_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Store user data for selected items
        user_data_cache = {}
        last_search_query = ""
        search_pending = False
        
        def on_reporter_type(event=None):
            """Handle typing in reporter field - auto-complete search"""
            nonlocal last_search_query, search_pending
            
            query = reporter_var.get().strip()
            
            # Debounce - don't search if query hasn't changed or search is already pending
            if query == last_search_query or search_pending:
                print(f"[DEBUG] Skipping duplicate search for: '{query}'")
                return
                
            last_search_query = query
            print(f"[DEBUG] Reporter autocomplete triggered: '{query}'")
            
            # Hide dropdown if query is too short
            if len(query) < 2:
                print(f"[DEBUG] Query too short ({len(query)} chars), hiding dropdown")
                autocomplete_frame.pack_forget()
                return
            
            # Search for licensed/assignable users only
            try:
                search_pending = True
                print(f"[DEBUG] Searching for users with query: '{query}'")
                logger.info(f"Starting user search for query: '{query}'")

                # Use assignable users endpoint to get only licensed users
                search_result = self.make_jira_request(f"user/assignable/search?query={query}&project={self.project_key}&maxResults=10")
                print(f"[DEBUG] Search result: {search_result}")
                logger.info(f"Assignable user search returned {len(search_result) if search_result else 0} results")

                # If no assignable users found, try broader user search
                if not search_result or len(search_result) == 0:
                    print(f"[DEBUG] No assignable users found, trying broader user search")
                    logger.info("No assignable users found, trying broader user search")
                    search_result = self.make_jira_request(f"user/search?query={query}&maxResults=10")
                    print(f"[DEBUG] Broader search result: {search_result}")
                    logger.info(f"Broader user search returned {len(search_result) if search_result else 0} results")

                search_pending = False

                if search_result and len(search_result) > 0:
                    print(f"[DEBUG] Found {len(search_result)} users")
                    # Clear previous results
                    autocomplete_listbox.delete(0, tk.END)
                    user_data_cache.clear()
                    
                    # Add users to dropdown
                    for i, user in enumerate(search_result):
                        display_name = user.get('displayName', 'Unknown')
                        email = user.get('emailAddress', 'No email')
                        account_id = user.get('accountId', '')
                        
                        # Create display text
                        display_text = f"{display_name} ({email})"
                        autocomplete_listbox.insert(tk.END, display_text)
                        print(f"[DEBUG] Added user {i+1}: {display_text}")
                        
                        # Cache user data
                        user_data_cache[display_text] = {
                            'accountId': account_id,
                            'displayName': display_name,
                            'email': email
                        }
                    
                    # Show dropdown
                    autocomplete_frame.pack(fill=tk.X, pady=(5, 0))
                    print(f"[DEBUG] Showing dropdown with {len(search_result)} users")
                else:
                    print(f"[DEBUG] No users found for query '{query}', showing manual entry option")
                    logger.warning(f"No users found for query '{query}' in either assignable or all user search")

                    # Show option to manually enter the user
                    autocomplete_listbox.delete(0, tk.END)
                    user_data_cache.clear()

                    # Add manual entry option
                    manual_entry = f"📝 Use '{query}' manually (user may not have project access)"
                    autocomplete_listbox.insert(tk.END, manual_entry)
                    user_data_cache[manual_entry] = {
                        'accountId': '',  # Empty account ID for manual entry
                        'displayName': query,
                        'email': query if '@' in query else ''
                    }

                    # Show dropdown with manual option
                    autocomplete_frame.pack(fill=tk.X, pady=(5, 0))
                    print(f"[DEBUG] Showing manual entry option for '{query}'")
            except Exception as e:
                search_pending = False
                print(f"[DEBUG] Auto-complete search error: {str(e)}")
                import traceback
                traceback.print_exc()
                autocomplete_frame.pack_forget()
        
        def on_autocomplete_select(event=None):
            """Handle selection from auto-complete dropdown"""
            try:
                selection = autocomplete_listbox.curselection()
                if selection:
                    selected_text = autocomplete_listbox.get(selection[0])
                    user_data = user_data_cache.get(selected_text, {})
                    
                    # Set the reporter
                    reporter_var.set(selected_text)
                    reporter_entry.account_id = user_data.get('accountId', '')
                    
                    # Hide dropdown
                    autocomplete_frame.pack_forget()
                    
                    print(f"[DEBUG] Selected reporter: {user_data.get('displayName')} - {user_data.get('accountId')}")
            except Exception as e:
                print(f"[DEBUG] Selection error: {str(e)}")
        
        def clear_reporter():
            """Clear reporter selection"""
            reporter_var.set("")
            if hasattr(reporter_entry, 'account_id'):
                delattr(reporter_entry, 'account_id')
            autocomplete_frame.pack_forget()
        
        # Bind events - use KeyRelease for better control
        print("[DEBUG] Setting up event bindings for reporter autocomplete")
        reporter_entry.bind('<KeyRelease>', lambda event: on_reporter_type())
        autocomplete_listbox.bind('<Double-Button-1>', on_autocomplete_select)
        autocomplete_listbox.bind('<Return>', on_autocomplete_select)
        
        # Clear button
        ttk.Button(reporter_entry_frame, text="Clear", command=clear_reporter).pack(side=tk.LEFT, padx=(5, 0))
        
        # Note about reporter
        ttk.Label(reporter_frame, text="💡 Leave empty to set yourself as reporter", 
                 font=('Segoe UI', 9), foreground='gray').pack(anchor=tk.W, pady=(5, 0))
        
        # Screenshot section
        screenshot_frame = ttk.LabelFrame(main_frame, text="📷 Screenshots", padding="10")
        screenshot_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.attachments = []  # Store attachments for this ticket
        
        def paste_screenshot():
            """Paste screenshot from clipboard"""
            try:
                # Try to get image from clipboard
                import tkinter as tk
                from PIL import ImageGrab, Image
                import io
                import tempfile
                
                # Get image from clipboard
                img = ImageGrab.grabclipboard()
                if img is None:
                    messagebox.showwarning("No Image", "No image found in clipboard. Copy an image first.")
                    return
                
                # Save to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
                img.save(temp_file.name, 'PNG')
                temp_file.close()
                
                # Add to attachments list
                self.attachments.append(temp_file.name)
                
                # Update UI
                update_attachment_list()
                
                # Automatically show preview of the pasted screenshot
                show_image_preview(temp_file.name)
                
                messagebox.showinfo("Success", f"Screenshot added! ({len(self.attachments)} file(s) attached)")
                
            except ImportError:
                messagebox.showerror("Error", "PIL (Pillow) library required for screenshot support.\nInstall with: pip install Pillow")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to paste screenshot: {str(e)}")
        
        def browse_file():
            """Browse for file to attach"""
            from tkinter import filedialog
            filename = filedialog.askopenfilename(
                title="Select file to attach",
                filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
            )
            if filename:
                self.attachments.append(filename)
                update_attachment_list()
        
        def update_attachment_list():
            """Update the attachment list display"""
            for widget in attachment_list_frame.winfo_children():
                widget.destroy()
            
            for i, filepath in enumerate(self.attachments):
                import os
                filename = os.path.basename(filepath)
                file_frame = ttk.Frame(attachment_list_frame)
                file_frame.pack(fill=tk.X, pady=2)
                
                # Create a frame for the file info
                info_frame = ttk.Frame(file_frame)
                info_frame.pack(fill=tk.X)
                
                # File name and preview button
                file_info_frame = ttk.Frame(info_frame)
                file_info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                ttk.Label(file_info_frame, text=f"📎 {filename}").pack(side=tk.LEFT)
                
                # Preview button for images
                if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    ttk.Button(file_info_frame, text="👁️ Preview", 
                              command=lambda fp=filepath: show_image_preview(fp)).pack(side=tk.LEFT, padx=(10, 0))
                
                ttk.Button(info_frame, text="❌", width=3, 
                          command=lambda idx=i: remove_attachment(idx)).pack(side=tk.RIGHT)
        
        def show_image_preview(filepath):
            """Show image preview in a popup window"""
            try:
                from PIL import Image, ImageTk
                import tkinter as tk
                
                # Create preview window
                preview_window = tk.Toplevel(ticket_window)
                preview_window.title(f"Preview - {os.path.basename(filepath)}")
                preview_window.geometry("600x500")
                
                # Load and resize image
                img = Image.open(filepath)
                
                # Calculate size to fit in window while maintaining aspect ratio
                max_width, max_height = 550, 400
                img_width, img_height = img.size
                
                if img_width > max_width or img_height > max_height:
                    ratio = min(max_width/img_width, max_height/img_height)
                    new_width = int(img_width * ratio)
                    new_height = int(img_height * ratio)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                # Create label to display image
                image_label = ttk.Label(preview_window, image=photo)
                image_label.image = photo  # Keep a reference
                image_label.pack(expand=True, pady=10)
                
                # Add info label
                info_text = f"File: {os.path.basename(filepath)}\nSize: {img_width}x{img_height}"
                ttk.Label(preview_window, text=info_text, font=('Segoe UI', 9)).pack(pady=5)
                
                # Close button
                ttk.Button(preview_window, text="Close", command=preview_window.destroy).pack(pady=10)
                
            except Exception as e:
                messagebox.showerror("Preview Error", f"Cannot preview image: {str(e)}")
        
        def remove_attachment(index):
            """Remove attachment from list"""
            if 0 <= index < len(self.attachments):
                self.attachments.pop(index)
                update_attachment_list()
        
        # Screenshot buttons
        button_frame = ttk.Frame(screenshot_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="📋 Paste Screenshot", command=paste_screenshot).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="📁 Browse File", command=browse_file).pack(side=tk.LEFT)
        
        # Attachment list
        attachment_list_frame = ttk.Frame(screenshot_frame)
        attachment_list_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Buttons
        button_bottom_frame = ttk.Frame(main_frame)
        button_bottom_frame.pack(fill=tk.X, pady=(10, 0))
        
        def create_ticket():
            """Create the ticket via API"""
            summary = summary_entry.get().strip()
            description = description_text.get(1.0, tk.END).strip()
            
            if not summary:
                messagebox.showwarning("Missing Summary", "Please enter a ticket summary")
                return
            
            # Get current user for assignment and default reporter
            user_data = self.make_jira_request("myself")
            if not user_data:
                messagebox.showerror("Error", "Failed to get user information")
                return
            
            account_id = user_data.get('accountId')
            
            # Determine reporter
            reporter_account_id = account_id  # Default to current user
            if hasattr(reporter_entry, 'account_id') and reporter_entry.account_id:
                reporter_account_id = reporter_entry.account_id
                print(f"[DEBUG] Using custom reporter: {reporter_account_id}")
            else:
                print(f"[DEBUG] Using current user as reporter: {account_id}")
            
            # Try multiple ticket creation formats
            print(f"[DEBUG] Creating ticket with summary: {summary}")
            print(f"[DEBUG] Description: {description}")
            print(f"[DEBUG] Reporter: {reporter_account_id}")
            print(f"[DEBUG] Assignee: {account_id}")
            
            # Method 1: ADF format (newer Jira instances) - Try this first since your instance requires it
            ticket_data_1 = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": summary,
                    "description": {
                        "content": [
                            {
                                "content": [
                                    {
                                        "text": description,
                                        "type": "text"
                                    }
                                ],
                                "type": "paragraph"
                            }
                        ],
                        "type": "doc",
                        "version": 1
                    },
                    "issuetype": {"id": list(self.issue_types.values())[0]},
                    "assignee": {"accountId": account_id},
                    "reporter": {"accountId": reporter_account_id}
                }
            }
            
            print(f"[DEBUG] Method 1 - ADF Ticket data: {ticket_data_1}")
            result = self.make_jira_request("issue", method="POST", data=ticket_data_1)
            
            if result is None:
                print("[DEBUG] Method 1 (ADF) failed, trying Method 2 (plain text)...")
                
                # Method 2: Simple string description (fallback)
                ticket_data_2 = {
                    "fields": {
                        "project": {"key": self.project_key},
                        "summary": summary,
                        "description": description,
                        "issuetype": {"id": list(self.issue_types.values())[0]},
                        "assignee": {"accountId": account_id},
                        "reporter": {"accountId": reporter_account_id}
                    }
                }
                
                print(f"[DEBUG] Method 2 - Plain text Ticket data: {ticket_data_2}")
                result = self.make_jira_request("issue", method="POST", data=ticket_data_2)
            
            if result is None:
                print("[DEBUG] Method 2 failed, trying Method 3...")
                
                # Method 3: No description (minimal ticket)
                ticket_data_3 = {
                    "fields": {
                        "project": {"key": self.project_key},
                        "summary": summary,
                        "issuetype": {"id": list(self.issue_types.values())[0]},
                        "assignee": {"accountId": account_id},
                        "reporter": {"accountId": reporter_account_id}
                    }
                }
                
                print(f"[DEBUG] Method 3 - Ticket data: {ticket_data_3}")
                result = self.make_jira_request("issue", method="POST", data=ticket_data_3)
                
                # If successful, add description as a comment
                if result and description.strip():
                    ticket_key = result.get('key')
                    print(f"[DEBUG] Adding description as comment to {ticket_key}")
                    comment_data = {
                        "body": {
                            "content": [
                                {
                                    "content": [
                                        {
                                            "text": description,
                                            "type": "text"
                                        }
                                    ],
                                    "type": "paragraph"
                                }
                            ],
                            "type": "doc",
                            "version": 1
                        }
                    }
                    self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data)
            
            if result:
                ticket_key = result.get('key')
                messagebox.showinfo("Success", f"Ticket {ticket_key} created successfully!")
                
                # Upload attachments if any
                if self.attachments:
                    self.upload_attachments(ticket_key)
                
                # Close dialog and refresh tickets
                ticket_window.destroy()
                self.load_all_tickets_threaded()
            else:
                messagebox.showerror("Error", "Failed to create ticket")
        
        ttk.Button(button_bottom_frame, text="✅ Create Ticket", command=create_ticket).pack(side=tk.RIGHT)
        ttk.Button(button_bottom_frame, text="❌ Cancel", command=ticket_window.destroy).pack(side=tk.RIGHT, padx=(0, 5))
    
    def upload_attachments(self, ticket_key):
        """Upload attachments to a ticket"""
        for filepath in self.attachments:
            try:
                import os
                if not os.path.exists(filepath):
                    continue
                    
                with open(filepath, 'rb') as f:
                    files = {'file': f}
                    result = self.make_jira_request(f"issue/{ticket_key}/attachments", method="POST", files=files)
                    
                if result:
                    print(f"[DEBUG] Uploaded attachment: {os.path.basename(filepath)}")
                else:
                    print(f"[DEBUG] Failed to upload: {os.path.basename(filepath)}")
                    
            except Exception as e:
                print(f"[DEBUG] Error uploading {filepath}: {str(e)}")
        
        # Clear attachments list
        self.attachments = []

    def open_ticket_in_browser(self):
        """Open ticket in web browser"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        url = f"{self.jira_url}/browse/{ticket_key}"
        webbrowser.open(url)
        
    def duplicate_ticket(self):
        """Duplicate selected ticket"""
        messagebox.showinfo("Feature", "Duplicate ticket functionality coming soon!")
        
    def ai_summarize_ticket(self):
        """AI ticket summarization"""
        if not self.current_ticket:
            messagebox.showwarning("No Selection", "Please select a ticket to analyze")
            return
        
        try:
            # Show AI summary dialog
            show_ai_summary(self.root, self.current_ticket, self)
        except Exception as e:
            # Handle encoding errors in the error message itself
            try:
                error_msg = str(e)
                # Test if we can display this
                error_msg.encode('cp1252')
            except (UnicodeEncodeError, UnicodeDecodeError):
                error_msg = "Encoding error - unable to display error details"

            messagebox.showerror("AI Analysis Error", f"Failed to analyze ticket: {error_msg}")
        
    def copy_ticket_url(self):
        """Copy ticket URL to clipboard"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        url = f"{self.jira_url}/browse/{ticket_key}"
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("Copied", f"URL copied: {url}")
        
    def copy_ticket_key(self):
        """Copy ticket key to clipboard"""
        if not self.current_ticket:
            return
            
        ticket_key = self.current_ticket.get('key')
        self.root.clipboard_clear()
        self.root.clipboard_append(ticket_key)
        messagebox.showinfo("Copied", f"Key copied: {ticket_key}")

    # License Management Methods
    def check_license_on_startup(self):
        """Check license status when app starts"""
        license_status = self.license_manager.check_license_status()
        
        if license_status["status"] == "no_license":
            self.show_license_dialog()
        elif license_status["status"] == "trial_expired":
            self.show_license_expired_dialog()
        elif license_status["status"] == "invalid":
            messagebox.showerror("License Error", license_status["message"])
            self.show_license_dialog()
        elif license_status["status"] in ["trial_active", "licensed"]:
            # Update title with license info
            days_remaining = license_status.get("days_remaining", 0)
            license_type = license_status["data"]["type"].title()
            self.root.title(f"Jira Ticket Viewer - {license_type} ({days_remaining} days)")
    
    def show_license_dialog(self):
        """Show license activation dialog"""
        license_window = tk.Toplevel(self.root)
        license_window.title("License Activation")
        license_window.geometry("500x400")
        license_window.configure(bg='#1e1e1e')
        license_window.transient(self.root)
        license_window.grab_set()
        
        # Center the window
        license_window.update_idletasks()
        x = (license_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (license_window.winfo_screenheight() // 2) - (400 // 2)
        license_window.geometry(f"500x400+{x}+{y}")
        
        main_frame = ttk.Frame(license_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔑 Jira Ticket Viewer Licensing", 
                               font=('Segoe UI', 14, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # License key entry
        ttk.Label(main_frame, text="Enter License Key:").pack(anchor=tk.W, pady=(0, 5))
        license_entry = scrolledtext.ScrolledText(main_frame, height=4, width=60)
        license_entry.pack(fill=tk.X, pady=(0, 15))
        
        # Machine ID display
        machine_id = self.license_manager.get_machine_id()
        ttk.Label(main_frame, text=f"Machine ID: {machine_id}", 
                 font=('Courier', 9), foreground='#cccccc').pack(anchor=tk.W, pady=(0, 15))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        def activate_license():
            license_key = license_entry.get(1.0, tk.END).strip()
            if not license_key:
                messagebox.showerror("Error", "Please enter a license key")
                return
            
            # Validate and save license
            validation = self.license_manager.validate_license_key(license_key)
            if validation["valid"]:
                self.license_manager.save_license(license_key)
                messagebox.showinfo("Success", "License activated successfully!")
                license_window.destroy()
                # Update title
                license_type = validation["data"]["type"].title()
                days = validation["days_remaining"]
                self.root.title(f"Jira Ticket Viewer - {license_type} ({days} days)")
            else:
                messagebox.showerror("Invalid License", validation["error"])
        
        def start_trial():
            if self.license_manager.get_trial_status():
                messagebox.showwarning("Trial", "Trial period has already been used")
                return
            
            if not self.user_email:
                email = tk.simpledialog.askstring("Email Required", "Enter your email to start trial:")
                if not email:
                    return
                self.user_email = email
            
            if self.license_manager.start_trial(self.user_email):
                self.license_manager.set_trial_started()
                messagebox.showinfo("Trial Started", f"14-day trial activated for {self.user_email}")
                license_window.destroy()
                self.root.title("Jira Ticket Viewer - Trial (14 days)")
            else:
                messagebox.showerror("Error", "Could not start trial")
        
        ttk.Button(button_frame, text="Activate License", command=activate_license).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Start Free Trial", command=start_trial).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT)
        
        # License info
        info_frame = ttk.LabelFrame(main_frame, text="License Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(20, 0))
        
        info_text = """Trial: 14 days, basic features
Standard: Full features for up to 5 users
Premium: All features, unlimited users, priority support

Contact: sales@example.com for license keys"""
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, foreground='#cccccc').pack(anchor=tk.W)
    
    def show_license_expired_dialog(self):
        """Show license expired dialog"""
        result = messagebox.askyesno("License Expired", 
                                   "Your license has expired. Would you like to enter a new license key?")
        if result:
            self.show_license_dialog()
        else:
            self.root.quit()
    
    def show_reminders(self):
        """Show the reminder manager"""
        if self.reminder_manager:
            self.reminder_manager.show_reminder_manager()
        else:
            messagebox.showinfo("Reminders Disabled", "Reminder system is temporarily disabled")
    
    def add_onboarding_reminder(self, user_email, start_date=None):
        """Add advance onboarding reminders for a new user (triggers BEFORE start date)"""
        if not self.reminder_manager:
            return  # Reminder system disabled
            
        from datetime import datetime, timedelta
        
        if start_date is None:
            start_date = datetime.now() + timedelta(days=3)  # Default: starting in 3 days
        
        # 2 days BEFORE start date - Setup preparation
        self.reminder_manager.add_reminder(
            f"🚨 PREP: {user_email} starts in 2 days",
            f"URGENT: Setup accounts, email, system access for {user_email} who starts on {start_date.strftime('%Y-%m-%d')}",
            start_date - timedelta(days=2),
            "onboarding",
            "critical"
        )
        
        # 1 day BEFORE start date - Final prep
        self.reminder_manager.add_reminder(
            f"🔥 TOMORROW: {user_email} starts",
            f"CRITICAL: Send welcome email, login credentials, first-day info to {user_email}. They start TOMORROW ({start_date.strftime('%Y-%m-%d')})",
            start_date - timedelta(days=1),
            "onboarding",
            "critical"
        )
        
        # ON start date - Morning check
        self.reminder_manager.add_reminder(
            f"📅 TODAY: {user_email}'s first day",
            f"First day for {user_email}! Ensure everything is ready and check in during the day",
            start_date.replace(hour=8, minute=0),  # 8 AM on start date
            "onboarding",
            "high"
        )
        
        # 1 week after start - Follow up
        self.reminder_manager.add_reminder(
            f"📋 Week 1 check: {user_email}",
            f"Follow up with {user_email} - how is their first week going? Any issues?",
            start_date + timedelta(days=7),
            "onboarding",
            "medium"
        )
    
    def add_offboarding_reminder(self, user_email, last_day=None):
        """Add advance offboarding reminders for departing user (triggers BEFORE last day)"""
        if not self.reminder_manager:
            return  # Reminder system disabled
            
        from datetime import datetime, timedelta
        
        if last_day is None:
            last_day = datetime.now() + timedelta(days=3)  # Default: leaving in 3 days
        
        # 2 days BEFORE last day - Preparation
        self.reminder_manager.add_reminder(
            f"🚨 PREP: {user_email} leaves in 2 days",
            f"URGENT: Start offboarding process for {user_email} who leaves on {last_day.strftime('%Y-%m-%d')}. Prepare equipment collection, access review.",
            last_day - timedelta(days=2),
            "offboarding",
            "critical"
        )
        
        # 1 day BEFORE last day - Final preparations
        self.reminder_manager.add_reminder(
            f"🔥 TOMORROW: {user_email}'s last day",
            f"CRITICAL: {user_email} leaves TOMORROW ({last_day.strftime('%Y-%m-%d')})! Ensure handover complete, equipment ready for collection.",
            last_day - timedelta(days=1),
            "offboarding",
            "critical"
        )
        
        # ON last day - Execute offboarding
        self.reminder_manager.add_reminder(
            f"📅 TODAY: {user_email}'s last day",
            f"Last day for {user_email}! Collect equipment, disable accounts, revoke access by end of day.",
            last_day.replace(hour=9, minute=0),  # 9 AM on last day
            "offboarding",
            "critical"
        )
        
        # ON last day - End of day tasks
        self.reminder_manager.add_reminder(
            f"🔒 EOD: Disable {user_email}",
            f"END OF DAY: Disable all accounts and access for {user_email}. Ensure all equipment collected.",
            last_day.replace(hour=17, minute=0),  # 5 PM on last day
            "offboarding",
            "critical"
        )
        
        # Day AFTER - Cleanup
        self.reminder_manager.add_reminder(
            f"🧹 Cleanup: {user_email}",
            f"Post-departure cleanup: Archive emails, transfer files, complete final documentation for {user_email}",
            last_day + timedelta(days=1).replace(hour=9, minute=0),
            "offboarding",
            "high"
        )
    
    def extract_dates_from_ticket(self, ticket_data):
        """Extract start/leave dates from ticket summary or description"""
        import re
        from datetime import datetime
        
        # Get ticket text to search
        summary = ticket_data.get('fields', {}).get('summary', '').lower()
        description_content = ticket_data.get('fields', {}).get('description', {})
        
        # Extract description text from ADF format
        description = ""
        if isinstance(description_content, dict) and 'content' in description_content:
            for content_item in description_content.get('content', []):
                if content_item.get('type') == 'paragraph':
                    for text_item in content_item.get('content', []):
                        if text_item.get('type') == 'text':
                            description += text_item.get('text', '') + " "
        
        ticket_text = f"{summary} {description}".lower()
        print(f"[DEBUG] Searching for dates in: {ticket_text[:100]}...")
        
        # Common date patterns
        date_patterns = [
            r'starts?\s+(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',  # "starts on 15/09/2024"
            r'start\s+date:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',      # "start date: 15/09/2024"
            r'begin[s]?\s+(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', # "begins on 15/09/2024"
            r'leaves?\s+(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',   # "leaves on 20/09/2024"
            r'last\s+day:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',        # "last day: 20/09/2024"
            r'finish[es]?\s+(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', # "finishes on 20/09/2024"
            r'end[s]?\s+(?:on\s+)?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',   # "ends on 20/09/2024"
        ]
        
        found_dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, ticket_text)
            for match in matches:
                try:
                    # Try different date formats
                    for date_format in ['%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y', '%m-%d-%Y', '%d/%m/%y', '%d-%m-%y']:
                        try:
                            parsed_date = datetime.strptime(match, date_format)
                            found_dates.append({
                                'date': parsed_date,
                                'original_text': match,
                                'pattern': pattern
                            })
                            print(f"[DEBUG] Found date: {parsed_date.strftime('%Y-%m-%d')} from '{match}'")
                            break
                        except ValueError:
                            continue
                except Exception as e:
                    print(f"[DEBUG] Error parsing date '{match}': {e}")
        
        return found_dates
    
    def create_reminders_from_ticket(self, ticket_data):
        """Analyze ticket and create appropriate reminders based on content"""
        summary = ticket_data.get('fields', {}).get('summary', '').lower()
        ticket_key = ticket_data.get('key', 'Unknown')
        
        # Extract any email addresses from the ticket
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, str(ticket_data))
        user_email = emails[0] if emails else "user@company.com"
        
        # Extract dates from ticket
        found_dates = self.extract_dates_from_ticket(ticket_data)
        
        if not found_dates:
            messagebox.showwarning("No Dates Found", 
                                 f"Could not find any dates in ticket {ticket_key}.\n"
                                 "Please add dates manually in the reminder manager.")
            return
        
        # Determine if this is onboarding or offboarding based on keywords
        onboarding_keywords = ['onboard', 'new user', 'new hire', 'start', 'join', 'begin']
        offboarding_keywords = ['offboard', 'leave', 'depart', 'resign', 'quit', 'last day', 'finish', 'end']
        
        is_onboarding = any(keyword in summary for keyword in onboarding_keywords)
        is_offboarding = any(keyword in summary for keyword in offboarding_keywords)
        
        # Create reminders based on ticket type
        for date_info in found_dates:
            target_date = date_info['date']
            
            if is_onboarding:
                print(f"[DEBUG] Creating onboarding reminders for {user_email} starting {target_date.strftime('%Y-%m-%d')}")
                self.add_onboarding_reminder(user_email, target_date)
                messagebox.showinfo("Onboarding Reminders Created", 
                                   f"Created onboarding reminders for {user_email}\n"
                                   f"Start date: {target_date.strftime('%Y-%m-%d')}\n"
                                   f"From ticket: {ticket_key}")
            
            elif is_offboarding:
                print(f"[DEBUG] Creating offboarding reminders for {user_email} leaving {target_date.strftime('%Y-%m-%d')}")
                self.add_offboarding_reminder(user_email, target_date)
                messagebox.showinfo("Offboarding Reminders Created", 
                                   f"Created offboarding reminders for {user_email}\n"
                                   f"Last day: {target_date.strftime('%Y-%m-%d')}\n"
                                   f"From ticket: {ticket_key}")
            
            else:
                # Generic reminder
                self.reminder_manager.add_reminder(
                    f"Follow up on {ticket_key}",
                    f"Follow up on ticket {ticket_key}: {summary[:100]}...",
                    target_date,
                    "general",
                    "medium"
                )
                messagebox.showinfo("Generic Reminder Created", 
                                   f"Created reminder for {target_date.strftime('%Y-%m-%d')}\n"
                                   f"From ticket: {ticket_key}")
        
        # Refresh the reminder list if open
        self.show_reminders()
    
    def create_reminders_from_current_ticket(self):
        """Create reminders from the currently selected ticket"""
        if not self.current_ticket:
            messagebox.showwarning("No Ticket Selected", "Please select a ticket first")
            return
        
        self.create_reminders_from_ticket(self.current_ticket)
    
    def check_feature_access(self, feature_name):
        """Check if user has access to specific feature"""
        if not self.license_manager.has_feature(feature_name):
            license_status = self.license_manager.check_license_status()
            license_type = license_status.get("data", {}).get("type", "trial")
            messagebox.showwarning("Feature Restricted", 
                                 f"This feature requires a higher license tier.\nCurrent: {license_type.title()}")
            return False
        return True
    def show_debug_log(self):
        """Show a debug log window with real-time verbose logging"""
        debug_window = tk.Toplevel(self.root)
        debug_window.title("Debug Log Viewer")
        debug_window.geometry("1000x700")
        debug_window.configure(bg='#1e1e1e')

        # Make resizable
        debug_window.resizable(True, True)

        # Main frame
        main_frame = ttk.Frame(debug_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(header_frame, text="Debug Log - Real-time Verbose Output",
                 font=('Segoe UI', 14, 'bold')).pack(side=tk.LEFT)

        # Buttons frame
        buttons_frame = ttk.Frame(header_frame)
        buttons_frame.pack(side=tk.RIGHT)

        # Log text area with monospace font
        log_frame = ttk.LabelFrame(main_frame, text="Live Debug Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.debug_text = scrolledtext.ScrolledText(
            log_frame,
            bg='#1a1a1a',
            fg='#00ff00',
            insertbackground='#00ff00',
            font=('Consolas', 9),
            wrap=tk.WORD,
            state=tk.DISABLED
        )
        self.debug_text.pack(fill=tk.BOTH, expand=True)

        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)

        def clear_log():
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.delete(1.0, tk.END)
            self.debug_text.config(state=tk.DISABLED)
            self.log_to_debug("=== DEBUG LOG CLEARED ===")

        def copy_all():
            content = self.debug_text.get(1.0, tk.END)
            debug_window.clipboard_clear()
            debug_window.clipboard_append(content)
            messagebox.showinfo("Copied", "All debug logs copied to clipboard!")

        def refresh_log():
            self.load_log_file()

        ttk.Button(control_frame, text="Clear Log", command=clear_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Copy All", command=copy_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Refresh from File", command=refresh_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Close", command=debug_window.destroy).pack(side=tk.RIGHT)

        # Load existing log content
        self.load_log_file()

        # Store reference for live updates
        self.debug_window = debug_window
        self.debug_text_widget = self.debug_text

        # Log that debug window opened
        self.log_to_debug("=== DEBUG LOG WINDOW OPENED ===")
        self.log_to_debug("AI Summary errors will appear here in real-time")
        self.log_to_debug("Ready to monitor AI operations...")

    def load_log_file(self):
        """Load existing log file content"""
        try:
            log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'jira_debug.log')
            if os.path.exists(log_file):
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Show last 5000 characters to avoid overwhelming
                    if len(content) > 5000:
                        content = "...[LOG TRUNCATED]...\n" + content[-5000:]

                    if hasattr(self, 'debug_text'):
                        self.debug_text.config(state=tk.NORMAL)
                        self.debug_text.delete(1.0, tk.END)
                        self.debug_text.insert(tk.END, content)
                        self.debug_text.see(tk.END)
                        self.debug_text.config(state=tk.DISABLED)
        except Exception as e:
            self.log_to_debug(f"Error loading log file: {str(e)}")

    def log_to_debug(self, message):
        """Add message to debug window if it's open"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"

        # Also log to file
        logger.info(message)

        # Update debug window if open
        if hasattr(self, 'debug_text_widget') and self.debug_text_widget.winfo_exists():
            try:
                self.debug_text_widget.config(state=tk.NORMAL)
                self.debug_text_widget.insert(tk.END, formatted_message)
                self.debug_text_widget.see(tk.END)
                self.debug_text_widget.config(state=tk.DISABLED)
            except:
                pass


if __name__ == "__main__":
    root = tk.Tk()
    
    # Configure for full screen usage
    root.configure(bg='#1a1a1a')
    
    app = JiraTicketViewer(root)
    
    # Ensure the window is properly maximized
    root.update_idletasks()  # Process pending events
    
    root.mainloop()