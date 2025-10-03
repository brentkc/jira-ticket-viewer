"""
License Validation System for Jira Ticket Viewer
This module ONLY validates licenses - it cannot generate them
"""

import hashlib
import hmac
import json
import base64
from datetime import datetime
import keyring
import uuid
import socket
import platform

class LicenseValidator:
    def __init__(self):
        self.app_name = "JiraTicketViewer"
        # Secret key for validation (must match generator)
        self.license_secret = "JTV-2025-SECRET-KEY-DO-NOT-SHARE"

    def get_machine_id(self):
        """Generate unique machine identifier"""
        hostname = socket.gethostname()
        system = platform.system()
        machine = platform.machine()
        mac = uuid.getnode()

        machine_string = f"{hostname}-{system}-{machine}-{mac}"
        return hashlib.sha256(machine_string.encode()).hexdigest()[:16]

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

            # Check machine ID (disabled for floating licenses)
            # Uncomment below to enable machine-locking
            # current_machine_id = self.get_machine_id()
            # if data.get("machine_id") and data["machine_id"] != current_machine_id:
            #     return {"valid": False, "error": "License not valid for this machine"}

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

    def check_license_status(self):
        """Check current license status"""
        license_key = self.load_license()

        if not license_key:
            return {"status": "no_license", "message": "No license found"}

        validation_result = self.validate_license_key(license_key)

        if validation_result["valid"]:
            data = validation_result["data"]
            days_remaining = validation_result["days_remaining"]

            return {
                "status": "licensed",
                "message": f"{data['type'].title()} License: {days_remaining} days remaining",
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

        if status["status"] == "licensed":
            features = status["data"]["features"]
            return features.get(feature_name, False)

        return False
