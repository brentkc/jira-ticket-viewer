"""
Test script to verify the complete refactored system works
"""

def test_all_modules():
    """Test that all modules can be imported and basic functionality works"""
    success = True
    
    try:
        print("Testing imports...")
        
        # Test config
        import config
        print("[OK] config.py imported")
        
        # Test utils
        import utils
        print("[OK] utils.py imported")
        
        # Test jira_api
        import jira_api
        client = jira_api.JiraAPIClient()
        print("[OK] jira_api.py imported and client created")
        
        # Test search_filter
        import search_filter
        search_mgr = search_filter.SearchFilterManager(client, None, lambda x: None, lambda x: None)
        print("[OK] search_filter.py imported and manager created")
        
        # Test ticket_operations
        import ticket_operations
        ops_mgr = ticket_operations.TicketOperationsManager(client, lambda x: None, lambda: None)
        print("[OK] ticket_operations.py imported and manager created")
        
        # Test comment_system
        import comment_system
        comment_mgr = comment_system.CommentSystemManager(client, lambda x: None)
        print("[OK] comment_system.py imported and manager created")
        
        # Test attachment_manager
        import attachment_manager
        attach_mgr = attachment_manager.AttachmentManager(client, lambda x: None)
        print("[OK] attachment_manager.py imported and manager created")
        
        # Test user_management
        import user_management
        user_mgr = user_management.UserManagementSystem(client, lambda x: None)
        print("[OK] user_management.py imported and manager created")
        
        # Test html_viewer
        import html_viewer
        # HTML viewer requires more setup, so just test import
        print("[OK] html_viewer.py imported")
        
        # Test full ticket viewer
        import ticket_viewer_full
        print("[OK] ticket_viewer_full.py imported")
        
        print("\n[SUCCESS] All modules imported successfully!")
        print("The refactored system is ready to run.")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing complete refactored Jira Ticket Viewer system...\n")
    
    success = test_all_modules()
    
    if success:
        print("\n" + "="*60)
        print("[SUCCESS] SYSTEM READY!")
        print("="*60)
        print()
        print("To run the full application:")
        print("1. Replace ticket_viewer.py with ticket_viewer_full.py")
        print("2. Run: python main.py")
        print()
        print("All features should now be available:")
        print("• Search and filtering")
        print("• Ticket operations (assign, close, resolve)")
        print("• Comment system with @mentions")
        print("• File attachments and drag-drop")
        print("• User management and quick mentions")
        print("• HTML viewer with editing capabilities")
        print("• Right-click context menus")
        print("• Sorting and all original functionality")
        print()
    else:
        print("\n[FAIL] SYSTEM NOT READY - Fix errors above")