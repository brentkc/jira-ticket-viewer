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
        self.root.title("Jira Ticket Viewer - Psychology-Optimized UI")
        self.root.geometry("1800x1200")
        
        # Set minimum window size for better user experience
        self.root.minsize(1400, 900)
        
        # Initialize state variables
        self.selected_ticket = None
        self.context_toolbar_visible = False
        
        # Configure dark mode
        self.setup_dark_mode()
        
        # Jira configuration - Load from config file
        self.jira_url = "https://your-domain.atlassian.net"
        self.api_token = "YOUR_API_TOKEN_HERE"
        self.project_key = "YOUR_PROJECT_KEY"
        
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
    
    def setup_keyboard_shortcuts(self):
        """Setup keyboard shortcuts for power users"""
        self.root.bind('<Control-r>', lambda e: self.load_all_tickets_threaded())
        self.root.bind('<Control-n>', lambda e: self.open_create_ticket_window())
        self.root.bind('<F5>', lambda e: self.load_all_tickets_threaded())
        self.root.bind('<Control-f>', lambda e: self.search_entry.focus_set())
        self.root.bind('<Return>', self.on_enter_pressed)
        
    def on_enter_pressed(self, event):
        """Handle Enter key context-sensitively"""
        focused = self.root.focus_get()
        if focused == self.search_entry:
            self.search_tickets()
        elif hasattr(self, 'comment_entry') and focused == self.comment_entry:
            self.add_comment()
        
    def on_search_focus(self, event):
        """Clear placeholder text on focus"""
        if self.search_entry.get() == "🔍 Search tickets...":
            self.search_entry.delete(0, tk.END)
            
    def on_search_unfocus(self, event):
        """Restore placeholder if empty"""
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, "🔍 Search tickets...")
    
    def focus_comment(self):
        """Focus the comment entry area"""
        if hasattr(self, 'comment_entry'):
            self.comment_entry.focus_set()
        
    def attach_file(self):
        """Quick file attachment"""
        from tkinter import filedialog
        filename = filedialog.askopenfilename(title="Attach File")
        if filename:
            messagebox.showinfo("Attachment", f"File {filename} would be attached")
    
    def show_context_toolbar(self):
        """Show the contextual toolbar when ticket is selected"""
        self.context_toolbar.grid()
        self.context_toolbar_visible = True
        
    def hide_context_toolbar(self):
        """Hide the contextual toolbar when no ticket is selected"""
        self.context_toolbar.grid_remove()
        self.context_toolbar_visible = False
        
    def clear_details(self):
        """Clear the details panel"""
        self.details_text.config(state='normal')
        self.details_text.delete(1.0, tk.END)
        self.details_text.config(state='disabled')
        if hasattr(self, 'comment_entry'):
            self.comment_entry.delete(1.0, tk.END)
        
    def enable_all_actions(self):
        """Enable all action buttons when ticket is selected"""
        for btn in self.all_action_buttons:
            btn.config(state="normal")
            
    def disable_all_actions(self):
        """Disable all action buttons when no ticket is selected"""
        for btn in self.all_action_buttons:
            btn.config(state="disabled")
        
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
        
        # Configure root window
        self.root.configure(bg=bg_primary)

    def setup_ui(self):
        """Setup the psychology-optimized user interface"""
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
        
        # Configure optimized columns for F-pattern scanning
        self.tree.heading("Key", text="ID", command=lambda: self.sort_treeview("Key", False))
        self.tree.column("Key", width=70, minwidth=70)
        
        self.tree.heading("Priority", text="⚡", command=lambda: self.sort_treeview("Priority", False))
        self.tree.column("Priority", width=40, minwidth=40)
        
        self.tree.heading("Summary", text="Summary")
        self.tree.column("Summary", width=400, minwidth=300)
        
        self.tree.heading("Status", text="Status", command=lambda: self.sort_treeview("Status", False))
        self.tree.column("Status", width=100, minwidth=80)
        
        self.tree.heading("Assignee", text="Assignee")
        self.tree.column("Assignee", width=120, minwidth=100)
        
        self.tree.heading("Age", text="Age", command=lambda: self.sort_treeview("Age", False))
        self.tree.column("Age", width=60, minwidth=60)
        
        tree_scrollbar = ttk.Scrollbar(tickets_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure visual priority tags
        self.tree.tag_configure('sla_missed', background='#4a2828', foreground='#ff9999')
        self.tree.tag_configure('critical', background='#3d1a1a', foreground='#ff6b6b')
        self.tree.tag_configure('high', background='#3d2a1a', foreground='#ffa726')
        self.tree.tag_configure('selected', background='#0078d4', foreground='#ffffff')
        
        # Right panel - Context-sensitive details
        right_panel = ttk.Frame(content_frame)
        right_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_panel.rowconfigure(1, weight=1)
        
        # Context toolbar (hidden initially)
        self.context_toolbar = ttk.Frame(right_panel)
        self.context_toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        self.context_toolbar.grid_remove()  # Hidden by default
        
        # Quick action buttons (contextual)
        self.quick_resolve_btn = ttk.Button(self.context_toolbar, text="✅ Resolve", command=self.resolve_ticket, state="disabled")
        self.quick_resolve_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.quick_assign_btn = ttk.Button(self.context_toolbar, text="👤 Assign to Me", command=self.assign_to_me, state="disabled")
        self.quick_assign_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.quick_comment_btn = ttk.Button(self.context_toolbar, text="💬 Comment", command=self.focus_comment, state="disabled")
        self.quick_comment_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Ticket details with better information hierarchy
        details_frame = ttk.LabelFrame(right_panel, text="📋 Details", padding="10")
        details_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        details_frame.rowconfigure(0, weight=1)
        details_frame.columnconfigure(0, weight=1)
        
        self.details_text = scrolledtext.ScrolledText(details_frame, width=35, height=12, wrap=tk.WORD,
                                                    bg='#2d2d2d', fg='#ffffff', insertbackground='#ffffff',
                                                    font=('Segoe UI', 10), state='disabled')
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Quick comment area (more prominent)
        comment_frame = ttk.LabelFrame(right_panel, text="💬 Quick Comment", padding="10")
        comment_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        comment_frame.columnconfigure(0, weight=1)
        
        self.comment_entry = scrolledtext.ScrolledText(comment_frame, height=4, wrap=tk.WORD,
                                                     bg='#2d2d2d', fg='#ffffff', insertbackground='#ffffff',
                                                     font=('Segoe UI', 10))
        self.comment_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        comment_buttons = ttk.Frame(comment_frame)
        comment_buttons.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        self.submit_btn = ttk.Button(comment_buttons, text="💬 Add Comment", command=self.add_comment, state="disabled")
        self.submit_btn.pack(side=tk.RIGHT)
        
        self.attach_btn = ttk.Button(comment_buttons, text="📎", width=3, command=self.attach_file, state="disabled")
        self.attach_btn.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Advanced actions (collapsed by default)
        self.advanced_frame = ttk.LabelFrame(right_panel, text="⚡ More Actions", padding="10")
        self.advanced_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        
        advanced_row1 = ttk.Frame(self.advanced_frame)
        advanced_row1.pack(fill=tk.X, pady=(0, 5))
        
        self.close_btn = ttk.Button(advanced_row1, text="❌ Close", command=self.close_ticket, state="disabled")
        self.close_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.open_btn = ttk.Button(advanced_row1, text="🔓 Reopen", command=self.open_ticket, state="disabled")
        self.open_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.browser_btn = ttk.Button(advanced_row1, text="🌐 Browser", command=self.open_ticket_in_browser, state="disabled")
        self.browser_btn.pack(side=tk.LEFT)
        
        advanced_row2 = ttk.Frame(self.advanced_frame)
        advanced_row2.pack(fill=tk.X)
        
        self.view_attachments_btn = ttk.Button(advanced_row2, text="🖼️ Images", command=self.view_attachments, state="disabled")
        self.view_attachments_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.html_viewer_btn = ttk.Button(advanced_row2, text="📊 HTML View", command=self.open_html_viewer, state="disabled")
        self.html_viewer_btn.pack(side=tk.LEFT)
        
        # Configure grid weights for responsive layout
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)  # Content area expands
        
        # Store references for state management
        self.all_action_buttons = [
            self.quick_resolve_btn, self.quick_assign_btn, self.quick_comment_btn,
            self.submit_btn, self.attach_btn, self.close_btn, self.open_btn, 
            self.browser_btn, self.view_attachments_btn, self.html_viewer_btn
        ]
        
        # Setup event bindings
        self.tree.bind('<<TreeviewSelect>>', self.on_ticket_select)
        self.tree.bind('<Double-1>', self.on_ticket_double_click)
        
        # Enable drag and drop and keyboard shortcuts
        self.setup_keyboard_shortcuts()
        
        # Add method implementations for compatibility
        self.comment_text = self.comment_entry  # Alias for compatibility
        self.comments_text = self.details_text  # Alias for compatibility

    def search_tickets(self, event=None):
        """Enhanced search with smart filtering"""
        search_term = self.search_entry.get().strip()
        if search_term == "🔍 Search tickets..." or not search_term:
            # Show all tickets if no search term
            self.filter_tickets()
            return
            
        # Filter current tickets based on search
        if not hasattr(self, 'all_tickets') or not self.all_tickets:
            return
            
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        matching_tickets = []
        search_lower = search_term.lower()
        
        for issue in self.all_tickets:
            fields = issue.get('fields', {})
            key = issue.get('key', '').lower()
            summary = fields.get('summary', '').lower()
            description = fields.get('description', '')
            desc_text = description if isinstance(description, str) else ''
            
            # Search in key, summary, and description
            if (search_lower in key or 
                search_lower in summary or 
                search_lower in desc_text.lower()):
                matching_tickets.append(issue)
                
        self.update_ticket_list(matching_tickets)
        self.status_label.config(text=f"Found {len(matching_tickets)} tickets matching '{search_term}'")

    # Add all the original methods with proper structure
    def make_jira_request(self, endpoint, method="GET", params=None, data=None, files=None):
        """Make authenticated request to Jira API"""
        url = f"{self.jira_url}/rest/api/2/{endpoint}"
        auth = HTTPBasicAuth(self.user_email, self.api_token)
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
            messagebox.showerror("API Error", error_msg)
            return None
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
            return None

    def load_all_tickets_threaded(self):
        """Load all tickets in background thread"""
        self.refresh_btn.config(state="disabled")
        self.status_label.config(text="Loading tickets...")
        threading.Thread(target=self.load_all_tickets, daemon=True).start()
        
    def load_all_tickets(self):
        """Load all tickets from Jira"""
        try:
            # Build JQL to filter only Incident and Service request tickets
            issue_type_ids = list(self.issue_types.values())  # ["11395", "11396"]
            jql = f'project = ITS AND issuetype in ({",".join(issue_type_ids)})'
            
            params = {
                'jql': jql,
                'maxResults': 100,
                'startAt': 0
            }
            
            data = self.make_jira_request("search", params=params)
            
            if data and 'issues' in data:
                self.root.after(0, self.update_ticket_list, data['issues'])
                self.root.after(0, lambda: self.status_label.config(text=f"Loaded {len(data['issues'])} tickets"))
            else:
                self.root.after(0, lambda: self.status_label.config(text="Failed to load tickets"))
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"Error: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.refresh_btn.config(state="normal"))
            # Apply default filter after loading
            self.root.after(100, self.filter_tickets)

    def update_ticket_list(self, issues):
        """Update the treeview with optimized ticket display"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Store tickets for filtering
        self.all_tickets = issues
        
        # Add tickets to treeview with improved data presentation
        for issue in issues:
            fields = issue.get('fields', {})
            
            key = issue.get('key', 'Unknown')
            
            priority = fields.get('priority', {})
            priority_name = priority.get('name', 'Unknown') if priority else 'Unknown'
            
            summary = fields.get('summary', 'No summary')
            
            status = fields.get('status', {})
            status_name = status.get('name', 'Unknown') if status else 'Unknown'
            
            assignee = fields.get('assignee')
            assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
            
            # Calculate age in human readable format
            created = fields.get('created', '')
            if created:
                try:
                    created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    now = datetime.now(created_dt.tzinfo)
                    age_hours = (now - created_dt).total_seconds() / 3600
                    if age_hours < 24:
                        age_str = f"{int(age_hours)}h"
                    elif age_hours < 168:  # 7 days
                        age_str = f"{int(age_hours/24)}d"
                    else:
                        age_str = f"{int(age_hours/168)}w"
                except:
                    age_str = "?"
            else:
                age_str = "?"
            
            # Priority symbol
            priority_symbol = {
                'critical': '🔴',
                'high': '🟠', 
                'medium': '🟡',
                'low': '🔵'
            }.get(priority_name.lower(), '⚪')
            
            values = (key, priority_symbol, summary, status_name, assignee_name, age_str)
            
            # Determine tags for this ticket with priority-based coloring
            tags = [key]
            if self.is_sla_missed(issue):
                tags.append('sla_missed')
            elif priority_name.lower() == 'critical':
                tags.append('critical')
            elif priority_name.lower() == 'high':
                tags.append('high')
            
            self.tree.insert("", "end", values=values, tags=tags)

    def filter_tickets(self, event=None):
        """Smart filtering with psychology-based defaults"""
        if not hasattr(self, 'all_tickets') or not self.all_tickets:
            return
            
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        ticket_filter = self.ticket_filter_var.get()
        hide_completed = self.hide_completed_var.get()
        user_email = self.user_email
        
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
            elif ticket_filter == "All Open":
                # Only show non-completed tickets
                status = fields.get('status', {})
                status_name = status.get('name', '').lower() if status else ''
                is_completed = any(completed_status in status_name for completed_status in completed_statuses)
                if is_completed:
                    continue
            elif ticket_filter == "Unassigned":
                assignee = fields.get('assignee')
                if assignee:  # Skip if has assignee
                    continue
            
            # Check completed status filter
            if hide_completed:
                status = fields.get('status', {})
                status_name = status.get('name', '').lower() if status else ''
                is_completed = any(completed_status in status_name for completed_status in completed_statuses)
                if is_completed:
                    continue
            
            tickets_to_show.append(issue)
        
        # Update display with filtered results
        self.update_ticket_list(tickets_to_show)
        
        # Update status message
        filter_text = f" ({ticket_filter})" if ticket_filter != "All Tickets" else ""
        completed_text = " (hiding completed)" if hide_completed else ""
        self.status_label.config(text=f"Showing {len(tickets_to_show)} tickets{filter_text}{completed_text}")
        
        # Store filtered tickets
        self.filtered_tickets = tickets_to_show

    def on_ticket_select(self, event):
        """Handle ticket selection with contextual UI updates"""
        selection = self.tree.selection()
        if not selection:
            self.current_ticket = None
            self.hide_context_toolbar()
            self.clear_details()
            return
            
        # Show context toolbar
        self.show_context_toolbar()
        self.enable_all_actions()

    def on_ticket_double_click(self, event):
        """Handle double-click - open in browser"""
        self.on_ticket_select(event)
        self.open_ticket_in_browser()

    # Placeholder methods - add your existing implementations
    def open_create_ticket_window(self):
        messagebox.showinfo("Feature", "Create ticket window would open")
        
    def open_dashboard(self):
        messagebox.showinfo("Feature", "Dashboard would open")
        
    def resolve_ticket(self):
        messagebox.showinfo("Feature", "Ticket would be resolved")
        
    def assign_to_me(self):
        messagebox.showinfo("Feature", "Ticket would be assigned to you")
        
    def add_comment(self):
        messagebox.showinfo("Feature", "Comment would be added")
        
    def close_ticket(self):
        messagebox.showinfo("Feature", "Ticket would be closed")
        
    def open_ticket(self):
        messagebox.showinfo("Feature", "Ticket would be reopened")
        
    def open_ticket_in_browser(self):
        """Open ticket in web browser"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            url = f"{self.jira_url}/browse/{ticket_key}"
            webbrowser.open(url)
        
    def view_attachments(self):
        messagebox.showinfo("Feature", "Attachments would be shown")
        
    def open_html_viewer(self):
        messagebox.showinfo("Feature", "HTML viewer would open")
        
    def sort_treeview(self, col, reverse):
        messagebox.showinfo("Feature", f"Would sort by {col}")

    def clear_search(self):
        """Clear search and show all tickets"""
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, "🔍 Search tickets...")
        self.filter_tickets()

if __name__ == "__main__":
    root = tk.Tk()
    app = JiraTicketViewer(root)
    
    # Configure window icon and additional properties
    try:
        root.state('zoomed')  # Maximize on Windows
    except:
        pass
    
    root.mainloop()