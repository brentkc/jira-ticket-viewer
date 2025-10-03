"""
HTML viewer module for displaying tickets in a formatted view with editing capabilities
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from datetime import datetime
from utils import format_datetime


class HTMLTicketViewer:
    def __init__(self, api_client, root_window, ticket_ops_manager, comment_system):
        """
        Initialize HTML ticket viewer
        
        Args:
            api_client: JiraAPIClient instance
            root_window: Main application window
            ticket_ops_manager: TicketOperationsManager instance
            comment_system: CommentSystemManager instance
        """
        self.api_client = api_client
        self.root_window = root_window
        self.ticket_ops_manager = ticket_ops_manager
        self.comment_system = comment_system
        
        # Viewer window reference
        self.html_viewer_window = None
        self.current_ticket = None
        
        # UI components
        self.html_title_label = None
        self.html_content = None
        self.html_description_editor = None
        self.html_comment_editor = None
        self.save_desc_btn = None
        self.html_add_comment_btn = None
        self.html_close_btn = None
        self.html_resolve_btn = None
    
    def open_html_viewer(self):
        """Open HTML viewer window for tickets with editing capability"""
        if self.html_viewer_window and self.html_viewer_window.winfo_exists():
            self.html_viewer_window.lift()
            return
        
        self.html_viewer_window = tk.Toplevel(self.root_window)
        self.html_viewer_window.title("Jira Ticket HTML Viewer & Editor")
        self.html_viewer_window.geometry("1000x800")
        self.html_viewer_window.configure(bg='#1e1e1e')
        self.html_viewer_window.protocol("WM_DELETE_WINDOW", self.on_html_viewer_close)
        
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
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # View tab (read-only formatted content)
        view_frame = ttk.Frame(notebook)
        notebook.add(view_frame, text="📖 View")
        
        self.html_content = scrolledtext.ScrolledText(view_frame, wrap=tk.WORD,
                                                     bg='#2d2d2d', fg='#ffffff', 
                                                     insertbackground='#ffffff',
                                                     font=('Segoe UI', 10),
                                                     state='disabled')
        self.html_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Edit tab (editable description)
        edit_frame = ttk.Frame(notebook)
        notebook.add(edit_frame, text="✏️ Edit Description")
        
        # Description editor
        desc_label = ttk.Label(edit_frame, text="Description:", font=('Segoe UI', 10, 'bold'))
        desc_label.pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.html_description_editor = scrolledtext.ScrolledText(edit_frame, wrap=tk.WORD,
                                                               bg='#3c3c3c', fg='#ffffff',
                                                               insertbackground='#ffffff',
                                                               font=('Segoe UI', 10))
        self.html_description_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Save button for description
        self.save_desc_btn = ttk.Button(edit_frame, text="Save Description", 
                                       command=self.save_description, state="disabled")
        self.save_desc_btn.pack(pady=5)
        
        # Comments tab (add comments)
        comments_frame = ttk.Frame(notebook)
        notebook.add(comments_frame, text="💬 Add Comment")
        
        comment_label = ttk.Label(comments_frame, text="Add Comment:", font=('Segoe UI', 10, 'bold'))
        comment_label.pack(anchor=tk.W, padx=5, pady=(5, 0))
        
        self.html_comment_editor = scrolledtext.ScrolledText(comments_frame, wrap=tk.WORD, height=6,
                                                           bg='#3c3c3c', fg='#ffffff',
                                                           insertbackground='#ffffff',
                                                           font=('Segoe UI', 10))
        self.html_comment_editor.pack(fill=tk.X, padx=5, pady=5)
        
        # Add comment button
        self.html_add_comment_btn = ttk.Button(comments_frame, text="Add Comment", 
                                             command=self.add_comment_from_html, state="disabled")
        self.html_add_comment_btn.pack(pady=5)
        
        # Instructions
        instructions = """
Instructions:
• View tab: Read-only formatted view of the ticket with all details
• Edit Description tab: Edit the ticket description and save changes
• Add Comment tab: Add new comments to the ticket

