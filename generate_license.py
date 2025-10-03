"""
Quick license key generator for Brent
"""

from license_manager import LicenseManager

def main():
    license_manager = LicenseManager()

    # Generate a premium license for Brent's email
    email = "brent@medemgroup.com"
    license_type = "premium"
    days_valid = 3650  # 10 years

    print(f"Generating license for: {email}")
    print(f"License type: {license_type}")
    print(f"Valid for: {days_valid} days")
    print()

    try:
        license_key = license_manager.generate_license_key(email, license_type, days_valid)
        print("[SUCCESS] LICENSE KEY GENERATED:")
        print("=" * 50)
        print(license_key)
        print("=" * 50)
        print()
        print("Copy this license key and paste it into the JIRA Ticket Viewer when prompted.")

        # Also try to validate it
        print("\n[VALIDATION] TESTING LICENSE:")
        validation_result = license_manager.validate_license(license_key, email)
        if validation_result["valid"]:
            print("[OK] License is valid!")
            print(f"   Features: {validation_result['features']}")
            print(f"   Expires: {validation_result['expires']}")
        else:
            print("[ERROR] License validation failed")
            print(f"   Error: {validation_result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"[ERROR] Error generating license: {e}")

if __name__ == "__main__":
    main()