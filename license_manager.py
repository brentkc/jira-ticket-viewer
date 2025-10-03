"""
License Management System for Jira Ticket Viewer
Handles license key validation, expiration, and feature restrictions
"""

import hashlib
import hmac
import json
import base64
from datetime import datetime, timedelta
import keyring
import uuid
import socket
import platform

class LicenseManager:
    def __init__(self):
        self.app_name = "JiraTicketViewer"
        self.license_secret = "JTV-2025-SECRET-KEY-DO-NOT-SHARE"  # Change this for production
        self.trial_days = 14
        
    def get_machine_id(self):
        """Generate unique machine identifier"""
        # Combine hostname, platform, and MAC address for unique ID
        hostname = socket.gethostname()
        system = platform.system()
        machine = platform.machine()
        
        # Get MAC address
        mac = uuid.getnode()
        
        # Create composite ID
        machine_string = f"{hostname}-{system}-{machine}-{mac}"
        return hashlib.sha256(machine_string.encode()).hexdigest()[:16]
    
    def generate_license_key(self, user_email, license_type="standard", days_valid=365):
        """Generate a license key for a user"""
        expiry_date = datetime.now() + timedelta(days=days_valid)
        machine_id = self.get_machine_id()
        
        # License data
        license_data = {
            "email": user_email,
            "type": license_type,
            "expires": expiry_date.isoformat(),
            "machine_id": machine_id,
            "version": "1.0",
            "features": self.get_license_features(license_type)
        }
        
        # Create signature
        data_string = json.dumps(license_data, sort_keys=True)
        signature = hmac.new(
            self.license_secret.encode(),
            data_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine data and signature
        license_payload = {
            "data": license_data,
            "signature": signature
        }
        
        # Encode as base64
        license_json = json.dumps(license_payload)
        license_key = base64.b64encode(license_json.encode()).decode()
        
        return license_key
    
    def get_license_features(self, license_type):
        """Define features available for each license type"""
        features = {
            "trial": {
                "create_tickets": True,
                "comment_tickets": True,
                "assign_tickets": True,
                "search_tickets": True,
                "export_data": False,
                "api_access": False,
                "priority_support": False,
                "max_users": 1
            },
            "standard": {
                "create_tickets": True,
                "comment_tickets": True,
                "assign_tickets": True,
                "search_tickets": True,
                "export_data": True,
                "api_access": True,
                "priority_support": False,
                "max_users": 5
            },
            "premium": {
                "create_tickets": True,
                "comment_tickets": True,
                "assign_tickets": True,
                "search_tickets": True,
                "export_data": True,
                "api_access": True,
                "priority_support": True,
                "max_users": -1  # Unlimited
            }
        }
        return features.get(license_type, features["trial"])
    
    def validate_license_key(self, license_key):
        """Validate a license key"""
        try:
            # Decode base64
            license_json = base64.b64decode(license_key.encode()).decode()
            license_payload = json.loads(license_json)
            
            data = license_payload["data"]
            signature = license_payload["signature"]
            
            # Verify signature
            data_string = json.dumps(data, sort_keys=True)
            expected_signature = hmac.new(
                self.license_secret.encode(),
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                return {"valid": False, "error": "Invalid license signature"}
            
            # Check expiry
            expiry_date = datetime.fromisoformat(data["expires"])
            if datetime.now() > expiry_date:
                return {"valid": False, "error": "License expired"}
            
            # Check machine ID (optional - can be disabled for floating licenses)
            current_machine_id = self.get_machine_id()
            if data.get("machine_id") and data["machine_id"] != current_machine_id:
                return {"valid": False, "error": "License not valid for this machine"}
            
            return {
                "valid": True,
                "data": data,
                "days_remaining": (expiry_date - datetime.now()).days
            }
            
        except Exception as e:
            return {"valid": False, "error": f"License validation error: {str(e)}"}
    
    def save_license(self, license_key):
        """Save license key securely"""
        try:
            keyring.set_password(self.app_name, "license_key", license_key)
            return True
        except Exception as e:
            print(f"Could not save license: {e}")
            return False
    
    def load_license(self):
        """Load saved license key"""
        try:
            license_key = keyring.get_password(self.app_name, "license_key")
            return license_key
        except Exception as e:
            print(f"Could not load license: {e}")
            return None
    
    def start_trial(self, user_email):
        """Start trial period"""
        trial_key = self.generate_license_key(user_email, "trial", self.trial_days)
        return self.save_license(trial_key)
    
    def get_trial_status(self):
        """Check if trial has been started"""
        try:
            trial_started = keyring.get_password(self.app_name, "trial_started")
            return trial_started is not None
        except:
            return False
    
    def set_trial_started(self):
        """Mark trial as started"""
        try:
            keyring.set_password(self.app_name, "trial_started", "true")
            return True
        except:
            return False
    
    def check_license_status(self):
        """Check current license status"""
        # Load saved license
        license_key = self.load_license()
        
        if not license_key:
            # No license found
            if not self.get_trial_status():
                return {"status": "no_license", "message": "No license found"}
            else:
                return {"status": "trial_expired", "message": "Trial expired"}
        
        # Validate license
        validation_result = self.validate_license_key(license_key)
        
        if validation_result["valid"]:
            data = validation_result["data"]
            days_remaining = validation_result["days_remaining"]
            
            if data["type"] == "trial":
                return {
                    "status": "trial_active",
                    "message": f"Trial: {days_remaining} days remaining",
                    "data": data,
                    "days_remaining": days_remaining
                }
            else:
                return {
                    "status": "licensed",
                    "message": f"Licensed: {days_remaining} days remaining",
                    "data": data,
                    "days_remaining": days_remaining
                }
        else:
            return {
                "status": "invalid",
                "message": validation_result["error"]
            }
    
    def has_feature(self, feature_name):
        """Check if current license has specific feature"""
        status = self.check_license_status()
        
        if status["status"] in ["trial_active", "licensed"]:
            features = status["data"]["features"]
            return features.get(feature_name, False)
        
        return False

# Example usage and testing
if __name__ == "__main__":
    lm = LicenseManager()
    
    # Generate sample licenses
    print("Machine ID:", lm.get_machine_id())
    
    # Generate different license types
    trial_key = lm.generate_license_key("user@example.com", "trial", 14)
    standard_key = lm.generate_license_key("user@example.com", "standard", 365)
    premium_key = lm.generate_license_key("user@example.com", "premium", 365)
    
    print(f"\nTrial Key: {trial_key[:50]}...")
    print(f"Standard Key: {standard_key[:50]}...")
    print(f"Premium Key: {premium_key[:50]}...")
    
    # Test validation
    print(f"\nValidation Results:")
    print("Trial:", lm.validate_license_key(trial_key))
    print("Standard:", lm.validate_license_key(standard_key))
    print("Premium:", lm.validate_license_key(premium_key))