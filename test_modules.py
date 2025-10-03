"""
Test script to verify our refactored modules work correctly
"""

def test_imports():
    """Test that all modules can be imported"""
    try:
        import config
        print("[OK] config.py imported successfully")
        print(f"  - JIRA_URL: {config.JIRA_URL}")
        print(f"  - PROJECT_KEY: {config.PROJECT_KEY}")
        print(f"  - Theme colors available: {len(config.THEME_COLORS)}")
    except Exception as e:
        print(f"[FAIL] config.py failed: {e}")
        return False

    try:
        import utils
        print("[OK] utils.py imported successfully")
        
        # Test a utility function
        size = utils.format_file_size(1024)
        print(f"  - format_file_size(1024) = {size}")
        
        # Test email validation
        valid = utils.validate_email("test@example.com")
        print(f"  - validate_email('test@example.com') = {valid}")
        
    except Exception as e:
        print(f"[FAIL] utils.py failed: {e}")
        return False

    try:
        import jira_api
        print("[OK] jira_api.py imported successfully")
        
        # Test creating client (without callbacks)
        client = jira_api.JiraAPIClient()
        print(f"  - JiraAPIClient created: {client.jira_url}")
        
    except Exception as e:
        print(f"[FAIL] jira_api.py failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("Testing refactored modules...\n")
    
    success = test_imports()
    
    if success:
        print("\n[SUCCESS] All modules passed basic tests!")
        print("Ready to create ticket_viewer.py")
    else:
        print("\n[ERROR] Some modules failed. Check errors above.")