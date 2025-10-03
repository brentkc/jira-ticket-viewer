"""
Utility functions for Jira Ticket Viewer
"""

import json
import os
import re
from datetime import datetime
from config import QUICK_MENTIONS_FILE, DEFAULT_QUICK_MENTIONS


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def load_quick_mentions(file_path=None):
    """Load quick mentions from file"""
    if not file_path:
        file_path = QUICK_MENTIONS_FILE
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            return DEFAULT_QUICK_MENTIONS
    except Exception as e:
        print(f"Could not load quick mentions: {e}")
        return DEFAULT_QUICK_MENTIONS


def save_quick_mentions(mentions, file_path=None):
    """Save quick mentions to file"""
    if not file_path:
        file_path = QUICK_MENTIONS_FILE
    
    try:
        with open(file_path, 'w') as f:
            json.dump(mentions, f)
        return True
    except Exception as e:
        print(f"Could not save quick mentions: {e}")
        return False


def format_datetime(datetime_str):
    """Format datetime string for display"""
    if not datetime_str:
        return ""
    
    try:
        # Parse ISO format datetime
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return datetime_str


def truncate_text(text, max_length=100):
    """Truncate text to specified length with ellipsis"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def extract_mentions_from_text(text):
    """Extract @mentions from text"""
    if not text:
        return []
    
    mention_pattern = r'@([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
    matches = re.findall(mention_pattern, text)
    return list(set(matches))  # Remove duplicates


def format_jira_text(text):
    """Format Jira text for display (handle basic formatting)"""
    if not text:
        return ""
    
    # Replace Jira markup with plain text equivalents
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # Remove bold
    text = re.sub(r'_([^_]+)_', r'\1', text)    # Remove italic
    text = re.sub(r'\+([^+]+)\+', r'\1', text)  # Remove underline
    text = re.sub(r'\^([^\^]+)\^', r'\1', text) # Remove superscript
    text = re.sub(r'~([^~]+)~', r'\1', text)    # Remove subscript
    text = re.sub(r'\{\{([^}]+)\}\}', r'\1', text) # Remove monospace
    
    return text


def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    if not filename:
        return "untitled"
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    
    if not filename:
        return "untitled"
    
    return filename[:255]  # Limit length


def parse_jira_key(text):
    """Extract Jira ticket key from text if present"""
    if not text:
        return None
    
    # Pattern for Jira keys (e.g., ITS-123, PROJ-456)
    pattern = r'\b([A-Z]{2,10}-\d+)\b'
    match = re.search(pattern, text.upper())
    
    return match.group(1) if match else None


def sort_tickets_by_key(tickets):
    """Sort tickets by key (numeric part)"""
    def extract_number(ticket):
        key = ticket.get('key', '')
        match = re.search(r'-(\d+)$', key)
        return int(match.group(1)) if match else 0
    
    return sorted(tickets, key=extract_number)


def sort_tickets_by_date(tickets, field='created'):
    """Sort tickets by date field"""
    def extract_date(ticket):
        fields = ticket.get('fields', {})
        date_str = fields.get(field)
        if date_str:
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                pass
        return datetime.min
    
    return sorted(tickets, key=extract_date, reverse=True)


def get_status_category(status_name):
    """Get status category for color coding"""
    if not status_name:
        return "unknown"
    
    status_lower = status_name.lower()
    
    if status_lower in ['open', 'new', 'created', 'to do', 'todo']:
        return "new"
    elif status_lower in ['in progress', 'in-progress', 'working', 'active']:
        return "in_progress"
    elif status_lower in ['done', 'closed', 'resolved', 'complete', 'finished']:
        return "done"
    elif status_lower in ['waiting', 'pending', 'blocked', 'hold']:
        return "waiting"
    else:
        return "other"


def extract_priority_order(priority_name):
    """Get numeric order for priority sorting"""
    if not priority_name:
        return 999
    
    priority_lower = priority_name.lower()
    priority_map = {
        'highest': 1,
        'high': 2,
        'medium': 3,
        'normal': 3,
        'low': 4,
        'lowest': 5
    }
    
    return priority_map.get(priority_lower, 999)