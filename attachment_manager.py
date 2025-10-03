"""
Attachment management module for handling file attachments and drag-drop functionality
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import requests
from PIL import Image, ImageTk
import io
from config import ATTACHMENT_FILE_TYPES
from utils import format_file_size


class AttachmentManager:
    def __init__(self, api_client, status_callback):
        """
        Initialize attachment manager
        
        Args:
            api_client: JiraAPIClient instance
            status_callback: Function to update status messages
        """
        self.api_client = api_client
        self.update_status = status_callback
        
        # Current ticket reference
        self.current_ticket = None
        self.root_window = None
    
    def set_root_window(self, root):
        """Set reference to root window for drag-drop"""
        self.root_window = root
    
    def set_current_ticket(self, ticket):
        """Set the current ticket for attachment operations"""
        self.current_ticket = ticket
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality for main window"""
        if not self.root_window:
            return
        
        try:
            from tkinterdnd2 import DND_FILES
            self.root_window.drop_target_register(DND_FILES)
            self.root_window.dnd_bind('<<Drop>>', self.on_drop_files)
        except ImportError:
            # If tkinterdnd2 not available, use browse button fallback
            pass
    
    def on_drop_files(self, event):
        """Handle file drop events"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        file_paths = event.data.split()
        for file_path in file_paths:
            # Clean path (remove braces if present)
            file_path = file_path.strip('{}')
            self.attach_file_to_ticket(file_path)
    
    def browse_files_to_attach(self, event=None):
        """Browse for files to attach to current ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        file_paths = filedialog.askopenfilenames(
            title="Select files to attach",
            filetypes=ATTACHMENT_FILE_TYPES
        )
        
        for file_path in file_paths:
            self.attach_file_to_ticket(file_path)
    
    def attach_file_to_ticket(self, file_path):
        """Attach a single file to the current ticket"""
        if not self.current_ticket:
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_attach():
            result = self.api_client.add_attachment(ticket_key, file_path)
            
            if result:
                import os
                filename = os.path.basename(file_path)
                self.update_status(f"File '{filename}' attached to {ticket_key}")
                messagebox.showinfo("Success", f"File '{filename}' attached successfully!")
            else:
                messagebox.showerror("Error", f"Failed to attach file")
        
        # Attach in background thread
        threading.Thread(target=do_attach, daemon=True).start()
    
    def view_attachments(self, view_attachments_btn=None):
        """View attachments for the selected ticket"""
        if not self.current_ticket:
            messagebox.showwarning("Warning", "Please select a ticket first")
            return
        
        ticket_key = self.current_ticket.get('key')
        
        def do_load():
            # Get fresh ticket data to ensure we have latest attachments
            ticket_data = self.api_client.get_ticket_details(ticket_key)
            if not ticket_data:
                messagebox.showerror("Error", "Failed to load ticket data")
                return
            
            fields = ticket_data.get('fields', {})
            attachments = fields.get('attachment', [])
            
            def update_ui():
                if not attachments:
                    messagebox.showinfo("No Attachments", f"Ticket {ticket_key} has no attachments")
                    return
                
                # Update button text with count if provided
                if view_attachments_btn:
                    view_attachments_btn.config(text=f"View Files ({len(attachments)})")
                
                # Filter attachments by type
                image_attachments = []
                other_attachments = []
                
                for attachment in attachments:
                    content_type = attachment.get('mimeType', '').lower()
                    if content_type.startswith('image/'):
                        image_attachments.append(attachment)
                    else:
                        other_attachments.append(attachment)
                
                # Show attachments window
                self.show_attachments_window(image_attachments, other_attachments)
            
            # Update UI in main thread
            if self.root_window:
                self.root_window.after(0, update_ui)
        
        # Load attachments in background thread
        threading.Thread(target=do_load, daemon=True).start()
    
    def show_attachments_window(self, image_attachments, other_attachments):
        """Show attachments in a new window"""
        if not self.root_window:
            return
        
        attach_window = tk.Toplevel(self.root_window)
        attach_window.title(f"Attachments - {self.current_ticket.get('key', 'Unknown')}")
        attach_window.geometry("800x600")
        attach_window.configure(bg='#1e1e1e')
        
        # Create notebook for different attachment types
        notebook = ttk.Notebook(attach_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Images tab
        if image_attachments:
            images_frame = ttk.Frame(notebook)
            notebook.add(images_frame, text=f"Images ({len(image_attachments)})")
            
            # Create scrollable frame for images
            images_canvas = tk.Canvas(images_frame, bg='#2d2d2d')
            images_scrollbar = ttk.Scrollbar(images_frame, orient="vertical", command=images_canvas.yview)
            images_scrollable_frame = ttk.Frame(images_canvas)
            
            images_scrollable_frame.bind(
                "<Configure>",
                lambda e: images_canvas.configure(scrollregion=images_canvas.bbox("all"))
            )
            
            images_canvas.create_window((0, 0), window=images_scrollable_frame, anchor="nw")
            images_canvas.configure(yscrollcommand=images_scrollbar.set)
            
            # Add images
            for i, attachment in enumerate(image_attachments):
                self.add_image_to_frame(images_scrollable_frame, attachment, i)
            
            images_canvas.pack(side="left", fill="both", expand=True)
            images_scrollbar.pack(side="right", fill="y")
        
        # Other files tab
        if other_attachments:
            files_frame = ttk.Frame(notebook)
            notebook.add(files_frame, text=f"Files ({len(other_attachments)})")
            
            # Create treeview for file list
            columns = ("Name", "Size", "Type", "Created")
            files_tree = ttk.Treeview(files_frame, columns=columns, show="headings", height=15)
            
            for col in columns:
                files_tree.heading(col, text=col)
                files_tree.column(col, width=150)
            
            # Add files to tree
            for attachment in other_attachments:
                filename = attachment.get('filename', 'Unknown')
                size = format_file_size(attachment.get('size', 0))
                mime_type = attachment.get('mimeType', 'Unknown')
                created = attachment.get('created', '')[:10] if attachment.get('created') else ''
                
                files_tree.insert('', 'end', values=(filename, size, mime_type, created))
            
            # Add scrollbar
            files_scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=files_tree.yview)
            files_tree.configure(yscrollcommand=files_scrollbar.set)
            
            files_tree.pack(side="left", fill="both", expand=True)
            files_scrollbar.pack(side="right", fill="y")
            
            # Bind double-click to open file
            def on_file_double_click(event):
                selection = files_tree.selection()
                if selection:
                    item = selection[0]
                    filename = files_tree.item(item)['values'][0]
                    
                    # Find the attachment
                    for attachment in other_attachments:
                        if attachment.get('filename') == filename:
                            self.open_attachment_url(attachment.get('content'))
                            break
            
            files_tree.bind("<Double-1>", on_file_double_click)
        
        # If no attachments at all
        if not image_attachments and not other_attachments:
            no_attach_frame = ttk.Frame(notebook)
            notebook.add(no_attach_frame, text="No Attachments")
            
            ttk.Label(no_attach_frame, text="This ticket has no attachments", 
                     font=('Arial', 12)).pack(expand=True)
    
    def add_image_to_frame(self, parent, attachment, index):
        """Add an image attachment to the scrollable frame"""
        image_frame = ttk.LabelFrame(parent, text=attachment.get('filename', 'Unknown Image'))
        image_frame.grid(row=index//2, column=index%2, padx=10, pady=10, sticky="ew")
        
        # Image info
        size_text = format_file_size(attachment.get('size', 0))
        created = attachment.get('created', '')[:10] if attachment.get('created') else ''
        
        info_label = ttk.Label(image_frame, text=f"Size: {size_text} | Created: {created}")
        info_label.pack(pady=5)
        
        # Load and display thumbnail
        content_url = attachment.get('content')
        if content_url:
            self.load_image_thumbnail(image_frame, content_url, attachment.get('filename', 'image'))
        
        # Open button
        open_btn = ttk.Button(image_frame, text="View Full Size", 
                             command=lambda: self.open_attachment_url(content_url))
        open_btn.pack(pady=5)
    
    def load_image_thumbnail(self, parent, url, filename):
        """Load and display image thumbnail"""
        def do_load():
            try:
                # Download image
                response = requests.get(url, auth=(
                    self.api_client.email_callback() if self.api_client.email_callback else "",
                    self.api_client.api_token
                ))
                response.raise_for_status()
                
                # Process image
                image = Image.open(io.BytesIO(response.content))
                
                # Create thumbnail
                image.thumbnail((200, 200), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                
                def update_thumbnail():
                    try:
                        thumb_label = tk.Label(parent, image=photo, bg='#2d2d2d')
                        thumb_label.image = photo  # Keep a reference
                        thumb_label.pack(pady=5)
                        
                        # Bind click to open full size
                        thumb_label.bind("<Button-1>", lambda e: self.open_attachment_url(url))
                        thumb_label.configure(cursor="hand2")
                    except Exception as e:
                        error_label = ttk.Label(parent, text=f"Failed to display image: {str(e)}")
                        error_label.pack(pady=5)
                
                # Update UI in main thread
                parent.after(0, update_thumbnail)
                
            except Exception as e:
                def show_error():
                    error_label = ttk.Label(parent, text=f"Failed to load image: {str(e)}")
                    error_label.pack(pady=5)
                
                parent.after(0, show_error)
        
        # Load image in background thread
        threading.Thread(target=do_load, daemon=True).start()
    
    def open_attachment_url(self, url):
        """Open attachment URL in browser or default application"""
        if url:
            import webbrowser
            webbrowser.open(url)