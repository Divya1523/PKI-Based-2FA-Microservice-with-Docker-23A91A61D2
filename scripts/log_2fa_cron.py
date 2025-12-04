#!/usr/bin/env python3
import datetime
import os
import sys

# CRITICAL: This imports your core TOTP generation logic from the utility module.
# Ensure your file containing generate_totp_code is named 'crypto_utils.py' 
# or adjust the import line accordingly.
import sys
sys.path.append('/app')
from crypto_utils import generate_totp_code # This import will now work

SEED_PATH = "/data/seed.txt"

def main():
    try:
        # 1. Read seed from persistent storage (Docker Volume)
        if not os.path.exists(SEED_PATH):
            # Log error if seed file is missing (i.e., /decrypt-seed hasn't run yet)
            print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Seed file not found", file=sys.stderr)
            return

        with open(SEED_PATH, 'r') as f:
            hex_seed = f.read().strip()
        
        if not hex_seed:
            print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Seed is empty", file=sys.stderr)
            return

        # 2. Generate current TOTP code
        # The function uses the container's UTC time for generation.
        code = generate_totp_code(hex_seed)

        # 3. Get current UTC timestamp (Required format)
        current_time_utc = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # 4. Output the formatted line to stdout (which cron redirects to /cron/last_code.txt)
        # Format: YYYY-MM-DD HH:MM:SS - 2FA Code: XXXXXX (Required)
        print(f"{current_time_utc} - 2FA Code: {code}")

    except Exception as e:
        # Log any unexpected errors to the log file (via stderr)
        print(f"[{datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}] CRON JOB FAILED: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()