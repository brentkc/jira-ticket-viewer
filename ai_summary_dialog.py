"""
Simple AI Summary Dialog for Jira Ticket Viewer
Provides practical triage responses and fact summaries
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from ai_summarizer import AITicketSummarizer, format_analysis_for_display

class AISummaryDialog:
    def __init__(self, parent, ticket_data, parent_app):
        self.parent = parent
        self.ticket_data = ticket_data
        self.parent_app = parent_app
        self.dialog = None
        self.summarizer = AITicketSummarizer()
        self.analysis_result = None
        self.additional_context = ""

        # First show context input dialog
        self.show_context_dialog()

    def show_context_dialog(self):
        """Show dialog to optionally add context for AI analysis"""
        context_dialog = tk.Toplevel(self.parent)
        context_dialog.title("Add Context (Optional)")
        context_dialog.geometry("500x300")
        context_dialog.configure(bg='#1e1e1e')

        # Make it modal
        context_dialog.transient(self.parent)
        context_dialog.grab_set()

        # Center the dialog
        context_dialog.update_idletasks()
        x = (context_dialog.winfo_screenwidth() // 2) - 250
        y = (context_dialog.winfo_screenheight() // 2) - 150
        context_dialog.geometry(f"500x300+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(context_dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(main_frame, text="Add Additional Context for AI (Optional)",
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w', pady=(0, 5))

        ttk.Label(main_frame, text="Provide any context to help AI frame the response correctly:",
                 font=('Segoe UI', 9)).pack(anchor='w', pady=(0, 10))

        # Context text area
        context_text = scrolledtext.ScrolledText(
            main_frame,
            width=60,
            height=8,
            bg='#ffffff',
            fg='#000000',
            insertbackground='#000000',
            font=('Segoe UI', 10),
            wrap=tk.WORD
        )
        context_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        context_text.insert(tk.END, "Example: This is a status update, not a request.")
        context_text.bind('<FocusIn>', lambda e: context_text.delete(1.0, tk.END) if context_text.get(1.0, tk.END).strip().startswith("Example:") else None)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        def continue_with_context():
            self.additional_context = context_text.get(1.0, tk.END).strip()
            if self.additional_context.startswith("Example:"):
                self.additional_context = ""
            context_dialog.destroy()
            self.create_dialog()
            self.start_analysis()

        def skip_context():
            self.additional_context = ""
            context_dialog.destroy()
            self.create_dialog()
            self.start_analysis()

        ttk.Button(button_frame, text="Continue with Context", command=continue_with_context).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Skip", command=skip_context).pack(side=tk.LEFT)

    def create_dialog(self):
        """Create the simple AI summary dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"🎯 Triage Assistant - {self.ticket_data.get('key', 'Unknown')}")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg='#1e1e1e')

        # Make it modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (400)
        y = (self.dialog.winfo_screenheight() // 2) - (300)
        self.dialog.geometry(f"800x600+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ticket_key = self.ticket_data.get('key', 'Unknown')
        ticket_summary = self.ticket_data.get('fields', {}).get('summary', 'No summary')

        ttk.Label(header_frame, text=f"Ticket: {ticket_key}",
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(header_frame, text=ticket_summary,
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(5, 0))

        # Loading label
        self.loading_label = ttk.Label(main_frame, text="🔄 Analyzing ticket...",
                                      font=('Segoe UI', 11))
        self.loading_label.pack(pady=20)

        # Content area (hidden initially)
        self.content_frame = ttk.Frame(main_frame)

        # Customer Response area (editable, clean)
        response_frame = ttk.LabelFrame(self.content_frame, text="Customer Response (Review & Edit Before Sending)", padding="10")
        response_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.response_text = scrolledtext.ScrolledText(
            response_frame,
            width=70,
            height=12,
            bg='#ffffff',
            fg='#000000',
            insertbackground='#000000',
            font=('Segoe UI', 10),
            wrap=tk.WORD
        )
        self.response_text.pack(fill=tk.BOTH, expand=True)

        # Internal Assessment area (read-only, for agent use only)
        assessment_frame = ttk.LabelFrame(self.content_frame, text="Internal Assessment (For Your Eyes Only)", padding="10")
        assessment_frame.pack(fill=tk.BOTH, expand=True)

        self.assessment_text = scrolledtext.ScrolledText(
            assessment_frame,
            width=70,
            height=8,
            bg='#2d2d2d',
            fg='#ffffff',
            insertbackground='#ffffff',
            font=('Courier', 9),
            wrap=tk.WORD
        )
        self.assessment_text.pack(fill=tk.BOTH, expand=True)

        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))

        ttk.Button(button_frame, text="Copy Customer Response",
                  command=self.copy_customer_response).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Post as Comment",
                  command=self.post_comment).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="Close",
                  command=self.close_dialog).pack(side=tk.RIGHT)

        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self.close_dialog)

    def start_analysis(self):
        """Start ticket analysis in background thread"""
        def analyze():
            try:
                # Verbose logging for debugging
                print(f"[AI DEBUG] Starting analysis for ticket: {self.ticket_data.get('key', 'Unknown')}")

                self.analysis_result = self.summarizer.analyze_ticket(self.ticket_data, additional_context=self.additional_context)

                print(f"[AI DEBUG] Analysis completed successfully")
                self.dialog.after(0, self.display_analysis)
            except Exception as e:
                import traceback
                error_details = f"AI Analysis Error: {str(e)}\n\nFull traceback:\n{traceback.format_exc()}"
                print(f"[AI DEBUG] ERROR: {error_details}")

                # Also try to log to parent app if available
                if hasattr(self.parent_app, 'log_to_debug'):
                    self.parent_app.log_to_debug(f"AI Summary Error: {str(e)}")
                    self.parent_app.log_to_debug(f"Full traceback: {traceback.format_exc()}")

                self.dialog.after(0, lambda: self.show_error(error_details))

        threading.Thread(target=analyze, daemon=True).start()

    def display_analysis(self):
        """Display the analysis results"""
        if not self.analysis_result:
            self.show_error("No analysis results available")
            return

        # Hide loading, show content
        self.loading_label.pack_forget()
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Display customer response (keep it editable for review/editing)
        self.response_text.config(state=tk.NORMAL)
        self.response_text.delete(1.0, tk.END)
        self.response_text.insert(tk.END, self.analysis_result['triage_response'])
        # Keep editable so user can review and modify before sending

        # Display internal assessment (read-only)
        self.assessment_text.config(state=tk.NORMAL)
        self.assessment_text.delete(1.0, tk.END)

        assessment_content = self.analysis_result.get('internal_assessment', 'No assessment available')
        self.assessment_text.insert(tk.END, assessment_content)
        self.assessment_text.config(state=tk.DISABLED)

        # Update dialog title with ticket type
        ticket_type = self.analysis_result['ticket_type'].replace('_', ' ').title()
        self.dialog.title(f"AI Triage Assistant - {self.ticket_data.get('key')} [{ticket_type}]")

    def copy_customer_response(self):
        """Copy customer-facing response to clipboard"""
        response_content = self.response_text.get(1.0, tk.END)
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(response_content.strip())
        messagebox.showinfo("Copied", "Customer response copied to clipboard!\n\nYou can now paste it into Jira.")

    def post_comment(self):
        """Post the response as a comment to the ticket"""
        response_content = self.response_text.get(1.0, tk.END).strip()

        if not response_content:
            messagebox.showwarning("Empty Response", "No response to post")
            return

        # Ask for confirmation
        confirm = messagebox.askyesno(
            "Confirm Post",
            "Post this response as a comment to the ticket?\n\nYou can review it one more time before confirming."
        )

        if confirm:
            try:
                # Try to post comment via parent app
                if hasattr(self.parent_app, 'add_comment_to_ticket'):
                    ticket_key = self.ticket_data.get('key')
                    success = self.parent_app.add_comment_to_ticket(ticket_key, response_content)
                    if success:
                        # Refresh ticket details to show the new comment
                        if hasattr(self.parent_app, 'load_ticket_details'):
                            self.parent_app.load_ticket_details(refresh_from_api=True, load_comments=True)
                        messagebox.showinfo("Posted", "Response posted as comment successfully!")
                        self.close_dialog()
                    else:
                        raise Exception("Failed to post comment")
                else:
                    # Fallback: just copy to clipboard
                    self.dialog.clipboard_clear()
                    self.dialog.clipboard_append(response_content)
                    messagebox.showinfo("Copied", "Comment posting not available.\n\nResponse copied to clipboard - please paste manually.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to post comment: {str(e)}\n\nResponse has been copied to clipboard.")
                self.dialog.clipboard_clear()
                self.dialog.clipboard_append(response_content)

    def show_error(self, error_message):
        """Show error message"""
        self.loading_label.config(text=f"❌ Error: {error_message}")

        error_frame = ttk.Frame(self.dialog)
        error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(error_frame, text="There was an error analyzing this ticket.",
                 font=('Segoe UI', 12)).pack(pady=10)
        ttk.Label(error_frame, text=str(error_message),
                 font=('Segoe UI', 10)).pack(pady=5)

    def close_dialog(self):
        """Close the dialog"""
        self.dialog.destroy()


def show_ai_summary(parent, ticket_data, parent_app):
    """Convenience function to show AI summary dialog"""
    AISummaryDialog(parent, ticket_data, parent_app)