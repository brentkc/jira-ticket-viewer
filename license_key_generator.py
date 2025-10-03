"""
License Key Generator for Jira Ticket Viewer
Use this tool to generate license keys for customers
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from license_manager import LicenseManager
import pyperclip

class LicenseKeyGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Jira Ticket Viewer - License Key Generator")
        self.root.geometry("700x500")
        self.root.configure(bg='#1e1e1e')
        
        self.license_manager = LicenseManager()
        self.setup_ui()
    
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔑 License Key Generator", 
                               font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Customer details
        details_frame = ttk.LabelFrame(main_frame, text="Customer Details", padding="15")
        details_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(details_frame, text="Customer Email:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.email_entry = ttk.Entry(details_frame, width=40)
        self.email_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Label(details_frame, text="License Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.license_type_var = tk.StringVar(value="standard")
        license_combo = ttk.Combobox(details_frame, textvariable=self.license_type_var, 
                                    values=["trial", "standard", "premium"], state="readonly", width=15)
        license_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        ttk.Label(details_frame, text="Valid Days:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.days_var = tk.StringVar(value="365")
        days_entry = ttk.Entry(details_frame, textvariable=self.days_var, width=10)
        days_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        
        # Generate button
        generate_btn = ttk.Button(main_frame, text="🔑 Generate License Key", 
                                 command=self.generate_key)
        generate_btn.pack(pady=(0, 20))
        
        # Generated key display
        key_frame = ttk.LabelFrame(main_frame, text="Generated License Key", padding="15")
        key_frame.pack(fill=tk.BOTH, expand=True)
        
        self.key_text = scrolledtext.ScrolledText(key_frame, height=6, width=70,
                                                 font=('Courier', 10))
        self.key_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Key actions
        key_actions = ttk.Frame(key_frame)
        key_actions.pack(fill=tk.X)
        
        ttk.Button(key_actions, text="📋 Copy Key", command=self.copy_key).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(key_actions, text="✅ Test Key", command=self.test_key).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(key_actions, text="💾 Save to File", command=self.save_key).pack(side=tk.LEFT)
        
        # Machine ID info
        info_frame = ttk.LabelFrame(main_frame, text="Machine Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(20, 0))
        
        current_machine_id = self.license_manager.get_machine_id()
        ttk.Label(info_frame, text=f"Current Machine ID: {current_machine_id}", 
                 font=('Courier', 9)).pack(anchor=tk.W)
        ttk.Label(info_frame, text="Note: License keys are machine-specific", 
                 font=('Segoe UI', 8), foreground='#cccccc').pack(anchor=tk.W)
    
    def generate_key(self):
        email = self.email_entry.get().strip()
        if not email:
            messagebox.showerror("Error", "Please enter customer email")
            return
        
        license_type = self.license_type_var.get()
        try:
            days = int(self.days_var.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid number of days")
            return
        
        # Generate the license key
        try:
            license_key = self.license_manager.generate_license_key(email, license_type, days)
            
            # Display the key
            self.key_text.delete(1.0, tk.END)
            self.key_text.insert(1.0, license_key)
            
            # Show success message with details
            messagebox.showinfo("License Generated", 
                               f"License key generated successfully!\n\n"
                               f"Customer: {email}\n"
                               f"Type: {license_type.title()}\n"
                               f"Valid for: {days} days")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate license: {str(e)}")
    
    def copy_key(self):
        key = self.key_text.get(1.0, tk.END).strip()
        if not key:
            messagebox.showwarning("Warning", "No license key to copy")
            return
        
        try:
            pyperclip.copy(key)
            messagebox.showinfo("Copied", "License key copied to clipboard")
        except:
            # Fallback to tkinter clipboard
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            messagebox.showinfo("Copied", "License key copied to clipboard")
    
    def test_key(self):
        key = self.key_text.get(1.0, tk.END).strip()
        if not key:
            messagebox.showwarning("Warning", "No license key to test")
            return
        
        validation = self.license_manager.validate_license_key(key)
        
        if validation["valid"]:
            data = validation["data"]
            messagebox.showinfo("Valid License", 
                               f"✅ License key is valid!\n\n"
                               f"Email: {data['email']}\n"
                               f"Type: {data['type'].title()}\n"
                               f"Expires: {data['expires'][:10]}\n"
                               f"Days remaining: {validation['days_remaining']}")
        else:
            messagebox.showerror("Invalid License", f"❌ {validation['error']}")
    
    def save_key(self):
        key = self.key_text.get(1.0, tk.END).strip()
        if not key:
            messagebox.showwarning("Warning", "No license key to save")
            return
        
        email = self.email_entry.get().strip()
        license_type = self.license_type_var.get()
        
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialname=f"license_{email}_{license_type}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(f"Jira Ticket Viewer License Key\n")
                    f.write(f"="*40 + "\n\n")
                    f.write(f"Customer Email: {email}\n")
                    f.write(f"License Type: {license_type.title()}\n")
                    f.write(f"Valid Days: {self.days_var.get()}\n")
                    f.write(f"Generated: {self.license_manager.get_machine_id()}\n\n")
                    f.write(f"License Key:\n{key}\n\n")
                    f.write(f"Instructions:\n")
                    f.write(f"1. Run Jira Ticket Viewer\n")
                    f.write(f"2. When prompted for license, copy and paste the key above\n")
                    f.write(f"3. Click 'Activate License'\n")
                
                messagebox.showinfo("Saved", f"License key saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

if __name__ == "__main__":
    # Install pyperclip if not available
    try:
        import pyperclip
    except ImportError:
        print("Installing pyperclip...")
        import subprocess
        subprocess.check_call(["pip", "install", "pyperclip"])
        import pyperclip
    
    root = tk.Tk()
    app = LicenseKeyGenerator(root)
    root.mainloop()