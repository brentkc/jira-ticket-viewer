"""
AI Settings Manager
Stores user preferences for AI-generated responses
"""

import json
import os
from pathlib import Path

class AISettings:
    def __init__(self):
        self.settings_file = Path.home() / ".jira_ai_settings.json"
        self.settings = self.load_settings()

    def load_settings(self):
        """Load AI settings from file"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        # Default settings
        return {
            "agent_name": "",
            "agent_signature": "Best regards",
            "team_name": "Support Team",
            "include_greeting": True,
            "greeting_style": "formal"  # formal or casual
        }

    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get(self, key, default=None):
        """Get a setting value"""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Set a setting value"""
        self.settings[key] = value
        return self.save_settings()

    def get_signature_block(self):
        """Get formatted signature block"""
        name = self.settings.get("agent_name", "")
        signature = self.settings.get("agent_signature", "Best regards")
        team = self.settings.get("team_name", "Support Team")

        if name:
            return f"{signature},\n{name}\n{team}"
        else:
            return f"{signature},\n{team}"