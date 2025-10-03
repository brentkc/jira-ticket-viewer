#!/usr/bin/env python3
"""
Wrapper script to run JiraTicketGUI_enhanced.py with full error capture
"""
import sys
import subprocess
import traceback
from datetime import datetime

def main():
    print(f"[WRAPPER] Starting at {datetime.now()}")
    print(f"[WRAPPER] Python version: {sys.version}")
    print(f"[WRAPPER] Python executable: {sys.executable}")

    # Set environment variables for better error handling
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUNBUFFERED'] = '1'

    try:
        print("[WRAPPER] Launching JiraTicketGUI_enhanced.py...")

        # Run the application and capture everything
        result = subprocess.run([
            sys.executable,
            'JiraTicketGUI_enhanced.py'
        ],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'  # Replace problematic characters instead of failing
        )

        print(f"[WRAPPER] Process finished with return code: {result.returncode}")

        if result.stdout:
            print("[WRAPPER] STDOUT:")
            # Clean output for safe printing
            safe_stdout = result.stdout.encode('ascii', errors='replace').decode('ascii')
            print(safe_stdout)

        if result.stderr:
            print("[WRAPPER] STDERR:")
            # Clean output for safe printing
            safe_stderr = result.stderr.encode('ascii', errors='replace').decode('ascii')
            print(safe_stderr)

    except Exception as e:
        print(f"[WRAPPER] Exception occurred: {e}")
        print(f"[WRAPPER] Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()