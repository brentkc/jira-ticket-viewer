"""
AI Configuration for Jira Ticket Viewer
Configure your AI provider and API keys here
"""

import os
import keyring

# AI Provider Options
AI_PROVIDER = "openai"  # Options: "openai", "azure_openai", "local"

# OpenAI Configuration (works with Copilot license)
OPENAI_API_KEY = ""  # Will be loaded from secure storage
OPENAI_MODEL = "gpt-4o-mini"  # Use GPT-4o-mini (affordable and fast)

# Azure OpenAI Configuration (for enterprise Copilot)
AZURE_OPENAI_ENDPOINT = ""
AZURE_OPENAI_API_KEY = ""
AZURE_OPENAI_DEPLOYMENT = "gpt-4"

# Model Settings
MAX_TOKENS = 1000
TEMPERATURE = 0.3  # Lower for more consistent responses

def get_openai_api_key():
    """Get OpenAI API key from secure storage or environment"""
    # Try to get from secure storage first
    try:
        api_key = keyring.get_password("JiraTicketViewer", "openai_api_key")
        if api_key:
            return api_key
    except:
        pass

    # Fall back to environment variable
    return os.getenv("OPENAI_API_KEY", "")

def set_openai_api_key(api_key):
    """Store OpenAI API key securely"""
    try:
        keyring.set_password("JiraTicketViewer", "openai_api_key", api_key)
        return True
    except:
        return False

def get_azure_config():
    """Get Azure OpenAI configuration"""
    return {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", AZURE_OPENAI_ENDPOINT),
        "api_key": os.getenv("AZURE_OPENAI_API_KEY", AZURE_OPENAI_API_KEY),
        "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", AZURE_OPENAI_DEPLOYMENT)
    }