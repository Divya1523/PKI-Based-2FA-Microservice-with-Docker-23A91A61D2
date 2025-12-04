import requests
import os

# --- CONFIGURE YOUR INPUTS HERE ---
STUDENT_ID = "23A91A61D2"
GITHUB_REPO_URL = "https://github.com/Divya1523/PKI-Based-2FA-Microservice-with-Docker-23A91A61D2" 
API_URL = "https://eajeyq4r3zljoq4rpovy2nthda0vtjqf.lambda-url.ap-south-1.on.aws"

# --- FILE PATHS ---
PUBLIC_KEY_PATH = "student_public.pem"
ENCRYPTED_SEED_PATH = "encrypted_seed.txt"


def request_seed(student_id: str, github_repo_url: str, api_url: str):
    """
    Requests the encrypted seed from the instructor API and saves it locally.
    """
    
    # 1. Read student public key from PEM file
    try:
        with open(PUBLIC_KEY_PATH, 'r') as f:
            # Read the entire PEM content, including newlines, which will be handled by json.dumps
            public_key_pem = f.read() 
    except FileNotFoundError:
        print(f"ERROR: Public key file not found at {PUBLIC_KEY_PATH}. Ensure Step 2 is complete.")
        return

    # 2. Prepare HTTP POST request payload
    payload = {
        "student_id": student_id,
        "github_repo_url": github_repo_url,
        # The requests library handles formatting the string with \n escapes correctly
        "public_key": public_key_pem
    }
    
    print(f"Sending request for Student ID: {student_id}...")

    # 3. Send POST request to instructor API
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status() # Raise exception for 4xx or 5xx errors
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: API request failed (network/timeout/server error). Details: {e}")
        return

    # 4. Parse JSON response
    try:
        data = response.json()
        
        if data.get("status") == "success":
            encrypted_seed = data.get("encrypted_seed")
            
            if not encrypted_seed:
                print("ERROR: API returned success but 'encrypted_seed' field is empty.")
                return
                
        else:
            print(f"ERROR: API returned status '{data.get('status')}'")
            print(f"Full response: {data}")
            return
            
    except ValueError:
        print("ERROR: Failed to parse JSON response from API.")
        print(f"Raw response: {response.text}")
        return

    # 5. Save encrypted seed to file
    try:
        with open(ENCRYPTED_SEED_PATH, 'w') as f:
            # CRITICAL: Save as plain text, single line
            f.write(encrypted_seed.strip())
        
        print("\n✅ SUCCESS: Encrypted seed successfully saved.")
        print(f"File: {ENCRYPTED_SEED_PATH}")
        print("You can now proceed to Step 5 (Implement Decryption Function).")
        
    except IOError as e:
        print(f"ERROR: Failed to save seed to file: {e}")


if __name__ == "__main__":
    request_seed(STUDENT_ID, GITHUB_REPO_URL, API_URL)