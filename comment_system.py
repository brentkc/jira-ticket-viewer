"""
Comment system module for handling ticket comments and @mentions
"""

import tkinter as tk
import threading
from tkinter import messagebox
from datetime import datetime
from utils import format_datetime


class CommentSystemManager:
    def __init__(self, api_client, status_callback):
        """
        Initialize comment system manager
        
        Args:
            api_client: JiraAPIClient instance
            status_callback: Function to update status messages
        """
        self.api_client = api_client
        self.update_status = status_callback
        
        # UI references
        self.comment_text = None
        self.comments_text = None
        self.current_ticket = None
        
        # Autocomplete state
        self.available_users = []
        self.autocomplete_frame = None
        self.autocomplete_listbox = None
        self.autocomplete_active = False
        self.mention_start_pos = None
    
    def set_ui_references(self, comment_text, comments_text):
        """Set references to UI components"""
        self.comment_text = comment_text
        self.comments_text = comments_text
    
    def set_autocomplete_references(self, autocomplete_frame, autocomplete_listbox):
        """Set references to autocomplete UI components"""
        self.autocomplete_frame = autocomplete_frame
        self.autocomplete_listbox = autocomplete_listbox
    
    def set_current_ticket(self, ticket):
        """Set the current ticket for comment operations"""
        self.current_ticket = ticket
    
    def load_comments(self, ticket_key, limit=5):
        """Load comments for the specified ticket"""
        if not ticket_key:
            return
        
        def do_load():
            comments_data = self.api_client.get_ticket_comments(ticket_key)
            
            def update_ui():
                if not self.comments_text:
                    return
                
                self.comments_text.delete(1.0, tk.END)
                
                if comments_data and 'comments' in comments_data:
                    comments = comments_data['comments'][-limit:] if limit else comments_data['comments']
                    
                    if comments:
                        for comment in comments:
                            author = comment.get('author', {})
                            author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
                            created = comment.get('created', '')
                            body = comment.get('body', 'No content')
                            
                            # Format timestamp
                            created_str = format_datetime(created)
                            
                            self.comments_text.insert(tk.END, f"[{created_str}] {author_name}:\n{body}\n\n")
                    else:
                        self.comments_text.insert(tk.END, "No comments yet.")
                else:
                    self.comments_text.insert(tk.END, "No comments yet.")
            
            # Update UI in main thread
            if self.comments_text:
                self.comments_text.after(0, update_ui)
        
        # Load comments in background thread
        threading.Thread(target=do_load, daemon=True).start()
    
    def add_comment(self):
        """Add comment to the current ticket"""
        if not self.current_ticket or not self.comment_text:
            return
        
        comment_text = self.comment_text.get(1.0, tk.END).strip()
        
        if not comment_text:
            messagebox.showwarning("Warning", "Please enter a comment")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_add():
            result = self.api_client.add_comment_to_ticket(ticket_key, comment_text)
            
            if result:
                # Clear comment box and reload comments
                self.comment_text.after(0, lambda: self.comment_text.delete(1.0, tk.END))
                self.load_comments(ticket_key)
                messagebox.showinfo("Success", "Comment added successfully!")
            else:
                messagebox.showerror("Error", "Failed to add comment")
        
        # Add comment in background thread
        threading.Thread(target=do_add, daemon=True).start()
    
    def on_comment_key_release(self, event):
        """Handle key release in comment box for @mention autocomplete"""
        if not self.comment_text:
            return
        
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
        
        if not self.autocomplete_frame or not self.autocomplete_listbox:
            return
        
        # Filter users based on search text
        filtered_users = []
        search_lower = search_text.lower()
        
        for user in self.available_users:
            display_name = user.get('displayName', '')
            email = user.get('emailAddress', '')
            
            if (search_lower in display_name.lower() or 
                search_lower in email.lower()):
                filtered_users.append(user)
        
        # Update listbox
        self.autocomplete_listbox.delete(0, tk.END)
        for user in filtered_users[:10]:  # Limit to 10 results
            display_name = user.get('displayName', '')
            email = user.get('emailAddress', '')
            self.autocomplete_listbox.insert(tk.END, f"{display_name} ({email})")
        
        # Show autocomplete if we have matches
        if filtered_users:
            self.autocomplete_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
            self.autocomplete_active = True
        else:
            self.hide_autocomplete()
    
    def hide_autocomplete(self):
        """Hide autocomplete suggestions"""
        if self.autocomplete_frame:
            self.autocomplete_frame.grid_forget()
        self.autocomplete_active = False
        self.mention_start_pos = None
    
    def on_autocomplete_select(self, event=None):
        """Handle selection from autocomplete list"""
        if not self.autocomplete_active or not self.autocomplete_listbox:
            return
        
        selection = self.autocomplete_listbox.curselection()
        if selection and self.comment_text and self.mention_start_pos:
            selected_text = self.autocomplete_listbox.get(selection[0])
            
            # Extract email from "Name (email)" format
            if '(' in selected_text and selected_text.endswith(')'):
                email = selected_text.split('(')[1][:-1]
            else:
                email = selected_text
            
            # Replace the @mention text with the selected email
            current_pos = self.comment_text.index(tk.INSERT)
            self.comment_text.delete(f"{self.mention_start_pos} + 1 chars", current_pos)
            self.comment_text.insert(f"{self.mention_start_pos} + 1 chars", email + " ")
            
            self.hide_autocomplete()
    
    def load_available_users(self):
        """Load available users for autocomplete"""
        def do_load():
            users = self.api_client.get_project_users()
            if users:
                self.available_users = users
        
        # Load users in background thread
        threading.Thread(target=do_load, daemon=True).start()
    
    def add_mention(self, email):
        """Add a mention to the current comment"""
        if self.comment_text:
            current_text = self.comment_text.get(1.0, tk.END)
            if current_text.strip():
                # Add space if text doesn't end with space or newline
                if not current_text.rstrip().endswith((' ', '\n')):
                    self.comment_text.insert(tk.END, ' ')
            
            self.comment_text.insert(tk.END, f"@{email} ")
            self.comment_text.focus_set()
    
    def get_comment_mentions(self, comment_text):
        """Extract @mentions from comment text"""
        import re
        mention_pattern = r'@([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        matches = re.findall(mention_pattern, comment_text)
        return list(set(matches))  # Remove duplicates
    
    def format_comment_for_display(self, comment_data):
        """Format comment data for display"""
        author = comment_data.get('author', {})
        author_name = author.get('displayName', 'Unknown') if author else 'Unknown'
        created = comment_data.get('created', '')
        body = comment_data.get('body', 'No content')
        
        # Format timestamp
        created_str = format_datetime(created)
        
        return f"[{created_str}] {author_name}:\n{body}"
    
    def create_text_context_menu(self, text_widget):
        """Create context menu for text widgets"""
        context_menu = tk.Menu(text_widget, tearoff=0)
        
        def copy_text():
            try:
                selected_text = text_widget.selection_get()
                text_widget.clipboard_clear()
                text_widget.clipboard_append(selected_text)
            except tk.TclError:
                pass
        
        def copy_all():
            text_widget.clipboard_clear()
            text_widget.clipboard_append(text_widget.get(1.0, tk.END))
        
        def paste_text():
            try:
                clipboard_text = text_widget.clipboard_get()
                text_widget.insert(tk.INSERT, clipboard_text)
            except tk.TclError:
                pass
        
        def select_all():
            text_widget.tag_add(tk.SEL, "1.0", tk.END)
            text_widget.mark_set(tk.INSERT, "1.0")
            text_widget.see(tk.INSERT)
        
        context_menu.add_command(label="Copy Selection", command=copy_text)
        context_menu.add_command(label="Copy All", command=copy_all)
        context_menu.add_separator()
        context_menu.add_command(label="Paste", command=paste_text)
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=select_all)
        
        def show_context_menu(event):
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
        
        text_widget.bind("<Button-3>", show_context_menu)
        return context_menu