"""
Test script to debug email autocomplete functionality
"""
import tkinter as tk
from tkinter import ttk
import requests
from requests.auth import HTTPBasicAuth
import keyring
import json

def test_user_search():
    """Test Jira user search endpoints"""
    
    # Get credentials from keyring (same way as main app)
    user_email = "brent@medemgroup.com"
    api_token = keyring.get_password("JiraTicketViewer", user_email)
    jira_url = "https://zsoftware.atlassian.net"
    project_key = "ITS"
    
    if not api_token:
        print("ERROR: No API token found in keyring")
        return
        
    print(f"SUCCESS: Found API token for {user_email}")
    auth = HTTPBasicAuth(user_email, api_token)
    
    # Test different user search endpoints
    endpoints_to_test = [
        f"user/assignable/search?query=brent&project={project_key}&maxResults=10",
        f"user/search?query=brent&maxResults=10",
        f"user/picker?query=brent&maxResults=10",
        f"project/{project_key}/role",  # To see available users in project
    ]
    
    for endpoint in endpoints_to_test:
        url = f"{jira_url}/rest/api/3/{endpoint}"
        print(f"\nTesting: {endpoint}")
        print(f"   URL: {url}")
        
        try:
            response = requests.get(url, auth=auth, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    print(f"   Found {len(data)} items")
                    for i, item in enumerate(data[:3]):  # Show first 3
                        print(f"     [{i+1}] {item}")
                elif isinstance(data, dict):
                    print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
                else:
                    print(f"   Response: {data}")
            else:
                print(f"   Error: {response.text[:200]}")
                
        except Exception as e:
            print(f"   Exception: {str(e)}")

def test_ui_autocomplete():
    """Test the UI autocomplete functionality"""
    print("\nTesting UI Autocomplete...")
    
    root = tk.Tk()
    root.title("Email Autocomplete Test")
    root.geometry("500x300")
    
    # Create test UI similar to the new ticket dialog
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    ttk.Label(main_frame, text="Reporter Email Test:", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
    
    # Test variables
    reporter_var = tk.StringVar()
    user_data_cache = {}
    
    # Entry and autocomplete setup
    entry_frame = ttk.Frame(main_frame)
    entry_frame.pack(fill=tk.X, pady=(0, 10))
    
    ttk.Label(entry_frame, text="Type email:").pack(side=tk.LEFT)
    reporter_entry = ttk.Entry(entry_frame, textvariable=reporter_var, width=40)
    reporter_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
    
    # Autocomplete dropdown
    autocomplete_frame = ttk.Frame(main_frame)
    autocomplete_listbox = tk.Listbox(autocomplete_frame, height=6)
    autocomplete_listbox.pack(fill=tk.BOTH, expand=True)
    
    # Test function to simulate API call
    def on_type_change():
        query = reporter_var.get().strip()
        print(f"User typed: '{query}'")
        
        if len(query) < 2:
            autocomplete_frame.pack_forget()
            print("   Query too short, hiding dropdown")
            return
            
        # Simulate some test data
        test_users = [
            {"displayName": "Brent Conlan", "emailAddress": "brent@medemgroup.com", "accountId": "123456"},
            {"displayName": "Test User", "emailAddress": "test@medemgroup.com", "accountId": "789012"},
            {"displayName": "Admin User", "emailAddress": "admin@medemgroup.com", "accountId": "345678"},
        ]
        
        # Filter test users based on query
        matching_users = [u for u in test_users if query.lower() in u["emailAddress"].lower() or query.lower() in u["displayName"].lower()]
        
        if matching_users:
            print(f"   Found {len(matching_users)} matching users")
            autocomplete_listbox.delete(0, tk.END)
            user_data_cache.clear()
            
            for user in matching_users:
                display_text = f"{user['displayName']} ({user['emailAddress']})"
                autocomplete_listbox.insert(tk.END, display_text)
                user_data_cache[display_text] = user
                print(f"     Added: {display_text}")
            
            autocomplete_frame.pack(fill=tk.X, pady=(5, 0))
            print("   Showing dropdown")
        else:
            autocomplete_frame.pack_forget()
            print("   No matches, hiding dropdown")
    
    def on_select(event=None):
        selection = autocomplete_listbox.curselection()
        if selection:
            selected_text = autocomplete_listbox.get(selection[0])
            reporter_var.set(selected_text)
            autocomplete_frame.pack_forget()
            print(f"Selected: {selected_text}")
    
    # Bind events
    reporter_var.trace('w', lambda *args: on_type_change())
    autocomplete_listbox.bind('<Double-Button-1>', on_select)
    autocomplete_listbox.bind('<Return>', on_select)
    
    # Instructions
    instructions = ttk.Label(main_frame, text="Type 'brent' or 'test' to see autocomplete", 
                           font=('Segoe UI', 10), foreground='gray')
    instructions.pack(anchor=tk.W, pady=(10, 0))
    
    root.mainloop()

if __name__ == "__main__":
    print("Email Autocomplete Debug Tool")
    print("=" * 50)
    
    # Test API endpoints first
    test_user_search()
    
    # Run UI test automatically
    print("\n" + "=" * 50)
    # test_ui_autocomplete()  # Skip UI test for now
    
    print("\nDebug complete!")