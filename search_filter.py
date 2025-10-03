"""
Search and filtering functionality for Jira tickets
"""

import threading
from tkinter import messagebox
from config import TICKET_FILTER_OPTIONS, ISSUE_TYPE_FILTER_OPTIONS


class SearchFilterManager:
    def __init__(self, api_client, tree_widget, status_callback, update_tickets_callback):
        """
        Initialize search and filter manager
        
        Args:
            api_client: JiraAPIClient instance
            tree_widget: Treeview widget to update
            status_callback: Function to update status messages
            update_tickets_callback: Function to update ticket list
        """
        self.api_client = api_client
        self.tree = tree_widget
        self.update_status = status_callback
        self.update_tickets_callback = update_tickets_callback
        
        # Filter state
        self.all_tickets = []
        self.search_entry = None
        self.ticket_filter_var = None
        self.issue_type_var = None
        self.hide_completed_var = None
        self.email_callback = None
    
    def set_ui_references(self, search_entry, ticket_filter_var, issue_type_var, 
                         hide_completed_var, email_callback):
        """Set references to UI components"""
        self.search_entry = search_entry
        self.ticket_filter_var = ticket_filter_var
        self.issue_type_var = issue_type_var
        self.hide_completed_var = hide_completed_var
        self.email_callback = email_callback
    
    def set_tickets(self, tickets):
        """Update the stored tickets list for filtering"""
        self.all_tickets = tickets
    
    def search_tickets(self, event=None):
        """Search tickets based on text content"""
        if not self.search_entry:
            return
        
        search_text = self.search_entry.get().strip()
        
        if not search_text:
            messagebox.showwarning("Warning", "Please enter search text")
            return
        
        self.update_status(f"Searching for: {search_text}...")
        
        def do_search():
            data = self.api_client.search_tickets(search_text)
            
            if data and 'issues' in data:
                self.all_tickets = data['issues']
                self.update_tickets_callback(data['issues'])
                self.update_status(f"Found {len(data['issues'])} tickets matching '{search_text}'")
            else:
                self.update_status(f"No tickets found matching '{search_text}'")
        
        # Run search in background thread
        threading.Thread(target=do_search, daemon=True).start()
    
    def clear_search(self):
        """Clear search and reload all tickets"""
        if self.search_entry:
            self.search_entry.delete(0, 'end')
        
        # Trigger reload of all tickets
        self.update_status("Reloading all tickets...")
        
        def do_reload():
            data = self.api_client.load_all_tickets()
            if data and 'issues' in data:
                self.all_tickets = data['issues']
                self.update_tickets_callback(data['issues'])
                self.update_status(f"Loaded {len(data['issues'])} tickets")
            else:
                self.update_status("Failed to reload tickets")
        
        threading.Thread(target=do_reload, daemon=True).start()
    
    def filter_tickets(self, event=None):
        """Filter tickets based on selected criteria"""
        if not self.all_tickets:
            return
        
        # Clear current display
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get filter criteria
        ticket_filter = self.ticket_filter_var.get() if self.ticket_filter_var else "All Tickets"
        issue_type_filter = self.issue_type_var.get() if self.issue_type_var else "All"
        hide_completed = self.hide_completed_var.get() if self.hide_completed_var else False
        user_email = self.email_callback() if self.email_callback else ""
        
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
                if assignee:  # Has assignee, skip
                    continue
            
            # Filter by issue type
            if issue_type_filter != "All":
                issue_type = fields.get('issuetype', {}).get('name', '')
                if issue_type != issue_type_filter:
                    continue
            
            # Filter by completion status
            if hide_completed:
                status = fields.get('status', {}).get('name', '').lower()
                if status in completed_statuses:
                    continue
            
            tickets_to_show.append(issue)
        
        # Update display with filtered tickets
        self.update_tickets_callback(tickets_to_show)
        
        # Update status
        total = len(self.all_tickets)
        shown = len(tickets_to_show)
        if shown == total:
            self.update_status(f"Showing all {total} tickets")
        else:
            self.update_status(f"Showing {shown} of {total} tickets (filtered)")
    
    def get_filter_options(self):
        """Get available filter options"""
        return {
            'ticket_filters': TICKET_FILTER_OPTIONS,
            'issue_type_filters': ISSUE_TYPE_FILTER_OPTIONS
        }
    
    def copy_ticket_url(self):
        """Copy selected ticket URL to clipboard"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            url = self.api_client.get_ticket_url(ticket_key)
            
            # Copy to clipboard (using tree's root widget)
            root = self.tree.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(url)
            self.update_status(f"Copied URL for {ticket_key} to clipboard")
    
    def open_ticket_in_browser(self):
        """Open selected ticket in browser"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            self.api_client.open_ticket_in_browser(ticket_key)
            self.update_status(f"Opened {ticket_key} in browser")
    
    def copy_ticket_key(self):
        """Copy selected ticket key to clipboard"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            ticket_key = self.tree.item(item)['values'][0]
            
            # Copy to clipboard
            root = self.tree.winfo_toplevel()
            root.clipboard_clear()
            root.clipboard_append(ticket_key)
            self.update_status(f"Copied {ticket_key} to clipboard")