Use the Close Ticket and Resolve buttons for quick status changes.
        """
        
        instructions_label = ttk.Label(comments_frame, text=instructions, 
                                     font=('Segoe UI', 9), foreground='#cccccc')
        instructions_label.pack(fill=tk.X, padx=5, pady=10)
    
    def update_html_viewer(self, issue):
        """Update the HTML viewer with ticket content"""
        if not self.html_viewer_window or not self.html_viewer_window.winfo_exists():
            return
        
        self.current_ticket = issue
        fields = issue.get('fields', {})
        ticket_key = issue.get('key', 'Unknown')
        
        # Update title
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
        
        # Enable buttons
        self.save_desc_btn.config(state="normal")
        self.html_add_comment_btn.config(state="normal")
        self.html_close_btn.config(state="normal")
        self.html_resolve_btn.config(state="normal")
        
        # Load comments in background
        self.load_comments_for_html_viewer(ticket_key)
    
    def build_ticket_html_content(self, issue):
        """Build formatted text content for the ticket"""
        fields = issue.get('fields', {})
        
        content = []
        content.append("=" * 80)
        content.append(f"TICKET: {issue.get('key', 'Unknown')}")
        content.append("=" * 80)
        content.append("")
        
        # Basic info
        content.append("BASIC INFORMATION:")
        content.append("-" * 20)
        content.append(f"Summary: {fields.get('summary', 'No summary')}")
        
        issue_type = fields.get('issuetype', {})
        content.append(f"Type: {issue_type.get('name', 'Unknown') if issue_type else 'Unknown'}")
        
        status = fields.get('status', {})
        content.append(f"Status: {status.get('name', 'Unknown') if status else 'Unknown'}")
        
        priority = fields.get('priority', {})
        if priority:
            content.append(f"Priority: {priority.get('name', 'Not set')}")
        
        reporter = fields.get('reporter', {})
        if reporter:
            content.append(f"Reporter: {reporter.get('displayName', 'Unknown')}")
        
        assignee = fields.get('assignee', {})
        if assignee:
            content.append(f"Assignee: {assignee.get('displayName', 'Unassigned')}")
        else:
            content.append("Assignee: Unassigned")
        
        created = fields.get('created', '')
        if created:
            content.append(f"Created: {format_datetime(created)}")
        
        updated = fields.get('updated', '')
        if updated:
            content.append(f"Updated: {format_datetime(updated)}")
        
        content.append("")
        
        # Description
        content.append("DESCRIPTION:")
        content.append("-" * 20)
        description = fields.get('description', 'No description provided')
        content.append(description)
        content.append("")
        
        # Attachments
        attachments = fields.get('attachment', [])
        if attachments:
            content.append("ATTACHMENTS:")
            content.append("-" * 20)
            for attachment in attachments:
                filename = attachment.get('filename', 'Unknown')
                size = attachment.get('size', 0)
                content.append(f"📎 {filename} ({self.format_file_size(size)})")
            content.append("")
        
        # Comments placeholder (will be updated separately)
        content.append("COMMENTS:")
        content.append("-" * 20)
        content.append("Loading comments...")
        content.append("")
        
        return "\n".join(content)
    
    def format_file_size(self, size_bytes):
        """Format file size in human readable format"""
        from utils import format_file_size
        return format_file_size(size_bytes)
    
    def load_comments_for_html_viewer(self, ticket_key):
        """Load comments for the HTML viewer"""
        def do_load():
            comments_data = self.api_client.get_ticket_comments(ticket_key)
            
            def update_comments():
                if (not self.html_viewer_window or not self.html_viewer_window.winfo_exists() or
                    not self.current_ticket or self.current_ticket.get('key') != ticket_key):
                    return
                
                # Build comments content
                comments_content = []
                
                if comments_data and 'comments' in comments_data:
                    comments = comments_data['comments']
                    
                    if comments:
                        for comment in comments:
                            author = comment.get('author', {})
                            author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                            created = comment.get('created', '')
                            body = comment.get('body', 'No content')
                            
                            created_str = format_datetime(created)
                            comments_content.append(f"[{created_str}] {author_name}:")
                            comments_content.append(body)
                            comments_content.append("")
                    else:
                        comments_content.append("No comments yet.")
                else:
                    comments_content.append("No comments yet.")
                
                # Update the view content by replacing the comments section
                current_content = self.html_content.get(1.0, tk.END)
                lines = current_content.split('\n')
                
                # Find and replace comments section
                comments_start = -1
                for i, line in enumerate(lines):
                    if line == "COMMENTS:":
                        comments_start = i
                        break
                
                if comments_start >= 0:
                    # Replace from "COMMENTS:" to end
                    new_lines = lines[:comments_start]
                    new_lines.extend(["COMMENTS:", "-" * 20])
                    new_lines.extend(comments_content)
                    
                    new_content = '\n'.join(new_lines)
                    
                    self.html_content.config(state='normal')
                    self.html_content.delete(1.0, tk.END)
                    self.html_content.insert(1.0, new_content)
                    self.html_content.config(state='disabled')
            
            # Update UI in main thread
            self.html_viewer_window.after(0, update_comments)
        
        # Load comments in background thread
        threading.Thread(target=do_load, daemon=True).start()
    
    def save_description(self):
        """Save edited description"""
        if not self.current_ticket:
            return
        
        new_description = self.html_description_editor.get(1.0, tk.END).strip()
        ticket_key = self.current_ticket.get('key')
        
        def do_save():
            # Update ticket description
            update_data = {
                "fields": {
                    "description": new_description
                }
            }
            
            result = self.api_client.make_jira_request(f"issue/{ticket_key}", method="PUT", data=update_data)
            
            if result is not None:
                messagebox.showinfo("Success", "Description updated successfully!")
                # Refresh the current ticket
                self.ticket_ops_manager.refresh_current_ticket()
            else:
                messagebox.showerror("Error", "Failed to update description")
        
        # Save in background thread
        threading.Thread(target=do_save, daemon=True).start()
    
    def add_comment_from_html(self):
        """Add comment from HTML viewer"""
        if not self.current_ticket:
            return
        
        comment_text = self.html_comment_editor.get(1.0, tk.END).strip()
        
        if not comment_text:
            messagebox.showwarning("Warning", "Please enter a comment")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_add():
            result = self.api_client.add_comment_to_ticket(ticket_key, comment_text)
            
            if result:
                messagebox.showinfo("Success", "Comment added successfully!")
                self.html_comment_editor.delete(1.0, tk.END)
                # Refresh the HTML viewer
                self.load_comments_for_html_viewer(ticket_key)
                # Refresh the current ticket
                self.ticket_ops_manager.refresh_current_ticket()
            else:
                messagebox.showerror("Error", "Failed to add comment")
        
        # Add comment in background thread
        threading.Thread(target=do_add, daemon=True).start()
    
    def close_ticket_from_html(self):
        """Close ticket from HTML viewer"""
        if self.ticket_ops_manager:
            self.ticket_ops_manager.close_ticket()
    
    def resolve_ticket_from_html(self):
        """Resolve ticket from HTML viewer"""
        if self.ticket_ops_manager:
            self.ticket_ops_manager.resolve_ticket()
    
    def on_html_viewer_close(self):
        """Handle HTML viewer window closing"""
        if self.html_viewer_window:
            self.html_viewer_window.destroy()
            self.html_viewer_window = None
    
    def is_open(self):
        """Check if HTML viewer is open"""
        return self.html_viewer_window and self.html_viewer_window.winfo_exists()
    
    def refresh_current_ticket(self):
        """Refresh the currently displayed ticket"""
        if self.current_ticket and self.is_open():
            # Get fresh ticket data
            ticket_key = self.current_ticket.get('key')
            
            def do_refresh():
                updated_ticket = self.api_client.get_ticket_details(ticket_key)
                if updated_ticket:
                    self.html_viewer_window.after(0, lambda: self.update_html_viewer(updated_ticket))
            
            threading.Thread(target=do_refresh, daemon=True).start()