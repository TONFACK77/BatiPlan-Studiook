"""SELLER ONLY. Generates the Ed25519 key pair. Keep seller_kit/private_key.pem secret and backed up!
Run ONCE before building the installer. It writes the public key into batiplan/_pubkey.py (shipped with the app)."""
import base64, os, sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
priv_path = os.path.join(root, "seller_kit", "private_key.pem")
if os.path.exists(priv_path) and "--force" not in sys.argv:
    sys.exit("private_key.pem already exists. Use --force ONLY if you accept to invalidate every licence already sold.")
k = Ed25519PrivateKey.generate(); os.makedirs(os.path.dirname(priv_path), exist_ok=True)
with open(priv_path, "wb") as f: f.write(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
with open(os.path.join(root, "batiplan", "_pubkey.py"), "w") as f: f.write('PUBLIC_KEY_B64 = "%s"\n' % base64.b64encode(pub).decode())
print("OK - keys generated.")
