"""
AI Setup Dialog for configuring OpenAI/Copilot integration
"""

import tkinter as tk
from tkinter import ttk, messagebox
from ai_config import set_openai_api_key, get_openai_api_key

class AISetupDialog:
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.create_dialog()

    def create_dialog(self):
        """Create the AI setup dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("🤖 AI Setup - Connect Your Copilot License")
        self.dialog.geometry("600x400")
        self.dialog.configure(bg='#1e1e1e')

        # Make it modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 300
        y = (self.dialog.winfo_screenheight() // 2) - 200
        self.dialog.geometry(f"600x400+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(main_frame, text="🤖 Real AI Integration Setup",
                 font=('Segoe UI', 16, 'bold')).pack(pady=(0, 10))

        ttk.Label(main_frame, text="Connect your Copilot license for emotional intelligence analysis",
                 font=('Segoe UI', 10)).pack(pady=(0, 20))

        # Instructions
        instructions = """
🔐 How to get your API key:

Option 1: Use your Copilot License
• Visit: https://platform.openai.com/api-keys
• Sign in with your Microsoft/GitHub account linked to Copilot
• Create a new API key for this application

Option 2: Direct OpenAI Account
• Visit: https://platform.openai.com/api-keys
• Sign up/in and create an API key
• Note: This may have usage costs

✅ Benefits of Real AI:
• Emotional intelligence assessment
• Context-aware responses
• Professional tone matching
• Advanced pattern recognition
• Personalized triage responses
"""

        text_frame = ttk.LabelFrame(main_frame, text="Setup Instructions", padding="10")
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        instructions_text = tk.Text(text_frame, height=12, width=60,
                                   bg='#2d2d2d', fg='#ffffff',
                                   font=('Segoe UI', 9), wrap=tk.WORD)
        instructions_text.pack(fill=tk.BOTH, expand=True)
        instructions_text.insert(tk.END, instructions)
        instructions_text.config(state=tk.DISABLED)

        # API Key input
        key_frame = ttk.LabelFrame(main_frame, text="API Key Configuration", padding="10")
        key_frame.pack(fill=tk.X, pady=(0, 20))

        ttk.Label(key_frame, text="OpenAI API Key:").pack(anchor='w')

        self.api_key_var = tk.StringVar()
        # Try to load existing key
        existing_key = get_openai_api_key()
        if existing_key:
            self.api_key_var.set("*" * 20 + existing_key[-8:])  # Show only last 8 chars

        self.key_entry = ttk.Entry(key_frame, textvariable=self.api_key_var,
                                  width=60, show="*")
        self.key_entry.pack(fill=tk.X, pady=(5, 10))

        # Show/Hide key button
        self.show_key_var = tk.BooleanVar()
        show_btn = ttk.Checkbutton(key_frame, text="Show API Key",
                                  variable=self.show_key_var,
                                  command=self.toggle_key_visibility)
        show_btn.pack(anchor='w')

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Test Connection",
                  command=self.test_connection).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Save & Close",
                  command=self.save_and_close).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Skip (Use Basic Mode)",
                  command=self.skip_setup).pack(side=tk.RIGHT)

        # Status label
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.pack(pady=(10, 0))

        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def toggle_key_visibility(self):
        """Toggle API key visibility"""
        if self.show_key_var.get():
            self.key_entry.config(show="")
        else:
            self.key_entry.config(show="*")

    def test_connection(self):
        """Test the AI connection"""
        api_key = self.api_key_var.get().strip()

        if not api_key or api_key.startswith("*"):
            self.status_label.config(text="❌ Please enter a valid API key")
            return

        self.status_label.config(text="🔄 Testing connection...")
        self.dialog.update()

        try:
            import openai
            client = openai.OpenAI(api_key=api_key)

            # Test with a simple request
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=10
            )

            self.status_label.config(text="✅ Connection successful! AI is ready.")

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "authentication" in error_msg.lower():
                self.status_label.config(text="❌ Invalid API key")
            elif "quota" in error_msg.lower():
                self.status_label.config(text="❌ API quota exceeded")
            else:
                self.status_label.config(text=f"❌ Connection failed: {error_msg[:50]}")

    def save_and_close(self):
        """Save the API key and close"""
        api_key = self.api_key_var.get().strip()

        if not api_key or api_key.startswith("*"):
            # If key starts with *, user didn't change it, so don't save
            existing_key = get_openai_api_key()
            if existing_key:
                messagebox.showinfo("AI Setup", "Existing API key will be used.")
                self.close_dialog()
                return
            else:
                messagebox.showwarning("Missing API Key", "Please enter an API key or skip to use basic mode.")
                return

        # Save the new key
        if set_openai_api_key(api_key):
            messagebox.showinfo("AI Setup Complete",
                              "✅ API key saved securely!\n\n" +
                              "🤖 Real AI with emotional intelligence is now active.\n" +
                              "Try the AI Summary button on any ticket!")
            self.close_dialog()
        else:
            messagebox.showerror("Save Error", "Failed to save API key securely.")

    def skip_setup(self):
        """Skip AI setup and use basic mode"""
        result = messagebox.askyesno("Skip AI Setup",
                                   "Skip AI setup and use basic rule-based analysis?\n\n" +
                                   "You can always set this up later from the settings.")
        if result:
            self.close_dialog()

    def close_dialog(self):
        """Close the dialog"""
        self.dialog.destroy()


def show_ai_setup(parent):
    """Show the AI setup dialog"""
    AISetupDialog(parent)