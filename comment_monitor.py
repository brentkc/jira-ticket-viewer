"""
Comment Monitor
Tracks new comments on tickets and alerts the user
"""

import threading
import time
from datetime import datetime
from tkinter import messagebox
import tkinter as tk


class CommentMonitor:
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.monitoring = False
        self.monitor_thread = None
        self.known_comments = {}  # ticket_key -> list of comment IDs
        self.check_interval = 60  # Check every 60 seconds
        self.new_comments = []  # List of new comments to display

    def start_monitoring(self):
        """Start monitoring for new comments"""
        if self.monitoring:
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print("[MONITOR] Comment monitoring started")

    def stop_monitoring(self):
        """Stop monitoring for new comments"""
        self.monitoring = False
        print("[MONITOR] Comment monitoring stopped")

    def _monitor_loop(self):
        """Background monitoring loop"""
        # Initial scan to establish baseline
        self._scan_current_tickets()

        while self.monitoring:
            time.sleep(self.check_interval)
            if self.monitoring:
                self._check_for_new_comments()

    def _scan_current_tickets(self):
        """Scan current tickets to establish baseline comment count"""
        if not hasattr(self.parent_app, 'all_tickets'):
            return

        for ticket in self.parent_app.all_tickets:
            ticket_key = ticket.get('key')
            if ticket_key:
                comments = self._get_ticket_comments(ticket_key)
                if comments:
                    self.known_comments[ticket_key] = [c['id'] for c in comments]

    def _get_ticket_comments(self, ticket_key):
        """Get comments for a specific ticket"""
        try:
            comments_data = self.parent_app.make_jira_request(f"issue/{ticket_key}/comment")
            if comments_data and 'comments' in comments_data:
                return comments_data['comments']
        except Exception as e:
            print(f"[MONITOR] Error fetching comments for {ticket_key}: {e}")
        return []

    def _check_for_new_comments(self):
        """Check all tickets for new comments"""
        if not hasattr(self.parent_app, 'all_tickets'):
            return

        new_comments_found = []

        for ticket in self.parent_app.all_tickets:
            ticket_key = ticket.get('key')
            if not ticket_key:
                continue

            comments = self._get_ticket_comments(ticket_key)
            if not comments:
                continue

            current_comment_ids = [c['id'] for c in comments]

            # Check if this ticket has new comments
            if ticket_key in self.known_comments:
                known_ids = set(self.known_comments[ticket_key])
                new_ids = [cid for cid in current_comment_ids if cid not in known_ids]

                if new_ids:
                    # Found new comments
                    for comment in comments:
                        if comment['id'] in new_ids:
                            new_comments_found.append({
                                'ticket_key': ticket_key,
                                'ticket_summary': ticket.get('fields', {}).get('summary', ''),
                                'comment': comment
                            })

            # Update known comments
            self.known_comments[ticket_key] = current_comment_ids

        # If new comments found, notify the user
        if new_comments_found:
            self.new_comments.extend(new_comments_found)
            self.parent_app.root.after(0, self._show_notification)

    def _show_notification(self):
        """Show notification dialog for new comments"""
        if not self.new_comments:
            return

        count = len(self.new_comments)

        # Create notification window
        notify_window = tk.Toplevel(self.parent_app.root)
        notify_window.title(f"New Comments ({count})")
        notify_window.geometry("400x300")
        notify_window.configure(bg='#1e1e1e')

        # Make it appear on top
        notify_window.attributes('-topmost', True)

        # Center on screen
        notify_window.update_idletasks()
        x = (notify_window.winfo_screenwidth() // 2) - 200
        y = (notify_window.winfo_screenheight() // 2) - 150
        notify_window.geometry(f"400x300+{x}+{y}")

        # Title
        title_label = tk.Label(notify_window, text=f"🔔 {count} New Comment{'s' if count > 1 else ''}",
                              font=('Segoe UI', 14, 'bold'),
                              bg='#1e1e1e', fg='#ffffff')
        title_label.pack(pady=20)

        # Listbox to show comments
        import tkinter.ttk as ttk
        list_frame = ttk.Frame(notify_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        comment_list = tk.Listbox(list_frame, bg='#2d2d2d', fg='#ffffff',
                                  selectbackground='#0078d4',
                                  font=('Segoe UI', 10),
                                  yscrollcommand=scrollbar.set)
        comment_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=comment_list.yview)

        for nc in self.new_comments:
            author = nc['comment'].get('author', {}).get('displayName', 'Unknown')
            ticket_key = nc['ticket_key']
            comment_list.insert(tk.END, f"{ticket_key} - New comment from {author}")

        # Buttons
        button_frame = ttk.Frame(notify_window)
        button_frame.pack(pady=(0, 20))

        def view_selected():
            selection = comment_list.curselection()
            if selection:
                idx = selection[0]
                comment_info = self.new_comments[idx]
                self._view_comment_detail(comment_info)
                notify_window.destroy()

        def dismiss_all():
            self.new_comments.clear()
            notify_window.destroy()

        ttk.Button(button_frame, text="View Selected", command=view_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Dismiss All", command=dismiss_all).pack(side=tk.LEFT, padx=5)

        # Double-click to view
        comment_list.bind('<Double-Button-1>', lambda e: view_selected())

    def _view_comment_detail(self, comment_info):
        """Show detail dialog for a specific comment"""
        ticket_key = comment_info['ticket_key']
        comment = comment_info['comment']

        # Find and select the ticket in the main app
        if hasattr(self.parent_app, 'tree'):
            for item in self.parent_app.tree.get_children():
                if self.parent_app.tree.item(item)['values'][0] == ticket_key:
                    self.parent_app.tree.selection_set(item)
                    self.parent_app.tree.see(item)
                    # Trigger selection event
                    self.parent_app.on_ticket_select(None)
                    break

        # Remove this comment from the new comments list
        if comment_info in self.new_comments:
            self.new_comments.remove(comment_info)