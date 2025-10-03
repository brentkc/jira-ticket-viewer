"""
Reminder Management System for Jira Ticket Viewer
Handles recurring reminders with flashing alerts for critical tasks
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, timedelta
import threading
import time

class ReminderManager:
    def __init__(self, parent_app=None):
        self.parent_app = parent_app
        self.reminders_file = os.path.expanduser("~/.jira_ticket_viewer/reminders.json")
        self.reminders = []
        self.alarm_active = False
        self.alarm_thread = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.reminders_file), exist_ok=True)
        
        self.load_reminders()
        self.start_reminder_checker()
    
    def load_reminders(self):
        """Load reminders from file"""
        try:
            if os.path.exists(self.reminders_file):
                with open(self.reminders_file, 'r') as f:
                    self.reminders = json.load(f)
                print(f"[DEBUG] Loaded {len(self.reminders)} reminders")
            else:
                self.reminders = []
        except Exception as e:
            print(f"[DEBUG] Error loading reminders: {e}")
            self.reminders = []
    
    def save_reminders(self):
        """Save reminders to file"""
        try:
            with open(self.reminders_file, 'w') as f:
                json.dump(self.reminders, f, indent=2)
            print(f"[DEBUG] Saved {len(self.reminders)} reminders")
        except Exception as e:
            print(f"[DEBUG] Error saving reminders: {e}")
    
    def add_reminder(self, title, description, due_date, reminder_type="general", priority="medium"):
        """Add a new reminder"""
        reminder = {
            "id": len(self.reminders) + 1,
            "title": title,
            "description": description,
            "due_date": due_date.isoformat() if isinstance(due_date, datetime) else due_date,
            "type": reminder_type,  # onboarding, offboarding, general, etc.
            "priority": priority,   # low, medium, high, critical
            "created": datetime.now().isoformat(),
            "completed": False,
            "snoozed_until": None
        }
        
        self.reminders.append(reminder)
        self.save_reminders()
        print(f"[DEBUG] Added reminder: {title}")
        return reminder
    
    def complete_reminder(self, reminder_id):
        """Mark reminder as completed"""
        for reminder in self.reminders:
            if reminder["id"] == reminder_id:
                reminder["completed"] = True
                reminder["completed_date"] = datetime.now().isoformat()
                self.save_reminders()
                print(f"[DEBUG] Completed reminder: {reminder['title']}")
                return True
        return False
    
    def snooze_reminder(self, reminder_id, hours=1):
        """Snooze reminder for specified hours"""
        for reminder in self.reminders:
            if reminder["id"] == reminder_id:
                snooze_until = datetime.now() + timedelta(hours=hours)
                reminder["snoozed_until"] = snooze_until.isoformat()
                self.save_reminders()
                print(f"[DEBUG] Snoozed reminder: {reminder['title']} for {hours} hours")
                return True
        return False
    
    def get_due_reminders(self):
        """Get all reminders that are due now"""
        now = datetime.now()
        due_reminders = []
        
        for reminder in self.reminders:
            if reminder["completed"]:
                continue
                
            # Check if snoozed
            if reminder.get("snoozed_until"):
                snooze_time = datetime.fromisoformat(reminder["snoozed_until"])
                if now < snooze_time:
                    continue
            
            # Check if due
            due_date = datetime.fromisoformat(reminder["due_date"])
            if now >= due_date:
                due_reminders.append(reminder)
        
        return due_reminders
    
    def start_reminder_checker(self):
        """Start background thread to check for due reminders"""
        def check_reminders():
            while True:
                try:
                    # TEMPORARILY DISABLED - alerts were triggering too frequently
                    # due_reminders = self.get_due_reminders()
                    # if due_reminders and not self.alarm_active:
                    #     self.trigger_alarm(due_reminders)
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    print(f"[DEBUG] Error in reminder checker: {e}")
                    time.sleep(60)
        
        self.checker_thread = threading.Thread(target=check_reminders, daemon=True)
        self.checker_thread.start()
    
    def trigger_alarm(self, due_reminders):
        """Trigger flashing alarm for due reminders"""
        if self.alarm_active:
            return
            
        self.alarm_active = True
        
        def flash_alarm():
            # Create alarm window
            alarm_window = tk.Toplevel()
            alarm_window.title("🚨 URGENT REMINDERS 🚨")
            alarm_window.geometry("600x400")
            alarm_window.configure(bg='#ff4444')
            alarm_window.attributes('-topmost', True)
            alarm_window.resizable(False, False)
            
            # Center the window
            alarm_window.update_idletasks()
            x = (alarm_window.winfo_screenwidth() // 2) - (600 // 2)
            y = (alarm_window.winfo_screenheight() // 2) - (400 // 2)
            alarm_window.geometry(f"600x400+{x}+{y}")
            
            # Single steady red color - no more color cycling!
            alert_color = '#ff4444'  # One consistent red color
            
            # Main frame
            main_frame = tk.Frame(alarm_window, bg='#ff4444', padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = tk.Label(main_frame, text="🚨 URGENT REMINDERS 🚨", 
                                 font=('Arial', 20, 'bold'), fg='white', bg='#ff4444')
            title_label.pack(pady=(0, 20))
            
            # Reminders list
            reminders_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
            reminders_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Scrollable text for reminders
            reminder_text = tk.Text(reminders_frame, wrap=tk.WORD, font=('Arial', 12),
                                   height=10, width=60)
            scrollbar = tk.Scrollbar(reminders_frame, orient=tk.VERTICAL, command=reminder_text.yview)
            reminder_text.configure(yscrollcommand=scrollbar.set)
            
            reminder_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
            
            # Populate reminders
            for i, reminder in enumerate(due_reminders, 1):
                priority_icon = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
                type_icon = {"onboarding": "👋", "offboarding": "👋", "general": "📋"}
                
                reminder_text.insert(tk.END, f"{i}. {priority_icon.get(reminder['priority'], '📋')} ")
                reminder_text.insert(tk.END, f"{type_icon.get(reminder['type'], '📋')} ")
                reminder_text.insert(tk.END, f"{reminder['title']}\n")
                reminder_text.insert(tk.END, f"   Due: {reminder['due_date'][:16]}\n")
                reminder_text.insert(tk.END, f"   {reminder['description']}\n\n")
            
            reminder_text.config(state=tk.DISABLED)
            
            # Buttons frame
            button_frame = tk.Frame(main_frame, bg='#ff4444')
            button_frame.pack(fill=tk.X)
            
            def snooze_all():
                for reminder in due_reminders:
                    self.snooze_reminder(reminder["id"], 1)
                self.alarm_active = False
                alarm_window.destroy()
            
            def view_all():
                self.alarm_active = False
                alarm_window.destroy()
                self.show_reminder_manager()
            
            def dismiss():
                self.alarm_active = False
                alarm_window.destroy()
            
            tk.Button(button_frame, text="Snooze All (1 hour)", command=snooze_all,
                     font=('Arial', 12, 'bold'), bg='yellow', fg='black').pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="View All Reminders", command=view_all,
                     font=('Arial', 12, 'bold'), bg='blue', fg='white').pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Dismiss", command=dismiss,
                     font=('Arial', 12, 'bold'), bg='gray', fg='white').pack(side=tk.RIGHT, padx=5)
            
            # Handle window close
            def on_closing():
                self.alarm_active = False
                alarm_window.destroy()
            
            alarm_window.protocol("WM_DELETE_WINDOW", on_closing)
            
            # NO FLASHING OR PULSING - Just solid color
            
            # Play system beep
            try:
                import winsound
                winsound.Beep(1000, 500)  # 1000 Hz for 500ms
            except:
                alarm_window.bell()  # Fallback to system bell
        
        # Run alarm in main thread
        if self.parent_app and hasattr(self.parent_app, 'root'):
            self.parent_app.root.after(0, flash_alarm)
        else:
            # Standalone mode
            threading.Thread(target=flash_alarm, daemon=True).start()
    
    def show_reminder_manager(self):
        """Show the main reminder management window"""
        manager_window = tk.Toplevel()
        manager_window.title("Reminder Manager")
        manager_window.geometry("800x600")
        manager_window.configure(bg='#2b2b2b')
        
        # Main frame
        main_frame = ttk.Frame(manager_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="📅 Reminder Manager", 
                               font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Add reminder button
        add_frame = ttk.Frame(main_frame)
        add_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(add_frame, text="➕ Add New Reminder", 
                  command=self.show_add_reminder_dialog).pack(side=tk.LEFT)
        ttk.Button(add_frame, text="🔄 Refresh", 
                  command=lambda: self.refresh_reminder_list(reminder_tree)).pack(side=tk.LEFT, padx=(10, 0))
        
        # Reminders list
        columns = ("ID", "Title", "Type", "Priority", "Due Date", "Status")
        reminder_tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        reminder_tree.heading("ID", text="ID")
        reminder_tree.heading("Title", text="Title")
        reminder_tree.heading("Type", text="Type")
        reminder_tree.heading("Priority", text="Priority")
        reminder_tree.heading("Due Date", text="Due Date")
        reminder_tree.heading("Status", text="Status")
        
        reminder_tree.column("ID", width=50)
        reminder_tree.column("Title", width=200)
        reminder_tree.column("Type", width=100)
        reminder_tree.column("Priority", width=80)
        reminder_tree.column("Due Date", width=150)
        reminder_tree.column("Status", width=100)
        
        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=reminder_tree.yview)
        reminder_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        reminder_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(20, 0))
        
        def complete_selected():
            selected = reminder_tree.selection()
            if selected:
                item = reminder_tree.item(selected[0])
                reminder_id = int(item['values'][0])
                self.complete_reminder(reminder_id)
                self.refresh_reminder_list(reminder_tree)
        
        def snooze_selected():
            selected = reminder_tree.selection()
            if selected:
                item = reminder_tree.item(selected[0])
                reminder_id = int(item['values'][0])
                self.snooze_reminder(reminder_id, 1)
                self.refresh_reminder_list(reminder_tree)
        
        ttk.Button(action_frame, text="✅ Complete", command=complete_selected).pack(side=tk.LEFT)
        ttk.Button(action_frame, text="😴 Snooze 1h", command=snooze_selected).pack(side=tk.LEFT, padx=(10, 0))
        
        # Load initial data
        self.refresh_reminder_list(reminder_tree)
    
    def refresh_reminder_list(self, tree):
        """Refresh the reminder list in the treeview"""
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
        
        # Reload reminders
        self.load_reminders()
        
        # Add reminders to tree
        for reminder in self.reminders:
            status = "✅ Completed" if reminder["completed"] else "⏰ Pending"
            if reminder.get("snoozed_until") and not reminder["completed"]:
                status = "😴 Snoozed"
            
            due_date = reminder["due_date"][:16] if reminder["due_date"] else "No date"
            
            tree.insert("", tk.END, values=(
                reminder["id"],
                reminder["title"],
                reminder["type"].title(),
                reminder["priority"].title(),
                due_date,
                status
            ))
    
    def show_add_reminder_dialog(self):
        """Show dialog to add new reminder"""
        dialog = tk.Toplevel()
        dialog.title("Add New Reminder")
        dialog.geometry("500x600")
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (250)
        y = (dialog.winfo_screenheight() // 2) - (300)
        dialog.geometry(f"500x600+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        ttk.Label(main_frame, text="Add New Reminder", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        
        # Form fields
        ttk.Label(main_frame, text="Title:").pack(anchor=tk.W)
        title_entry = ttk.Entry(main_frame, width=50, font=('Segoe UI', 10))
        title_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(main_frame, text="Description:").pack(anchor=tk.W)
        desc_text = tk.Text(main_frame, height=6, width=50, font=('Segoe UI', 10))
        desc_text.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(main_frame, text="Type:").pack(anchor=tk.W)
        type_var = tk.StringVar(value="general")
        type_combo = ttk.Combobox(main_frame, textvariable=type_var, 
                                 values=["general", "onboarding", "offboarding", "maintenance", "security"])
        type_combo.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(main_frame, text="Priority:").pack(anchor=tk.W)
        priority_var = tk.StringVar(value="medium")
        priority_combo = ttk.Combobox(main_frame, textvariable=priority_var,
                                     values=["low", "medium", "high", "critical"])
        priority_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Date/time selection
        ttk.Label(main_frame, text="Due Date & Time:").pack(anchor=tk.W)
        date_frame = ttk.Frame(main_frame)
        date_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Simple date/time entry
        ttk.Label(date_frame, text="YYYY-MM-DD HH:MM").pack(side=tk.LEFT)
        datetime_entry = ttk.Entry(date_frame, width=20)
        datetime_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Set default to tomorrow at 9 AM
        tomorrow = datetime.now() + timedelta(days=1)
        default_datetime = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
        datetime_entry.insert(0, default_datetime.strftime("%Y-%m-%d %H:%M"))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_reminder():
            title = title_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()
            reminder_type = type_var.get()
            priority = priority_var.get()
            
            if not title:
                messagebox.showwarning("Missing Title", "Please enter a title for the reminder")
                return
            
            try:
                due_datetime = datetime.strptime(datetime_entry.get(), "%Y-%m-%d %H:%M")
            except ValueError:
                messagebox.showerror("Invalid Date", "Please enter date in format: YYYY-MM-DD HH:MM")
                return
            
            self.add_reminder(title, description, due_datetime, reminder_type, priority)
            messagebox.showinfo("Success", "Reminder added successfully!")
            dialog.destroy()
        
        ttk.Button(button_frame, text="Save Reminder", command=save_reminder).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=(10, 0))


# Standalone mode for testing
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window
    
    rm = ReminderManager()
    
    # Add some test reminders
    rm.add_reminder(
        "Test Onboarding Reminder",
        "Set up new user accounts and access permissions",
        datetime.now() + timedelta(minutes=1),
        "onboarding",
        "high"
    )
    
    rm.show_reminder_manager()
    root.mainloop()