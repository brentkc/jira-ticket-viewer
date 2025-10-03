"""
User management module for handling team members, quick mentions, and user operations
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import logging
from utils import load_quick_mentions, save_quick_mentions, validate_email

# Get logger
logger = logging.getLogger(__name__)


class UserManagementSystem:
    def __init__(self, api_client, status_callback):
        """
        Initialize user management system
        
        Args:
            api_client: JiraAPIClient instance
            status_callback: Function to update status messages
        """
        self.api_client = api_client
        self.update_status = status_callback
        
        # Quick mentions management
        self.quick_mentions = load_quick_mentions()
        self.quick_mentions_frame = None
        self.root_window = None
    
    def set_root_window(self, root):
        """Set reference to root window"""
        self.root_window = root
    
    def set_quick_mentions_frame(self, frame):
        """Set reference to quick mentions frame"""
        self.quick_mentions_frame = frame
    
    def get_team_members(self):
        """Get list of team members from projects for mentions"""
        if not self.root_window:
            return
        
        users_window = tk.Toplevel(self.root_window)
        users_window.title("Select Team Members")
        users_window.geometry("500x600")
        users_window.configure(bg='#1e1e1e')
        users_window.transient(self.root_window)
        users_window.grab_set()
        
        main_frame = ttk.Frame(users_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        ttk.Label(main_frame, text="Load Team Members", 
                 font=('Segoe UI', 12, 'bold')).pack(pady=(0, 10))
        
        # Status label
        status_label = ttk.Label(main_frame, text="Ready to load team members...")
        status_label.pack(pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        load_project_btn = ttk.Button(buttons_frame, text="Load Project Users", 
                                     command=lambda: self.load_project_users(users_window, status_label))
        load_project_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        search_btn = ttk.Button(buttons_frame, text="Search All Users", 
                               command=lambda: self.search_all_users(users_window, status_label))
        search_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Users listbox
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        users_listbox = tk.Listbox(list_frame, 
                                  bg='#2d2d2d', fg='#ffffff',
                                  selectbackground='#0d7377',
                                  yscrollcommand=scrollbar.set)
        users_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=users_listbox.yview)
        
        # Add to quick mentions button
        add_btn = ttk.Button(main_frame, text="Add Selected to Quick Mentions",
                            command=lambda: self.add_selected_users_to_mentions(users_listbox, users_window))
        add_btn.pack(pady=(0, 10))
        
        # Close button
        ttk.Button(main_frame, text="Close", command=users_window.destroy).pack()
        
        # Store references for loading functions
        users_window.users_listbox = users_listbox
        users_window.status_label = status_label
    
    def load_project_users(self, parent_window, status_label=None):
        """Load users who can be assigned to tickets in the project"""
        def do_load():
            logger.info("Starting load_project_users")

            if status_label:
                status_label.config(text="Loading project users...")

            try:
                users = self.api_client.get_project_users()
                logger.info(f"API returned {len(users) if users else 0} users")

                def update_ui():
                    if not hasattr(parent_window, 'users_listbox'):
                        logger.error("Parent window doesn't have users_listbox attribute")
                        return

                    parent_window.users_listbox.delete(0, tk.END)

                    if users:
                        valid_users = 0
                        for user in users:
                            display_name = user.get('displayName', 'Unknown')
                            email = user.get('emailAddress', '')
                            logger.debug(f"Processing user: {display_name} - {email}")

                            if email:
                                parent_window.users_listbox.insert(tk.END, f"{display_name} - {email}")
                                valid_users += 1
                            else:
                                logger.warning(f"User {display_name} has no email address")

                        logger.info(f"Added {valid_users} valid users to listbox")

                        if status_label:
                            status_label.config(text=f"Loaded {len(users)} project users")
                    else:
                        logger.warning("No users returned from API")
                        if status_label:
                            status_label.config(text="Failed to load project users")

                parent_window.after(0, update_ui)

            except Exception as e:
                logger.error(f"Error in load_project_users: {str(e)}", exc_info=True)
                if status_label:
                    status_label.config(text=f"Error loading users: {str(e)}")

        threading.Thread(target=do_load, daemon=True).start()
    
    def search_all_users(self, parent_window, status_label=None):
        """Search for all users in the system"""
        search_window = tk.Toplevel(parent_window)
        search_window.title("Search Users")
        search_window.geometry("300x150")
        search_window.configure(bg='#1e1e1e')
        search_window.transient(parent_window)
        search_window.grab_set()
        
        search_frame = ttk.Frame(search_window, padding="10")
        search_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(search_frame, text="Enter search term:").pack(pady=(0, 5))
        
        search_entry = ttk.Entry(search_frame, width=30)
        search_entry.pack(pady=(0, 10))
        search_entry.focus_set()
        
        def do_search():
            search_query = search_entry.get().strip()
            logger.info(f"User initiated search with query: '{search_query}'")

            if not search_query:
                logger.warning("User tried to search with empty query")
                messagebox.showwarning("Warning", "Please enter a search term")
                return

            search_window.destroy()

            if status_label:
                status_label.config(text=f"Searching for users matching '{search_query}'...")

            def search_users():
                logger.info(f"Starting user search for: '{search_query}'")

                try:
                    users = self.api_client.search_users(search_query)
                    logger.info(f"User search returned {len(users) if users else 0} results")

                    def update_results():
                        if not hasattr(parent_window, 'users_listbox'):
                            logger.error("Parent window doesn't have users_listbox attribute")
                            return

                        parent_window.users_listbox.delete(0, tk.END)

                        if users:
                            valid_users = 0
                            for user in users:
                                display_name = user.get('displayName', 'Unknown')
                                email = user.get('emailAddress', '')
                                logger.debug(f"Processing search result: {display_name} - {email}")

                                if email:
                                    parent_window.users_listbox.insert(tk.END, f"{display_name} - {email}")
                                    valid_users += 1
                                else:
                                    logger.warning(f"Search result {display_name} has no email address")

                            logger.info(f"Added {valid_users} valid users to search results")

                            if status_label:
                                status_label.config(text=f"Found {len(users)} users matching '{search_query}'")
                        else:
                            logger.warning(f"No users found for query: '{search_query}'")
                            if status_label:
                                status_label.config(text=f"No users found matching '{search_query}'")

                    parent_window.after(0, update_results)

                except Exception as e:
                    logger.error(f"Error in search_users: {str(e)}", exc_info=True)
                    if status_label:
                        status_label.config(text=f"Error searching users: {str(e)}")

            threading.Thread(target=search_users, daemon=True).start()
        
        search_btn = ttk.Button(search_frame, text="Search", command=do_search)
        search_btn.pack(pady=(0, 5))
        
        cancel_btn = ttk.Button(search_frame, text="Cancel", command=search_window.destroy)
        cancel_btn.pack()
        
        # Bind Enter key to search
        search_entry.bind('<Return>', lambda e: do_search())
    
    def add_selected_users_to_mentions(self, listbox, window):
        """Add selected users to quick mentions"""
        selection = listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select users to add")
            return
        
        added_count = 0
        for index in selection:
            user_text = listbox.get(index)
            
            # Parse "Name - email" format
            if ' - ' in user_text:
                name, email = user_text.split(' - ', 1)
                
                # Check if already exists
                if (name, email) not in self.quick_mentions:
                    self.quick_mentions.append((name, email))
                    added_count += 1
        
        if added_count > 0:
            self.save_quick_mentions()
            self.refresh_quick_mention_buttons()
            messagebox.showinfo("Success", f"Added {added_count} users to quick mentions")
            window.destroy()
        else:
            messagebox.showinfo("Info", "Selected users are already in quick mentions")
    
    def manage_quick_mentions(self):
        """Open window to manage quick mentions"""
        if not self.root_window:
            return
        
        manage_window = tk.Toplevel(self.root_window)
        manage_window.title("Manage Quick Mentions")
        manage_window.geometry("500x400")
        manage_window.configure(bg='#1e1e1e')
        manage_window.transient(self.root_window)
        manage_window.grab_set()
        
        main_frame = ttk.Frame(manage_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Quick Mention List:", 
                 font=('Segoe UI', 12, 'bold')).pack(pady=(0, 10))
        
        # Listbox to show current quick mentions
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        mentions_listbox = tk.Listbox(list_frame, 
                                     bg='#2d2d2d', fg='#ffffff',
                                     selectbackground='#0d7377',
                                     yscrollcommand=scrollbar.set)
        mentions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=mentions_listbox.yview)
        
        # Populate listbox
        for name, email in self.quick_mentions:
            mentions_listbox.insert(tk.END, f"{name} - {email}")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        def add_mention():
            # Create add dialog
            add_window = tk.Toplevel(manage_window)
            add_window.title("Add Quick Mention")
            add_window.geometry("350x150")
            add_window.configure(bg='#1e1e1e')
            add_window.transient(manage_window)
            add_window.grab_set()
            
            add_frame = ttk.Frame(add_window, padding="10")
            add_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(add_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
            name_entry = ttk.Entry(add_frame, width=30)
            name_entry.grid(row=0, column=1, pady=(0, 5))
            
            ttk.Label(add_frame, text="Email:").grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
            email_entry = ttk.Entry(add_frame, width=30)
            email_entry.grid(row=1, column=1, pady=(0, 10))
            
            def save_mention():
                name = name_entry.get().strip()
                email = email_entry.get().strip()
                
                if not name or not email:
                    messagebox.showerror("Error", "Both name and email are required")
                    return
                
                if not validate_email(email):
                    messagebox.showerror("Error", "Please enter a valid email address")
                    return
                
                if (name, email) in self.quick_mentions:
                    messagebox.showwarning("Warning", "This mention already exists")
                    return
                
                self.quick_mentions.append((name, email))
                mentions_listbox.insert(tk.END, f"{name} - {email}")
                add_window.destroy()
            
            btn_frame = ttk.Frame(add_frame)
            btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
            
            ttk.Button(btn_frame, text="Add", command=save_mention).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(btn_frame, text="Cancel", command=add_window.destroy).pack(side=tk.LEFT)
            
            name_entry.focus_set()
        
        def remove_mention():
            selection = mentions_listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a mention to remove")
                return
            
            index = selection[0]
            if 0 <= index < len(self.quick_mentions):
                name, email = self.quick_mentions[index]
                result = messagebox.askyesno("Confirm", f"Remove {name} ({email}) from quick mentions?")
                if result:
                    del self.quick_mentions[index]
                    mentions_listbox.delete(index)
        
        def load_from_team():
            manage_window.destroy()
            self.get_team_members()
        
        ttk.Button(buttons_frame, text="➕ Add", command=add_mention).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="➖ Remove", command=remove_mention).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(buttons_frame, text="👥 Load from Team", command=load_from_team).pack(side=tk.LEFT, padx=(0, 5))
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        
        def save_and_close():
            self.save_quick_mentions()
            self.refresh_quick_mention_buttons()
            manage_window.destroy()
        
        ttk.Button(bottom_frame, text="Save & Close", command=save_and_close).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bottom_frame, text="Cancel", command=manage_window.destroy).pack(side=tk.LEFT)
    
    def refresh_quick_mention_buttons(self):
        """Refresh the quick mention buttons in the main UI"""
        if not self.quick_mentions_frame:
            return
        
        # Clear existing buttons
        for widget in self.quick_mentions_frame.winfo_children():
            widget.destroy()
        
        # Create buttons for quick mentions
        for i, (name, email) in enumerate(self.quick_mentions):
            btn_frame = ttk.Frame(self.quick_mentions_frame)
            btn_frame.grid(row=i // 3, column=i % 3, padx=(0, 5), pady=(0, 5), sticky=tk.W)
            
            # Mention button
            btn = ttk.Button(btn_frame, text=name[:15] + ("..." if len(name) > 15 else ""),
                           command=lambda e=email: self.add_mention_callback(e))
            btn.pack(side=tk.LEFT)
            
            # Remove button (small)
            remove_btn = ttk.Button(btn_frame, text="✕", width=3,
                                   command=lambda idx=i: self.remove_quick_mention(idx))
            remove_btn.pack(side=tk.LEFT, padx=(2, 0))
    
    def remove_quick_mention(self, index):
        """Remove a quick mention by index"""
        if 0 <= index < len(self.quick_mentions):
            name, email = self.quick_mentions[index]
            result = messagebox.askyesno("Confirm", f"Remove {name} from quick mentions?")
            if result:
                del self.quick_mentions[index]
                self.save_quick_mentions()
                self.refresh_quick_mention_buttons()
    
    def save_quick_mentions(self):
        """Save quick mentions to file"""
        save_quick_mentions(self.quick_mentions)
    
    def load_quick_mentions(self):
        """Load quick mentions from file"""
        self.quick_mentions = load_quick_mentions()
        return self.quick_mentions
    
    def add_mention_callback(self, email):
        """Callback for when a quick mention button is clicked"""
        # This should be set by the parent component
        pass
    
    def set_mention_callback(self, callback):
        """Set the callback for adding mentions"""
        self.add_mention_callback = callback