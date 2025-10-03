"""
Ticket operations module for creating, updating, and managing Jira tickets
"""

import threading
import tempfile
import io
from tkinter import messagebox
from PIL import ImageGrab


class TicketOperationsManager:
    def __init__(self, api_client, status_callback, refresh_callback):
        """
        Initialize ticket operations manager
        
        Args:
            api_client: JiraAPIClient instance
            status_callback: Function to update status messages
            refresh_callback: Function to refresh ticket data
        """
        self.api_client = api_client
        self.update_status = status_callback
        self.refresh_callback = refresh_callback
        
        # Current ticket reference
        self.current_ticket = None
        self.email_callback = None
    
    def set_email_callback(self, email_callback):
        """Set callback to get user email"""
        self.email_callback = email_callback
    
    def set_current_ticket(self, ticket):
        """Set the current ticket for operations"""
        self.current_ticket = ticket
    
    def get_current_ticket(self):
        """Get the current ticket"""
        return self.current_ticket
    
    def assign_to_me(self):
        """Assign the current ticket to the logged-in user"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        ticket_key = self.current_ticket.get('key')
        my_email = self.email_callback() if self.email_callback else ""
        
        if not my_email:
            messagebox.showerror("Error", "Email not configured")
            return
        
        def assign_ticket():
            # Get account ID for the user - REQUIRED for Jira Cloud
            user_search = self.api_client.search_users(my_email)
            
            if user_search and len(user_search) > 0:
                account_id = user_search[0].get('accountId')
                
                # Use accountId for assignment
                result = self.api_client.assign_ticket(ticket_key, account_id)
                
                if result is not None:
                    messagebox.showinfo("Success", f"Ticket {ticket_key} assigned to you!")
                    self.refresh_callback()
                else:
                    messagebox.showerror("Error", f"Failed to assign ticket {ticket_key}")
            else:
                messagebox.showerror("Error", f"User not found: {my_email}\nMake sure the email is correct and has Jira access.")
        
        # Run assignment in background thread
        threading.Thread(target=assign_ticket, daemon=True).start()
    
    def close_ticket(self):
        """Close the selected ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_close():
            # Get available transitions
            transitions_data = self.api_client.get_available_transitions(ticket_key)
            
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
            result = self.api_client.transition_ticket(ticket_key, selected_transition['id'])
            
            if result is not None:
                messagebox.showinfo("Success", f"Ticket {ticket_key} closed successfully!")
                self.refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to close ticket")
        
        # Run in background thread
        threading.Thread(target=do_close, daemon=True).start()
    
    def resolve_ticket(self):
        """Resolve the selected ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_resolve():
            # Get available transitions
            transitions_data = self.api_client.get_available_transitions(ticket_key)
            
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
            result = self.api_client.transition_ticket(ticket_key, selected_transition['id'])
            
            if result is not None:
                messagebox.showinfo("Success", f"Ticket {ticket_key} resolved successfully!")
                self.refresh_callback()
            else:
                messagebox.showerror("Error", "Failed to resolve ticket")
        
        # Run in background thread
        threading.Thread(target=do_resolve, daemon=True).start()
    
    def create_ticket(self, summary, description, issue_type_name, reporter_email=None, assignee_email=None):
        """Create a new ticket"""
        if not summary.strip():
            messagebox.showerror("Error", "Summary is required")
            return False
        
        # Get issue type ID from name
        from config import ISSUE_TYPES
        issue_type_id = ISSUE_TYPES.get(issue_type_name)
        
        if not issue_type_id:
            messagebox.showerror("Error", f"Invalid issue type: {issue_type_name}")
            return False
        
        def do_create():
            # Get account IDs if needed
            reporter_account_id = None
            assignee_account_id = None
            
            # Get reporter account ID
            if reporter_email:
                user_search = self.api_client.search_users(reporter_email)
                if user_search and len(user_search) > 0:
                    reporter_account_id = user_search[0].get('accountId')
                else:
                    messagebox.showwarning("Warning", f"Reporter '{reporter_email}' not found. Using current user.")
            
            # Get assignee account ID if specified
            if assignee_email:
                user_search = self.api_client.search_users(assignee_email)
                if user_search and len(user_search) > 0:
                    assignee_account_id = user_search[0].get('accountId')
                else:
                    response = messagebox.askyesno("User Not Found", 
                        f"Assignee '{assignee_email}' not found.\nCreate ticket unassigned?")
                    if not response:
                        return
            
            # Create the ticket
            result = self.api_client.create_ticket(summary, description, issue_type_id, assignee_account_id)
            
            if result and 'key' in result:
                ticket_key = result['key']
                messagebox.showinfo("Success", f"Ticket {ticket_key} created successfully!")
                self.refresh_callback()
                return True
            else:
                messagebox.showerror("Error", "Failed to create ticket")
                return False
        
        # Run in background thread
        threading.Thread(target=do_create, daemon=True).start()
        return True
    
    def paste_screenshot(self):
        """Paste screenshot from clipboard and attach to current ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        try:
            ticket_key = self.current_ticket.get('key')
            
            # Get image from clipboard
            img = ImageGrab.grabclipboard()
            
            if img is not None:
                # Convert to bytes
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_file.write(img_bytes.getvalue())
                    temp_path = temp_file.name
                
                # Upload to Jira
                result = self.api_client.add_attachment(ticket_key, temp_path)
                
                if result:
                    messagebox.showinfo("Success", f"Screenshot attached to {ticket_key}")
                    self.update_status(f"Screenshot attached to {ticket_key}")
                else:
                    messagebox.showerror("Error", "Failed to attach screenshot")
                
                # Clean up temp file
                import os
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
            else:
                messagebox.showwarning("Warning", "No image found in clipboard. Copy an image first.")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to paste screenshot: {str(e)}")
    
    def attach_file(self, file_path):
        """Attach a file to the current ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return False
        
        ticket_key = self.current_ticket.get('key')
        
        def do_attach():
            result = self.api_client.add_attachment(ticket_key, file_path)
            
            if result:
                import os
                filename = os.path.basename(file_path)
                messagebox.showinfo("Success", f"File '{filename}' attached to {ticket_key}")
                self.update_status(f"File '{filename}' attached to {ticket_key}")
            else:
                messagebox.showerror("Error", f"Failed to attach file")
        
        # Run in background thread
        threading.Thread(target=do_attach, daemon=True).start()
        return True
    
    def refresh_current_ticket(self):
        """Refresh current ticket data after editing"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_refresh():
            # Get updated ticket data
            updated_ticket = self.api_client.get_ticket_details(ticket_key)
            
            if updated_ticket:
                self.current_ticket = updated_ticket
                self.refresh_callback()
        
        # Run in background thread
        threading.Thread(target=do_refresh, daemon=True).start()