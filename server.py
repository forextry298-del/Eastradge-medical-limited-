import os, re, sqlite3, secrets, string, hashlib
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, jsonify, session, send_file, redirect, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash

ROOT = os.path.abspath(os.environ.get("PLATFORM_DIR", "."))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(ROOT, "eastradge_accounts.sqlite3"))
LAUNCH_UTC = datetime(2026, 11, 30, 4, 0, 0, tzinfo=timezone.utc)
SYSTEM_CODE = "FGJGL"
ADMIN_PHONE = os.environ.get("ADMIN_PHONE", "0758878297")
app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE-THIS-SECRET-KEY-BEFORE-DEPLOYMENT")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "0") == "1")

def db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            invite_code TEXT NOT NULL UNIQUE,
            invited_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(invited_by) REFERENCES accounts(id)
        )""")
        con.execute("CREATE INDEX IF NOT EXISTS idx_accounts_invited_by ON accounts(invited_by)")

def launched():
    return datetime.now(timezone.utc) >= LAUNCH_UTC

def valid_phone(phone):
    return bool(re.fullmatch(r"07\d{8}", phone or ""))

def code_exists(con, code):
    if code == SYSTEM_CODE:
        return True
    return con.execute("SELECT 1 FROM accounts WHERE invite_code=?", (code,)).fetchone() is not None

def make_code(con, phone):
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "INV" + phone[-4:] + "".join(secrets.choice(alphabet) for _ in range(4))
        if not code_exists(con, code):
            return code

def invite_counts(con, user_id):
    # Descendant counts by referral depth; only aggregate counts are returned.
    level1 = [r["id"] for r in con.execute("SELECT id FROM accounts WHERE invited_by=?", (user_id,)).fetchall()]
    level2, level3 = [], []
    if level1:
        marks = ",".join("?" for _ in level1)
        level2 = [r["id"] for r in con.execute(f"SELECT id FROM accounts WHERE invited_by IN ({marks})", level1).fetchall()]
    if level2:
        marks = ",".join("?" for _ in level2)
        level3 = [r["id"] for r in con.execute(f"SELECT id FROM accounts WHERE invited_by IN ({marks})", level2).fetchall()]
    return {"LV1": len(level1), "LV2": len(level2), "LV3": len(level3), "total": len(level1)+len(level2)+len(level3)}

def account_payload(con, row):
    counts = invite_counts(con, row["id"])
    host = request.host_url.rstrip("/")
    inviter = None
    if row["invited_by"]:
        inviter = con.execute(
            "SELECT invite_code FROM accounts WHERE id=?",
            (row["invited_by"],)
        ).fetchone()

    created_ms = int(
        datetime.fromisoformat(row["created_at"]).timestamp() * 1000
    )

    account = {
        "uid": "INV-" + str(row["id"]),
        "name": row["full_name"],
        "phone": row["phone"],
        "isAdmin": row["phone"] == ADMIN_PHONE,
        "referralCode": row["invite_code"],
        "referredBy": inviter["invite_code"] if inviter else "DIRECT",
        "avatarUrl": "",
        "depositBalance": 0,
        "withdrawBalance": 0,
        "totalEarned": 0,
        "withdrawCountToday": 0,
        "teamStats": {
            "lv1Count": counts["LV1"],
            "lv2Count": counts["LV2"],
            "lv3Count": counts["LV3"],
            "lv1Earned": 0,
            "lv2Earned": 0,
            "lv3Earned": 0
        },
        "claimedMilestones": [],
        "bonus45PlusClaimedCount": 0,
        "orders": [],
        "transactions": [],
        "createdAt": created_ms
    }

    return {
        "fullName": row["full_name"],
        "phone": row["phone"],
        "inviteCode": row["invite_code"],
        "inviteLink": host + "/?ref=" + row["invite_code"],
        "counts": counts,
        "levels": {"LV1": "15%", "LV2": "5%", "LV3": "1%"},
        "account": account
    }

def logged_in(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("account_id"):
            return jsonify({"error": "Please log in."}), 401
        return fn(*args, **kwargs)
    return wrapper

@app.get("/api/status")
def status():
    return jsonify({"launched": launched(), "launchUtc": LAUNCH_UTC.isoformat()})

@app.post("/api/register")
def register():
    if launched():
        return jsonify({"error": "The reservation period has ended. Please log in."}), 403
    data = request.get_json(silent=True) or {}
    name = " ".join((data.get("fullName") or "").split())
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""
    invite = (data.get("inviteCode") or "").strip().upper()
    if not invite:
        return jsonify({"error": "Invitation code is required."}), 400
    if len(name) < 3:
        return jsonify({"error": "Enter your full name."}), 400
    if not valid_phone(phone):
        return jsonify({"error": "Phone must be 10 digits and start with 07."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must contain at least 6 characters."}), 400
    with db() as con:
        if con.execute("SELECT 1 FROM accounts WHERE phone=?", (phone,)).fetchone():
            return jsonify({"error": "This phone number is already registered."}), 409
        if not code_exists(con, invite):
            return jsonify({"error": "Invitation code is not valid."}), 400
        inviter = con.execute("SELECT id FROM accounts WHERE invite_code=?", (invite,)).fetchone() if invite != SYSTEM_CODE else None
        code = make_code(con, phone)
        try:
            cur = con.execute(
                "INSERT INTO accounts(full_name,phone,password_hash,invite_code,invited_by,created_at) VALUES(?,?,?,?,?,?)",
                (name, phone, generate_password_hash(password), code, inviter["id"] if inviter else None, datetime.now(timezone.utc).isoformat())
            )
            row = con.execute("SELECT * FROM accounts WHERE id=?", (cur.lastrowid,)).fetchone()
        except sqlite3.IntegrityError:
            return jsonify({"error": "This phone number or invitation code is already in use."}), 409
        session["account_id"] = row["id"]
        return jsonify(account_payload(con, row))

@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""
    with db() as con:
        row = con.execute("SELECT * FROM accounts WHERE phone=?", (phone,)).fetchone()
        if not row or not check_password_hash(row["password_hash"], password):
            return jsonify({"error": "Incorrect phone number or password."}), 401
        session["account_id"] = row["id"]
        return jsonify(account_payload(con, row))

@app.get("/api/me")
@logged_in
def me():
    with db() as con:
        row = con.execute("SELECT * FROM accounts WHERE id=?", (session["account_id"],)).fetchone()
        if not row:
            session.clear()
            return jsonify({"error": "Account not found."}), 404
        return jsonify(account_payload(con, row))

@app.get("/api/platform-account")
@logged_in
def platform_account():
    with db() as con:
        row = con.execute(
            "SELECT * FROM accounts WHERE id=?",
            (session["account_id"],)
        ).fetchone()
        if not row:
            session.clear()
            return jsonify({"error": "Account not found."}), 404
        return jsonify(account_payload(con, row))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.get("/account")
def account_page():
    if not launched():
        return redirect("/")
    if not session.get("account_id"):
        return redirect("/")
    return send_file(os.path.join(ROOT, "account.html"))

@app.get("/platform")
def platform():
    if not launched():
        return redirect("/")
    if not session.get("account_id"):
        return redirect("/")
    path = os.path.join(ROOT, "index.html")
    if not os.path.isfile(path):
        return "Your existing index.html was not found in the project root.", 404
    # Serve original file bytes without modifying the user's platform file.
    return send_file(path)

@app.get("/")
def home():
    # Before launch, everyone sees the gate. After launch, only logged-in users
    # may access the existing platform.
    if launched() and session.get("account_id"):
        return send_file(os.path.join(ROOT, "index.html"))
    return send_file(os.path.join(os.path.dirname(__file__), "gate.html"))

@app.get("/<path:filename>")
def platform_assets(filename):
    # Allow existing platform assets only after launch and authenticated login.
    if not launched() or not session.get("account_id"):
        return redirect("/")
    full = os.path.abspath(os.path.join(ROOT, filename))
    if not full.startswith(ROOT + os.sep) or not os.path.isfile(full):
        return "Not found", 404
    return send_file(full)

init_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")), debug=False)
