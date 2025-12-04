import base64
import os
import time
import pyotp
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# --- UTILITY HELPERS ---

def load_private_key(path: str = "student_private.pem"):
    """Loads the RSA private key from a PEM file."""
    # Note: When running in the container, the path will be adjusted (e.g., /app/student_private.pem)
    try:
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    except Exception as e:
        print(f"ERROR: Failed to load or parse private key: {e}")
        # Return None or raise an exception that the main app handles
        return None

def save_hex_seed(seed: str, path: str = "/data/seed.txt"):
    """Saves the decrypted seed to the persistent volume path."""
    try:
        # Create the directory if it doesn't exist (critical for Docker volume)
        os.makedirs(os.path.dirname(path), exist_ok=True) 
        with open(path, 'w') as f:
            f.write(seed.strip()) # Ensure no extra whitespace, crucial for TOTP
            f.write("\n") # Add a final newline
    except IOError as e:
        raise Exception(f"Failed to write seed to persistence path {path}: {e}")

# --- STEP 5: DECRYPTION LOGIC ---

def decrypt_seed(encrypted_seed_b64: str, private_key) -> str:
    """
    Decrypts base64-encoded encrypted seed using RSA/OAEP-SHA256.
    Returns the 64-character hex seed.
    """
    if not private_key:
        raise Exception("Private key object is missing or failed to load.")

    # 1. Base64 decode the encrypted seed string
    try:
        ciphertext = base64.b64decode(encrypted_seed_b64)
    except base64.binascii.Error:
        raise ValueError("Input is not valid Base64.")

    # 2. RSA/OAEP decrypt with CRITICAL parameters
    try:
        plaintext_bytes = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception:
        # Catch decryption errors (e.g., wrong key, wrong parameters)
        raise Exception("Decryption failed (Key or Parameter Mismatch)")

    # 3. Decode bytes to UTF-8 string
    seed_hex = plaintext_bytes.decode("utf-8").strip()

    # 4. Validate: must be 64-character hex string
    if len(seed_hex) != 64:
        raise ValueError(f"Invalid seed length: expected 64, got {len(seed_hex)}")

    # Check for valid hex characters (0-9, a-f, case-insensitive)
    valid_hex_chars = set("0123456789abcdef")
    if not all(c.lower() in valid_hex_chars for c in seed_hex):
        raise ValueError("Seed contains non-hex characters")

    # 5. Return hex seed
    return seed_hex

# --- STEP 6: TOTP LOGIC ---

def hex_to_base32(hex_seed: str) -> str:
    """Converts a 64-character hex seed string into a Base32 encoded string."""
    try:
        # Convert hex string to bytes
        seed_bytes = bytes.fromhex(hex_seed)
    except ValueError:
        raise ValueError("Invalid hex string provided for seed conversion.")

    # Convert bytes to base32 encoding and decode to a string
    base32_seed = base64.b32encode(seed_bytes).decode('utf-8')
    return base32_seed

def generate_totp_code(hex_seed: str) -> dict:
    """
    Generate current TOTP code (SHA-1, 30s, 6 digits) and remaining validity time.
    """
    base32_seed = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(base32_seed) 
    
    code = totp.now()
    valid_for = 30 - (int(time.time()) % 30)
    
    return {"code": code, "valid_for": valid_for}

def verify_totp_code(hex_seed: str, code: str, valid_window: int = 1) -> bool:
    """
    Verify TOTP code with time window tolerance of +/- 1 period (30 seconds).
    """
    base32_seed = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(base32_seed)
    
    # Verify with valid_window=1 (current period +/- 1 period)
    is_valid = totp.verify(code, valid_window=valid_window)
    
    return is_valid

# --- LOCAL TESTING ENTRY POINT (For checking Step 5 only) ---

def run_local_test():
    """
    Function to locally test Step 5 logic before setting up the API/Docker.
    Requires encrypted_seed.txt and student_private.pem in the current directory.
    """
    try:
        # 1. Read encrypted seed
        with open("encrypted_seed.txt", "r") as f:
            encrypted_seed_b64 = f.read().strip()
            
        # 2. Load private key
        # CRITICAL: We use the local path for testing here.
        private_key = load_private_key("student_private.pem")

        # 3. Decrypt seed
        seed_hex = decrypt_seed(encrypted_seed_b64, private_key)
        print("--- Step 5 Decryption Test Results ---")
        print("✅ SUCCESS! Decrypted seed (64-char hex):", seed_hex)

        # 4. Local Persistence Test (optional for quick check)
        # Note: This creates a temporary directory for verification, NOT the final Docker path.
        data_dir = "data_local_test" 
        save_hex_seed(seed_hex, os.path.join(data_dir, "seed.txt"))
        print(f"✅ Persistence simulated: Seed written to {os.path.join(data_dir, 'seed.txt')}")
        
    except FileNotFoundError as e:
        print(f"❌ TEST FAILED: Required file not found. Ensure {e.filename} is in the current directory.")
    except Exception as e:
        print(f"❌ TEST FAILED: Decryption or validation error: {e}")


# FIX: The entry point now uses the correct double underscore notation: __main__
if __name__ == "__main__":
    run_local_test()