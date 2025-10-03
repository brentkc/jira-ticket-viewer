"""
Jira API communication module for ticket operations
"""

import requests
import json
from requests.auth import HTTPBasicAuth
from tkinter import messagebox
import webbrowser
import logging
import datetime
import os
from config import JIRA_URL, API_TOKEN, PROJECT_KEY, ISSUE_TYPES

# Setup logging
log_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(log_dir, 'jira_debug.log')

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger(__name__)


class JiraAPIClient:
    def __init__(self, email_callback=None, status_callback=None):
        """
        Initialize Jira API client
        
        Args:
            email_callback: Function to get user email
            status_callback: Function to update status messages
        """
        self.jira_url = JIRA_URL
        self.api_token = API_TOKEN
        self.project_key = PROJECT_KEY
        self.issue_types = ISSUE_TYPES
        self.email_callback = email_callback
        self.status_callback = status_callback
    
    def get_user_email(self):
        """Get user email from callback or return empty string"""
        if self.email_callback:
            return self.email_callback()
        return ""
    
    def update_status(self, message):
        """Update status message via callback"""
        if self.status_callback:
            self.status_callback(message)
    
    def make_jira_request(self, endpoint, method="GET", params=None, data=None, files=None):
        """Make authenticated request to Jira API"""
        logger.info(f"Making Jira request: {method} {endpoint}")
        logger.debug(f"Params: {params}")

        user_email = self.get_user_email()
        logger.debug(f"User email: {user_email}")

        if not user_email.strip():
            logger.error("No user email provided")
            messagebox.showerror("Error", "Please enter your email address")
            return None

        url = f"{self.jira_url}/rest/api/2/{endpoint}"
        logger.debug(f"Full URL: {url}")

        auth = HTTPBasicAuth(user_email.strip(), self.api_token)
        headers = {"Accept": "application/json"}
        
        if method in ["POST", "PUT"] and not files:
            headers["Content-Type"] = "application/json"
        
        try:
            logger.debug(f"Request headers: {headers}")

            # Make the request based on method
            if method == "GET":
                logger.debug("Making GET request")
                response = requests.get(url, auth=auth, headers=headers, params=params, timeout=30)
            elif method == "POST":
                if files:
                    logger.debug("Making POST request with files")
                    response = requests.post(url, auth=auth, files=files, data=data, timeout=30)
                else:
                    logger.debug("Making POST request with JSON")
                    response = requests.post(url, auth=auth, headers=headers, json=data, timeout=30)
            elif method == "PUT":
                logger.debug("Making PUT request")
                response = requests.put(url, auth=auth, headers=headers, json=data, timeout=30)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                messagebox.showerror("Error", f"Unsupported HTTP method: {method}")
                return None

            logger.info(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")

            # Check response
            response.raise_for_status()

            # Return JSON or success indicator
            if response.text.strip():
                result = response.json()
                logger.debug(f"Response JSON length: {len(str(result))}")
                if isinstance(result, list):
                    logger.info(f"Returned {len(result)} items")
                elif isinstance(result, dict):
                    logger.info(f"Returned dict with keys: {list(result.keys())}")
                return result
            else:
                logger.info("Empty response, returning success")
                return {"success": True}

        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout: {str(e)}"
            logger.error(error_msg)
            messagebox.showerror("Timeout Error", error_msg)
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"API Error: {str(e)}"
            logger.error(error_msg)
            if 'response' in locals() and response:
                logger.error(f"Response status: {response.status_code}")
                error_msg += f"\nStatus: {response.status_code}"
                if response.text:
                    logger.error(f"Response text: {response.text[:1000]}")
                    error_msg += f"\nResponse: {response.text[:500]}"
            messagebox.showerror("API Error", error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            messagebox.showerror("Error", error_msg)
            return None
    
    def load_all_tickets(self):
        """Load all tickets in the project - using VERIFIED working approach"""
        # Build JQL to filter only Incident and Service request tickets
        issue_type_ids = list(self.issue_types.values())  # ["11395", "11396"]
        jql = f'project = {self.project_key} AND issuetype in ({",".join(issue_type_ids)})'
        
        params = {
            'jql': jql,
            'maxResults': 100,
            'startAt': 0
            # NO fields parameter - get everything by default
        }
        
        return self.make_jira_request("search", params=params)
    
    def search_tickets(self, search_query):
        """Search tickets using JQL or text search"""
        if search_query.strip().startswith('project'):
            # If query starts with 'project', treat as raw JQL
            jql = search_query
        else:
            # Build text search JQL
            issue_type_ids = list(self.issue_types.values())
            jql = (f'project = {self.project_key} AND '
                   f'issuetype in ({",".join(issue_type_ids)}) AND '
                   f'(summary ~ "{search_query}" OR description ~ "{search_query}" OR '
                   f'key = "{search_query.upper()}")')
        
        params = {
            'jql': jql,
            'maxResults': 100,
            'startAt': 0
        }
        
        return self.make_jira_request("search", params=params)
    
    def get_ticket_details(self, ticket_key):
        """Get detailed information for a specific ticket"""
        return self.make_jira_request(f"issue/{ticket_key}")
    
    def get_ticket_comments(self, ticket_key):
        """Get comments for a specific ticket"""
        return self.make_jira_request(f"issue/{ticket_key}/comment")
    
    def add_comment_to_ticket(self, ticket_key, comment_body):
        """Add a comment to a ticket"""
        comment_data = {
            "body": comment_body
        }
        return self.make_jira_request(f"issue/{ticket_key}/comment", method="POST", data=comment_data)
    
    def assign_ticket(self, ticket_key, assignee_email):
        """Assign a ticket to a user"""
        assign_data = {
            "fields": {
                "assignee": {
                    "name": assignee_email.split('@')[0] if '@' in assignee_email else assignee_email
                }
            }
        }
        return self.make_jira_request(f"issue/{ticket_key}", method="PUT", data=assign_data)
    
    def transition_ticket(self, ticket_key, transition_id, comment=None):
        """Transition a ticket to a new status"""
        transition_data = {
            "transition": {"id": transition_id}
        }
        
        if comment:
            transition_data["update"] = {
                "comment": [{"add": {"body": comment}}]
            }
        
        return self.make_jira_request(f"issue/{ticket_key}/transitions", method="POST", data=transition_data)
    
    def get_available_transitions(self, ticket_key):
        """Get available transitions for a ticket"""
        return self.make_jira_request(f"issue/{ticket_key}/transitions")
    
    def create_ticket(self, summary, description, issue_type_id, assignee=None):
        """Create a new ticket"""
        ticket_data = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": summary,
                "description": description,
                "issuetype": {"id": issue_type_id}
            }
        }
        
        if assignee:
            ticket_data["fields"]["assignee"] = {
                "name": assignee.split('@')[0] if '@' in assignee else assignee
            }
        
        return self.make_jira_request("issue", method="POST", data=ticket_data)
    
    def add_attachment(self, ticket_key, file_path):
        """Add an attachment to a ticket"""
        try:
            with open(file_path, 'rb') as file:
                files = {'file': file}
                return self.make_jira_request(f"issue/{ticket_key}/attachments", 
                                            method="POST", files=files)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to attach file: {str(e)}")
            return None
    
    def get_project_users(self):
        """Get users who can be assigned to tickets in the project"""
        logger.info(f"Getting project users for project: {self.project_key}")

        params = {
            'project': self.project_key,
            'maxResults': 50
        }
        logger.debug(f"Project users params: {params}")

        result = self.make_jira_request("user/assignable/search", params=params)

        if result:
            logger.info(f"Found {len(result)} project users")
            for i, user in enumerate(result[:3]):  # Log first 3 users
                logger.debug(f"User {i+1}: {user.get('displayName', 'Unknown')} - {user.get('emailAddress', 'No email')}")
        else:
            logger.warning("No project users found or request failed")

        return result

    def search_users(self, query):
        """Search for users"""
        logger.info(f"Searching users with query: '{query}'")

        params = {
            'query': query,
            'maxResults': 20
        }
        logger.debug(f"User search params: {params}")

        result = self.make_jira_request("user/search", params=params)

        if result:
            logger.info(f"User search returned {len(result)} results")
            for i, user in enumerate(result[:3]):  # Log first 3 users
                logger.debug(f"Search result {i+1}: {user.get('displayName', 'Unknown')} - {user.get('emailAddress', 'No email')}")
        else:
            logger.warning(f"No users found for query: '{query}' or request failed")

        return result
    
    def open_dashboard(self):
        """Open the Jira Service Desk dashboard in browser"""
        dashboard_url = f"{self.jira_url}/jira/servicedesk/projects/{self.project_key}/summary"
        webbrowser.open(dashboard_url)
        self.update_status(f"Opened dashboard for project {self.project_key}")
    
    def get_ticket_url(self, ticket_key):
        """Get the URL for a specific ticket"""
        return f"{self.jira_url}/browse/{ticket_key}"
    
    def open_ticket_in_browser(self, ticket_key):
        """Open a ticket in the browser"""
        ticket_url = self.get_ticket_url(ticket_key)
        webbrowser.open(ticket_url)
        return ticket_url