# Jira Ticket Viewer - Distribution Guide

## 📦 COMPILED APPLICATIONS

### ✅ Customer-Facing Application
**File:** `dist/Jira-Ticket-Viewer.exe` (54 MB)
- **Purpose:** This is the application you sell/distribute to customers
- **Features:**
  - Full Jira ticket management
  - Secure credential storage (uses Windows Credential Manager)
  - License validation (can only validate, cannot generate licenses)
  - No hardcoded API tokens or personal credentials
  - Users configure their own Jira instance on first run

### 🔐 Admin License Generator
**File:** `dist/ADMIN-License-Generator.exe` (14 MB)
- **Purpose:** FOR YOUR USE ONLY - Generate license keys for customers
- **⚠️ DO NOT DISTRIBUTE THIS FILE TO CUSTOMERS ⚠️**
- **Features:**
  - Generate trial, standard, and premium licenses
  - Set custom expiration dates
  - Email license keys to customers
  - Test and validate generated keys

---

## 🔑 LICENSE SYSTEM

### License Types Available:
1. **Trial** (14 days)
   - All basic features
   - 1 user
   - No export/API access

2. **Standard** (365 days default)
   - All features including export
   - Up to 5 users
   - API access

3. **Premium** (365 days default)
   - All features
   - Unlimited users
   - Priority support

### How to Generate Licenses:

1. Run `ADMIN-License-Generator.exe`
2. Enter customer details:
   - Customer name
   - Customer email (required)
   - Company name (optional)
3. Select license type and duration
4. Click "Generate License Key"
5. Copy or save the license key to send to customer

### Machine Locking:
- **Currently DISABLED** - Licenses work on any machine
- To enable machine-locking, edit `license_validator.py` lines 55-58

---

## 📋 CUSTOMER ONBOARDING PROCESS

### Step 1: Customer Downloads Application
Provide customer with `Jira-Ticket-Viewer.exe`

### Step 2: Initial Setup
When customer launches the app for the first time:
1. They'll be prompted to enter:
   - Their Jira URL (e.g., https://yourcompany.atlassian.net)
   - Their email address
   - Their Jira API token (they generate this from their Jira account)
   - Project key

2. Credentials are stored securely in Windows Credential Manager
   - **NOT** in the application files
   - **NOT** visible to you as the vendor

### Step 3: License Activation
1. Customer pastes the license key you provided
2. Application validates the license
3. Features unlock based on license type

---

## 🛠️ RECOMPILING THE APPLICATIONS

### Customer Application:
```bash
cd "C:\Users\BrentConlan\OneDrive - Medem\Code\jira-project"
pyinstaller Customer-Jira-Viewer.spec --clean
```

### Admin License Generator:
```bash
cd "C:\Users\BrentConlan\OneDrive - Medem\Code\jira-project"
pyinstaller Admin-License-Generator.spec --clean
```

---

## 🔒 SECURITY NOTES

### What's Protected:
✅ License generation secret key is NOT in customer application
✅ No hardcoded credentials in customer application
✅ Customer credentials stored securely via Windows Credential Manager
✅ License generator is separate executable for admin use only

### Important Files:

**Customer Application Uses:**
- `license_validator.py` - Can only VALIDATE licenses, not generate
- `JiraTicketGUI_enhanced.py` - Main application

**Admin Tool Uses:**
- `license_manager.py` - Can GENERATE and validate licenses
- `admin_license_generator.py` - GUI for license generation

**DO NOT DISTRIBUTE:**
- `license_manager.py`
- `admin_license_generator.py`
- `ADMIN-License-Generator.exe`
- Any files in the source code directory

---

## 📝 CHANGING THE LICENSE SECRET

To change the license secret key (recommended for production):

1. Edit `license_manager.py` line 19:
   ```python
   self.license_secret = "YOUR-NEW-SECRET-KEY-HERE"
   ```

2. Edit `license_validator.py` line 20 with THE SAME secret:
   ```python
   self.license_secret = "YOUR-NEW-SECRET-KEY-HERE"
   ```

3. Recompile both applications

⚠️ **CRITICAL:** Both files MUST use the same secret key or licenses won't validate!

---

## 📧 CUSTOMER SUPPORT TEMPLATE

When sending licenses to customers:

```
Subject: Your Jira Ticket Viewer License

Dear [Customer Name],

Thank you for your purchase of Jira Ticket Viewer!

License Details:
─────────────────────────────────
Type: [Standard/Premium]
Valid Until: [Date]

Your License Key:
[PASTE LICENSE KEY HERE]

Installation Instructions:
─────────────────────────────────
1. Download Jira-Ticket-Viewer.exe
2. Run the application
3. Enter your Jira connection details when prompted
4. Paste your license key when requested
5. Click "Activate License"

Need help? Contact us at [your support email]

Best regards,
[Your Company]
```

---

## 🚀 DISTRIBUTION CHECKLIST

Before sending to customer:
- [ ] Generated license key using ADMIN-License-Generator.exe
- [ ] Verified license key works (use "Test Key" button)
- [ ] Saved license key to file or email template
- [ ] Confirmed you're sending `Jira-Ticket-Viewer.exe` (NOT the admin tool)
- [ ] Provided customer with setup instructions

---

## 📊 FILE STRUCTURE

```
jira-project/
├── dist/
│   ├── Jira-Ticket-Viewer.exe           ← DISTRIBUTE THIS
│   └── ADMIN-License-Generator.exe      ← KEEP PRIVATE
├── JiraTicketGUI_enhanced.py            ← Main app source
├── license_validator.py                 ← Validator (in customer app)
├── license_manager.py                   ← Generator (NOT in customer app)
├── admin_license_generator.py           ← Admin tool source
├── Customer-Jira-Viewer.spec            ← Build spec for customer app
└── Admin-License-Generator.spec         ← Build spec for admin tool
```

---

## ⚙️ TECHNICAL DETAILS

### Dependencies Included:
- tkinter (GUI framework)
- requests (API calls)
- keyring (secure credential storage)
- Pillow (image handling)
- anthropic (AI features)
- All other required libraries

### Platform Support:
- Windows 10/11 (64-bit)
- No installation required (standalone EXE)
- No admin rights needed to run

### Data Storage:
- Credentials: Windows Credential Manager
- License: Windows Credential Manager
- Settings: JSON files in application directory
- No cloud storage, fully local

---

## 🎯 NEXT STEPS

1. **Test both applications**
   - Run customer app, verify setup wizard works
   - Run admin tool, generate a test license
   - Activate test license in customer app

2. **Customize branding** (optional)
   - Add your company logo/icon
   - Update window titles
   - Modify color scheme

3. **Create installer** (optional)
   - Use NSIS or Inno Setup to create .msi installer
   - Add desktop shortcuts
   - Include uninstaller

4. **Set up distribution**
   - Host on your website
   - Create download links
   - Set up customer portal

---

Generated: 2025-10-02
Version: 1.0
