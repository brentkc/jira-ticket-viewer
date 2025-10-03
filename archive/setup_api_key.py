"""
Setup OpenAI API Key for Jira Ticket Viewer
Run this once to configure your API key securely
"""

import keyring
from ai_config import set_openai_api_key

def setup_api_key():
    """Setup OpenAI API key in secure storage"""

    api_key = input("Enter your OpenAI API key: ").strip()

    try:
        # Store in Windows Credential Manager
        keyring.set_password("JiraTicketViewer", "openai_api_key", api_key)
        print("[OK] OpenAI API key configured successfully!")
        print("[OK] Key stored securely in Windows Credential Manager")
        print("\nYou can now use AI features in the Jira Ticket Viewer.")

        # Verify it works
        stored_key = keyring.get_password("JiraTicketViewer", "openai_api_key")
        if stored_key == api_key:
            print("[OK] Verification successful - API key can be retrieved")
        else:
            print("[WARNING] Verification failed")

    except Exception as e:
        print(f"[ERROR] Error setting up API key: {str(e)}")
        return False

    return True

if __name__ == "__main__":
    print("Setting up OpenAI API key for Jira Ticket Viewer...")
    print("-" * 50)
    setup_api_key()