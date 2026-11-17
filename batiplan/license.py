"""Offline licence system: Ed25519-signed keys bound to a machine code + 14-day trial.
The customer sends his MACHINE CODE (WhatsApp / e-mail) -> the seller returns a licence key -> works offline."""
import base64, hashlib, hmac, json, os, platform, uuid, datetime
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from .brand import APP_ID, TRIAL_DAYS
from ._pubkey import PUBLIC_KEY_B64

_FULL = {"draw", "dxf", "png", "save", "pdf", "xlsx", "hatch_all", "stairs", "furniture_all", "check", "underlay"}
FEATURES = {"starter": {"draw", "dxf", "png", "save"}, "pro": set(_FULL), "edu": set(_FULL), "trial": set(_FULL), "demo": {"draw", "save", "png"}}


def config_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, APP_ID); os.makedirs(d, exist_ok=True); return d


def _hw_id():
    """Stable per-computer identifier (never random per run)."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
            return "win:" + str(winreg.QueryValueEx(k, "MachineGuid")[0])
    except Exception: pass
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            v = open(p).read().strip()
            if v: return "lnx:" + v
        except Exception: pass
    try:
        import subprocess
        out = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if "IOPlatformUUID" in line: return "mac:" + line.split('"')[-2]
    except Exception: pass
    p = os.path.join(config_dir(), "hwid.txt")          # last resort: generated once, then persisted
    if not os.path.exists(p):
        with open(p, "w") as f: f.write(uuid.uuid4().hex)
    return "gen:" + open(p).read().strip()


def machine_code():
    h = hashlib.sha256(("batiplan|" + _hw_id()).encode()).hexdigest().upper()[:16]
    return "-".join(h[i:i + 4] for i in range(0, 16, 4))


def _b64d(s): s = s.strip(); return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Licence:
    def __init__(self, ok=False, edition="demo", name="", email="", expires="", reason="", trial_left=0):
        self.ok, self.edition, self.name, self.email, self.expires, self.reason, self.trial_left = ok, edition, name, email, expires, reason, trial_left
    def allows(self, feature): return feature in FEATURES.get(self.edition, set())
    @property
    def watermark(self): return "DEMO" if self.edition == "demo" else None


def verify_key(key_text, mcode=None):
    mcode = mcode or machine_code()
    try:
        k = key_text.strip().replace("\n", "").replace(" ", "")
        if not k.startswith("BP1-"): return Licence(reason="format")
        body, sig = k[4:].split("."); payload = _b64d(body)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64)).verify(_b64d(sig), payload); d = json.loads(payload.decode())
    except (InvalidSignature, ValueError, KeyError): return Licence(reason="signature")
    if d.get("mid") not in ("*", mcode): return Licence(reason="machine", name=d.get("name", ""))
    exp = d.get("expires", "")
    if exp and datetime.date.fromisoformat(exp) < datetime.date.today(): return Licence(reason="expired", name=d.get("name", ""), expires=exp)
    return Licence(True, d.get("edition", "pro"), d.get("name", ""), d.get("email", ""), exp)


def _state_path(): return os.path.join(config_dir(), "state.dat")
def _lic_path(): return os.path.join(config_dir(), "licence.key")
def _mac(blob): return hmac.new(("bp-state-" + machine_code()).encode(), blob.encode(), hashlib.sha256).hexdigest()[:20]


def trial_days_left(today=None):
    today = today or datetime.date.today(); p = _state_path(); first, last = today, today
    if os.path.exists(p):
        try:
            txt = open(p).read().split("|")
            if _mac(txt[0] + "|" + txt[1]) == txt[2]: first, last = datetime.date.fromisoformat(txt[0]), datetime.date.fromisoformat(txt[1])
            else: return 0
        except Exception: return 0
    if today < last - datetime.timedelta(days=1): return 0   # clock rolled back
    last = max(last, today); blob = f"{first.isoformat()}|{last.isoformat()}"
    with open(p, "w") as f: f.write(blob + "|" + _mac(blob))
    return max(0, TRIAL_DAYS - (today - first).days)


def current_licence():
    p = _lic_path()
    if os.path.exists(p):
        lic = verify_key(open(p).read())
        if lic.ok: return lic
    left = trial_days_left()
    if left > 0: return Licence(True, "trial", reason="trial", trial_left=left)
    return Licence(False, "demo", reason="trial_over")


def activate(key_text):
    lic = verify_key(key_text)
    if lic.ok:
        with open(_lic_path(), "w") as f: f.write(key_text.strip())
    return lic


def issue_key(private_pem_path, name, email, edition="pro", mid="*", expires=""):
    """Seller side (used by seller_kit/keygen.py)."""
    from cryptography.hazmat.primitives import serialization
    priv = serialization.load_pem_private_key(open(private_pem_path, "rb").read(), None)
    payload = json.dumps({"v": 1, "name": name, "email": email, "edition": edition, "mid": mid, "expires": expires, "issued": datetime.date.today().isoformat()}, separators=(",", ":")).encode()
    e = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
    return "BP1-" + e(payload) + "." + e(priv.sign(payload))
