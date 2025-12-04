from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_rsa_keypair(key_size: int = 4096):
    """
    Generates an RSA 4096-bit key pair with public exponent 65537 
    and saves them in PEM format.
    """
    print(f"Generating RSA key pair with size: {key_size} bits...")

    # Generate the private key object
    private_key = rsa.generate_private_key(
        # Required public exponent
        public_exponent=65537, 
        # Required key size
        key_size=key_size, 
    )

    # --- Save Private Key (student_private.pem) ---
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        # Recommended format
        format=serialization.PrivateFormat.PKCS8, 
        # Required to be unencrypted for Docker/API use
        encryption_algorithm=serialization.NoEncryption() 
    )
    with open("student_private.pem", "wb") as f:
        f.write(private_pem)
    
    print("Saved student_private.pem (MUST be committed)")
    
    # --- Save Public Key (student_public.pem) ---
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        # Standard format for public keys
        format=serialization.PublicFormat.SubjectPublicKeyInfo 
    )
    with open("student_public.pem", "wb") as f:
        f.write(public_pem)
        
    print("Saved student_public.pem (MUST be committed)")
    
    # Return the key objects for immediate use in Step 4 if needed
    return private_key, public_key

if __name__ == "__main__":
    generate_rsa_keypair(key_size=4096)