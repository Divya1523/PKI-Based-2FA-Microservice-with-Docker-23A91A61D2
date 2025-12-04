# app.py
import os
import base64
import time
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import pyotp
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

# Config
PRIVATE_KEY_PATH = os.environ.get("PRIVATE_KEY_PATH", "student_private.pem")
SEED_PATH = os.environ.get("SEED_PATH", "/data/seed.txt")
# For local dev override:
# PRIVATE_KEY_PATH="student_private.pem" SEED_PATH="data_local/seed.txt" uvicorn app:app --reload

app = FastAPI(title="TOTP Seed Service")


# ----- Helpers -----
def load_private_key(path: str = PRIVATE_KEY_PATH):
    try:
        with open(path, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)
    except Exception as e:
        # Do not print key contents; only indicate failure
        raise RuntimeError(f"Failed to load private key from {path}: {e}")


def decrypt_seed_from_bytes(ciphertext: bytes, private_key) -> str:
    try:
        plaintext_bytes = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
    except Exception as e:
        raise RuntimeError("Decryption failed (Key or Parameter Mismatch)")

    seed_hex = plaintext_bytes.decode("utf-8").strip()
    # validate format
    if len(seed_hex) != 64:
        raise ValueError(f"Invalid seed length: expected 64, got {len(seed_hex)}")
    valid_hex_chars = set("0123456789abcdef")
    if not all(c.lower() in valid_hex_chars for c in seed_hex):
        raise ValueError("Seed contains non-hex characters")
    return seed_hex


def save_seed_atomic(seed_hex: str, path: str = SEED_PATH):
    dirpath = os.path.dirname(path)
    os.makedirs(dirpath, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        f.write(seed_hex.strip() + "\n")
    # atomic replace
    os.replace(tmp_path, path)


def read_seed(path: str = SEED_PATH) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError("Seed not found")
    with open(path, "r") as f:
        s = f.read().strip()
    if len(s) != 64:
        raise ValueError("Stored seed invalid length")
    return s


def hex_to_base32(hex_seed: str) -> str:
    try:
        seed_bytes = bytes.fromhex(hex_seed)
    except ValueError:
        raise ValueError("Invalid hex seed")
    b32 = base64.b32encode(seed_bytes).decode("utf-8").strip().replace("=", "")
    return b32


def generate_totp_from_hex(hex_seed: str):
    b32 = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(b32)
    code = totp.now()
    valid_for = 30 - (int(time.time()) % 30)
    return code, valid_for


def verify_totp_from_hex(hex_seed: str, code: str, valid_window: int = 1) -> bool:
    b32 = hex_to_base32(hex_seed)
    totp = pyotp.TOTP(b32)
    # pyotp.verify returns True/False with valid_window param
    return bool(totp.verify(str(code), valid_window=valid_window))


# ----- Request models -----
class DecryptRequest(BaseModel):
    encrypted_seed: str


class VerifyRequest(BaseModel):
    code: str


# Load private key once at startup (fail fast) or do lazy load:
try:
    PRIVATE_KEY = load_private_key(PRIVATE_KEY_PATH)
except Exception as e:
    # store None and only error when endpoint used
    PRIVATE_KEY = None
    _privkey_load_error = str(e)
else:
    _privkey_load_error = None


# ----- Endpoints -----

@app.post("/decrypt-seed")
async def decrypt_seed_endpoint(req: DecryptRequest):
    if not req.encrypted_seed:
        raise HTTPException(status_code=400, detail={"error": "Missing encrypted_seed"})
    if PRIVATE_KEY is None:
        # Do not return internal stack trace; return generic error
        raise HTTPException(status_code=500, detail={"error": "Server private key not available"})

    # base64 decode
    try:
        ciphertext = base64.b64decode(req.encrypted_seed)
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "Invalid base64"})

    # decrypt
    try:
        seed_hex = decrypt_seed_from_bytes(ciphertext, PRIVATE_KEY)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail={"error": str(ve)})
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "Decryption failed"})

    # persist atomically
    try:
        save_seed_atomic(seed_hex, SEED_PATH)
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "Failed to persist seed"})

    return {"status": "ok"}


@app.get("/generate-2fa")
async def generate_2fa_endpoint():
    # Check seed exists
    try:
        seed_hex = read_seed(SEED_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail={"error": "Seed not decrypted yet"})
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "Failed to read seed"})

    try:
        code, valid_for = generate_totp_from_hex(seed_hex)
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "Failed to generate TOTP"})

    return {"code": code, "valid_for": valid_for}


@app.post("/verify-2fa")
async def verify_2fa_endpoint(req: VerifyRequest):
    if not req.code:
        raise HTTPException(status_code=400, detail={"error": "Missing code"})

    # Check seed exists
    try:
        seed_hex = read_seed(SEED_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail={"error": "Seed not decrypted yet"})
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "Failed to read seed"})

    try:
        valid = verify_totp_from_hex(seed_hex, req.code, valid_window=1)
    except Exception:
        raise HTTPException(status_code=500, detail={"error": "Verification failed"})

    return {"valid": valid}
