"""
AI Settings Configuration Dialog
Allows users to configure their AI preferences
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from ai_settings import AISettings
from ai_config import get_openai_api_key, set_openai_api_key
import openai
import os


class AISettingsDialog:
    def __init__(self, parent):
        self.parent = parent
        self.settings = AISettings()
        self.dialog = None
        self.create_dialog()

    def create_dialog(self):
        """Create the settings dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("AI Assistant Settings")
        self.dialog.geometry("800x800")
        self.dialog.configure(bg='#1e1e1e')

        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - 400
        y = (self.dialog.winfo_screenheight() // 2) - 400
        self.dialog.geometry(f"800x800+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        ttk.Label(main_frame, text="AI Assistant Settings",
                 font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))

        # API Configuration Section
        api_frame = ttk.LabelFrame(main_frame, text="OpenAI API Configuration", padding="15")
        api_frame.pack(fill=tk.X, pady=(0, 15))

        # API Key
        ttk.Label(api_frame, text="OpenAI API Key:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.api_key_entry = ttk.Entry(api_frame, width=40, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=10)

        # Load existing API key
        existing_key = get_openai_api_key()
        if existing_key:
            self.api_key_entry.insert(0, existing_key)

        # Show/Hide API key button
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(api_frame, text="Show API Key", variable=self.show_key_var,
                       command=self.toggle_api_key_visibility).grid(row=0, column=2, padx=(10, 0))

        # Test API button
        test_btn = ttk.Button(api_frame, text="🧪 Test API Connection", command=self.test_api_connection)
        test_btn.grid(row=1, column=1, sticky=tk.W, pady=(0, 10))

        # API status label
        self.api_status_label = ttk.Label(api_frame, text="", font=('Segoe UI', 9))
        self.api_status_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Help text
        help_text = "Get your API key from: https://platform.openai.com/api-keys"
        ttk.Label(api_frame, text=help_text, font=('Segoe UI', 8),
                 foreground='#00d4aa').grid(row=3, column=0, columnspan=3, sticky=tk.W)

        # Settings form
        form_frame = ttk.LabelFrame(main_frame, text="Personal Information", padding="15")
        form_frame.pack(fill=tk.X, pady=(0, 15))

        # Agent Name
        ttk.Label(form_frame, text="Your Name:").grid(row=0, column=0, sticky=tk.W, pady=10)
        self.name_entry = ttk.Entry(form_frame, width=30)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=10)
        self.name_entry.insert(0, self.settings.get("agent_name", ""))

        # Team Name
        ttk.Label(form_frame, text="Team Name:").grid(row=1, column=0, sticky=tk.W, pady=10)
        self.team_entry = ttk.Entry(form_frame, width=30)
        self.team_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=10)
        self.team_entry.insert(0, self.settings.get("team_name", "Support Team"))

        # Signature Line
        ttk.Label(form_frame, text="Signature:").grid(row=2, column=0, sticky=tk.W, pady=10)
        self.signature_entry = ttk.Entry(form_frame, width=30)
        self.signature_entry.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=10)
        self.signature_entry.insert(0, self.settings.get("agent_signature", "Best regards"))

        # Greeting Style
        ttk.Label(form_frame, text="Greeting Style:").grid(row=3, column=0, sticky=tk.W, pady=10)
        self.greeting_var = tk.StringVar(value=self.settings.get("greeting_style", "formal"))
        greeting_frame = ttk.Frame(form_frame)
        greeting_frame.grid(row=3, column=1, sticky=tk.W, padx=(10, 0), pady=10)

        ttk.Radiobutton(greeting_frame, text="Formal (Hi [Name],)",
                       variable=self.greeting_var, value="formal").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(greeting_frame, text="Casual (Hey [Name],)",
                       variable=self.greeting_var, value="casual").pack(side=tk.LEFT)

        # Preview section
        preview_frame = ttk.LabelFrame(main_frame, text="Signature Preview", padding="10")
        preview_frame.pack(fill=tk.X, pady=(0, 15))

        self.preview_label = ttk.Label(preview_frame, text="", font=('Courier', 9))
        self.preview_label.pack(anchor=tk.W)

        # Update preview
        self.update_preview()

        # Bind entries to update preview
        self.name_entry.bind('<KeyRelease>', lambda e: self.update_preview())
        self.team_entry.bind('<KeyRelease>', lambda e: self.update_preview())
        self.signature_entry.bind('<KeyRelease>', lambda e: self.update_preview())

        # Custom AI Instructions Section
        instructions_frame = ttk.LabelFrame(main_frame, text="Custom AI Instructions (Company Knowledge)", padding="15")
        instructions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Help text
        help_label = ttk.Label(instructions_frame,
                              text="Add custom instructions for the AI agent (e.g., company software, policies, org chart, etc.)",
                              font=('Segoe UI', 9), foreground='#cccccc')
        help_label.pack(anchor=tk.W, pady=(0, 10))

        # Text editor for custom instructions
        self.instructions_text = scrolledtext.ScrolledText(
            instructions_frame,
            height=10,
            width=90,
            font=('Consolas', 10),
            wrap=tk.WORD
        )
        self.instructions_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Load existing custom instructions
        self.load_custom_instructions()

        # Instruction buttons
        inst_buttons = ttk.Frame(instructions_frame)
        inst_buttons.pack(fill=tk.X)

        ttk.Button(inst_buttons, text="💾 Save Instructions",
                  command=self.save_custom_instructions).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(inst_buttons, text="🔄 Reload",
                  command=self.load_custom_instructions).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(inst_buttons, text="📝 View Example",
                  command=self.show_example_instructions).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.close_dialog).pack(side=tk.LEFT)

        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def update_preview(self):
        """Update the signature preview"""
        name = self.name_entry.get().strip()
        signature = self.signature_entry.get().strip()
        team = self.team_entry.get().strip()

        if name:
            preview = f"{signature},\n{name}\n{team}"
        else:
            preview = f"{signature},\n{team}"

        self.preview_label.config(text=preview)

    def toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def test_api_connection(self):
        """Test the OpenAI API connection"""
        api_key = self.api_key_entry.get().strip()

        if not api_key:
            self.api_status_label.config(text="❌ Please enter an API key first", foreground='red')
            return

        self.api_status_label.config(text="🔄 Testing connection...", foreground='orange')
        self.dialog.update()

        try:
            # Test the API with a simple request
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )

            # If we get here, the API key works
            self.api_status_label.config(
                text="✅ API connection successful! Your OpenAI API key is working.",
                foreground='green'
            )

        except openai.AuthenticationError:
            self.api_status_label.config(
                text="❌ Invalid API key. Please check your key and try again.",
                foreground='red'
            )
        except openai.RateLimitError:
            self.api_status_label.config(
                text="⚠️ API key works but rate limit exceeded or no credits available.",
                foreground='orange'
            )
        except Exception as e:
            self.api_status_label.config(
                text=f"❌ Connection failed: {str(e)}",
                foreground='red'
            )

    def save_settings(self):
        """Save the settings"""
        # Save API key
        api_key = self.api_key_entry.get().strip()
        if api_key:
            if set_openai_api_key(api_key):
                pass  # Successfully saved
            else:
                messagebox.showwarning("Warning", "Could not save API key to secure storage")

        # Save personal settings
        self.settings.set("agent_name", self.name_entry.get().strip())
        self.settings.set("team_name", self.team_entry.get().strip())
        self.settings.set("agent_signature", self.signature_entry.get().strip())
        self.settings.set("greeting_style", self.greeting_var.get())

        messagebox.showinfo("Saved", "AI Assistant settings saved successfully!")
        self.close_dialog()

    def load_custom_instructions(self):
        """Load custom instructions from file"""
        try:
            knowledge_file = os.path.join(os.path.dirname(__file__), 'company_knowledge.txt')
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.instructions_text.delete(1.0, tk.END)
                    self.instructions_text.insert(1.0, content)
            else:
                # Create default template
                self.instructions_text.delete(1.0, tk.END)
                self.instructions_text.insert(1.0, self.get_default_template())
        except Exception as e:
            messagebox.showerror("Error", f"Could not load instructions: {str(e)}")

    def save_custom_instructions(self):
        """Save custom instructions to file"""
        try:
            knowledge_file = os.path.join(os.path.dirname(__file__), 'company_knowledge.txt')
            content = self.instructions_text.get(1.0, tk.END).strip()

            with open(knowledge_file, 'w', encoding='utf-8') as f:
                f.write(content)

            messagebox.showinfo("Saved", "Custom AI instructions saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save instructions: {str(e)}")

    def show_example_instructions(self):
        """Show example instructions in a popup"""
        example_window = tk.Toplevel(self.dialog)
        example_window.title("Example Custom Instructions")
        example_window.geometry("700x600")
        example_window.configure(bg='#1e1e1e')

        # Make modal
        example_window.transient(self.dialog)
        example_window.grab_set()

        frame = ttk.Frame(example_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Example Custom Instructions",
                 font=('Segoe UI', 14, 'bold')).pack(pady=(0, 10))

        ttk.Label(frame, text="Here are examples of what you can add:",
                 font=('Segoe UI', 9)).pack(anchor=tk.W, pady=(0, 10))

        example_text = scrolledtext.ScrolledText(frame, height=25, width=80,
                                                 font=('Consolas', 9), wrap=tk.WORD)
        example_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        example_content = self.get_default_template()
        example_text.insert(1.0, example_content)
        example_text.config(state='disabled')

        ttk.Button(frame, text="Close", command=example_window.destroy).pack()

    def get_default_template(self):
        """Get default template for custom instructions"""
        return """# Company Knowledge Base for AI Triage Assistant

## Current Software Subscriptions
List your company's software subscriptions here so the AI can suggest existing tools:

### Communication & Collaboration
- Microsoft 365: Email, Teams, OneDrive
- Slack: Team messaging
- Zoom: Video conferencing

### Project Management
- Jira: Issue tracking
- Confluence: Documentation

### Other Tools
- (Add your tools here)

## Organization Chart
Help the AI understand who to route requests to:

### IT Department
- IT Manager: [Name]
- Support Team: [Names]

### Executive Team
- CEO: [Name]
- CTO: [Name]

## Common Request Patterns
Guide the AI on how to handle specific request types:

### Software Requests
- Always check existing subscriptions first
- Screen recording: Teams has built-in recording
- Document collaboration: Microsoft 365, Confluence available

### Access Requests
- System access: Route to IT Support
- Financial systems: Require CFO approval
- Customer data: Require security review

### Hardware Standards
- Laptops: [Your standard models]
- Monitors: [Your standard monitors]
- Peripherals: [Your standard peripherals]

## Support Guidelines
- Be brief when acknowledging status updates from executives
- Always check existing tools before approving new software
- Include business justification for access requests

## Custom Policies
Add any company-specific policies or procedures here that the AI should know about.
"""

    def close_dialog(self):
        """Close the dialog"""
        self.dialog.destroy()


def show_ai_settings(parent):
    """Show AI settings dialog"""
    AISettingsDialog(parent)