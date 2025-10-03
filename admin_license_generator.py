"""
ADMIN ONLY - License Key Generator for Jira Ticket Viewer
This tool generates license keys for customers
DO NOT DISTRIBUTE THIS FILE TO CUSTOMERS
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from license_manager import LicenseManager
import pyperclip
from datetime import datetime

class AdminLicenseGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("🔐 ADMIN - Jira Ticket Viewer License Generator")
        self.root.geometry("800x700")
        self.root.configure(bg='#1e1e1e')

        # Make window prominent
        self.root.attributes('-topmost', True)
        self.root.after(100, lambda: self.root.attributes('-topmost', False))

        self.license_manager = LicenseManager()
        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Warning banner
        warning_frame = tk.Frame(main_frame, bg='#8B0000', relief=tk.RAISED, borderwidth=2)
        warning_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(warning_frame, text="⚠️ ADMINISTRATOR ONLY - DO NOT DISTRIBUTE THIS APPLICATION ⚠️",
                font=('Segoe UI', 12, 'bold'), fg='white', bg='#8B0000', pady=10).pack()

        # Title
        title_label = ttk.Label(main_frame, text="🔑 License Key Generator",
                               font=('Segoe UI', 16, 'bold'))
        title_label.pack(pady=(0, 20))

        # Customer details
        details_frame = ttk.LabelFrame(main_frame, text="Customer Details", padding="15")
        details_frame.pack(fill=tk.X, pady=(0, 20))

        # Customer Name
        ttk.Label(details_frame, text="Customer Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(details_frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Customer Email
        ttk.Label(details_frame, text="Customer Email:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.email_entry = ttk.Entry(details_frame, width=40)
        self.email_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Company
        ttk.Label(details_frame, text="Company:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.company_entry = ttk.Entry(details_frame, width=40)
        self.company_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # License configuration
        config_frame = ttk.LabelFrame(main_frame, text="License Configuration", padding="15")
        config_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(config_frame, text="License Type:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.license_type_var = tk.StringVar(value="standard")
        license_combo = ttk.Combobox(config_frame, textvariable=self.license_type_var,
                                    values=["trial", "standard", "premium"], state="readonly", width=15)
        license_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)
        license_combo.bind('<<ComboboxSelected>>', self.update_license_info)

        ttk.Label(config_frame, text="Valid Days:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.days_var = tk.StringVar(value="365")
        days_entry = ttk.Entry(config_frame, textvariable=self.days_var, width=10)
        days_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # License features display
        self.features_label = ttk.Label(config_frame, text="", font=('Segoe UI', 9), foreground='#00d4aa')
        self.features_label.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        self.update_license_info()

        # Generate button
        generate_btn = ttk.Button(main_frame, text="🔑 Generate License Key",
                                 command=self.generate_key)
        generate_btn.pack(pady=(0, 20))

        # Generated key display
        key_frame = ttk.LabelFrame(main_frame, text="Generated License Key", padding="15")
        key_frame.pack(fill=tk.BOTH, expand=True)

        self.key_text = scrolledtext.ScrolledText(key_frame, height=6, width=70,
                                                 font=('Courier', 10), wrap=tk.WORD)
        self.key_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Key actions
        key_actions = ttk.Frame(key_frame)
        key_actions.pack(fill=tk.X)

        ttk.Button(key_actions, text="📋 Copy Key", command=self.copy_key).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(key_actions, text="✅ Test Key", command=self.test_key).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(key_actions, text="💾 Save to File", command=self.save_key).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(key_actions, text="📧 Email Customer", command=self.email_customer).pack(side=tk.LEFT)

        # Machine ID info
        info_frame = ttk.LabelFrame(main_frame, text="Machine Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(20, 0))

        current_machine_id = self.license_manager.get_machine_id()
        ttk.Label(info_frame, text=f"Current Machine ID: {current_machine_id}",
                 font=('Courier', 9)).pack(anchor=tk.W)
        ttk.Label(info_frame, text="Note: Machine-locking is currently DISABLED for floating licenses",
                 font=('Segoe UI', 8), foreground='#cccccc').pack(anchor=tk.W)

    def update_license_info(self, event=None):
        """Update license features display"""
        license_type = self.license_type_var.get()
        features = self.license_manager.get_license_features(license_type)

        feature_text = f"✓ {license_type.title()} License Features:\n"
        feature_text += f"  • Max Users: {'Unlimited' if features['max_users'] == -1 else features['max_users']}\n"
        feature_text += f"  • Priority Support: {'Yes' if features['priority_support'] else 'No'}"

        self.features_label.config(text=feature_text)

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

            # Calculate expiry date
            from datetime import timedelta
            expiry_date = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')

            # Show success message with details
            messagebox.showinfo("License Generated Successfully",
                               f"License key generated!\n\n"
                               f"Customer: {email}\n"
                               f"Type: {license_type.title()}\n"
                               f"Valid for: {days} days\n"
                               f"Expires: {expiry_date}")

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
                               f"✅ License key is VALID!\n\n"
                               f"Email: {data['email']}\n"
                               f"Type: {data['type'].title()}\n"
                               f"Expires: {data['expires'][:10]}\n"
                               f"Days remaining: {validation['days_remaining']}\n"
                               f"Machine ID: {data.get('machine_id', 'N/A')}")
        else:
            messagebox.showerror("Invalid License", f"❌ {validation['error']}")

    def save_key(self):
        key = self.key_text.get(1.0, tk.END).strip()
        if not key:
            messagebox.showwarning("Warning", "No license key to save")
            return

        name = self.name_entry.get().strip() or "Customer"
        email = self.email_entry.get().strip()
        company = self.company_entry.get().strip()
        license_type = self.license_type_var.get()

        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialname=f"license_{email.replace('@', '_')}_{license_type}.txt"
        )

        if filename:
            try:
                from datetime import timedelta
                expiry_date = (datetime.now() + timedelta(days=int(self.days_var.get()))).strftime('%Y-%m-%d')

                with open(filename, 'w') as f:
                    f.write(f"═══════════════════════════════════════════════════════\n")
                    f.write(f"    JIRA TICKET VIEWER - LICENSE KEY\n")
                    f.write(f"═══════════════════════════════════════════════════════\n\n")
                    f.write(f"Customer Name:    {name}\n")
                    f.write(f"Customer Email:   {email}\n")
                    if company:
                        f.write(f"Company:          {company}\n")
                    f.write(f"License Type:     {license_type.title()}\n")
                    f.write(f"Valid Until:      {expiry_date}\n")
                    f.write(f"Generated:        {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                    f.write(f"\n───────────────────────────────────────────────────────\n")
                    f.write(f"LICENSE KEY:\n")
                    f.write(f"───────────────────────────────────────────────────────\n\n")
                    f.write(f"{key}\n\n")
                    f.write(f"───────────────────────────────────────────────────────\n")
                    f.write(f"INSTALLATION INSTRUCTIONS:\n")
                    f.write(f"───────────────────────────────────────────────────────\n\n")
                    f.write(f"1. Launch Jira Ticket Viewer application\n")
                    f.write(f"2. When prompted for license activation, copy the\n")
                    f.write(f"   license key above (entire text block)\n")
                    f.write(f"3. Paste the key into the license activation dialog\n")
                    f.write(f"4. Click 'Activate License'\n\n")
                    f.write(f"Support: contact your license administrator\n")
                    f.write(f"═══════════════════════════════════════════════════════\n")

                messagebox.showinfo("Saved", f"License key saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def email_customer(self):
        """Open email client with pre-filled license information"""
        key = self.key_text.get(1.0, tk.END).strip()
        if not key:
            messagebox.showwarning("Warning", "No license key to email")
            return

        email = self.email_entry.get().strip()
        name = self.name_entry.get().strip() or "Valued Customer"
        license_type = self.license_type_var.get()

        from datetime import timedelta
        import urllib.parse

        expiry_date = (datetime.now() + timedelta(days=int(self.days_var.get()))).strftime('%Y-%m-%d')

        subject = "Your Jira Ticket Viewer License Key"
        body = f"""Dear {name},

Thank you for your purchase of Jira Ticket Viewer!

Your {license_type.title()} License details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
License Type: {license_type.title()}
Valid Until: {expiry_date}

LICENSE KEY:
{key}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTALLATION INSTRUCTIONS:

1. Download and launch Jira Ticket Viewer
2. Copy your license key above (entire text)
3. When prompted, paste the license key
4. Click 'Activate License'

Your license will be activated immediately!

If you have any questions or need assistance, please don't hesitate to contact us.

Best regards,
Jira Ticket Viewer Support Team
"""

        mailto_link = f"mailto:{email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"

        try:
            import webbrowser
            webbrowser.open(mailto_link)
        except Exception as e:
            messagebox.showerror("Error", f"Could not open email client: {str(e)}\n\nPlease copy the license key manually.")

if __name__ == "__main__":
    # Check for required dependencies
    try:
        import pyperclip
    except ImportError:
        print("Installing pyperclip...")
        import subprocess
        subprocess.check_call(["pip", "install", "pyperclip"])
        import pyperclip

    root = tk.Tk()
    app = AdminLicenseGenerator(root)
    root.mainloop()
