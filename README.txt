EASTRADGE CAPITAL — LAUNCH GATE ADD-ON
=====================================

IMPORTANT: This add-on is designed to leave your existing index.html untouched.
It adds a Flask server, gate page, and SQLite account database. The server serves
the existing index.html only after launch and successful login.

Launch time: 30 November 2026, 07:00 EAT (UTC+3)
Equivalent UTC: 30 November 2026, 04:00 UTC

FEATURES
- Countdown and two tabs matching the supplied screenshots.
- Before launch: account reservation with full name, unique phone, password,
  and a REQUIRED invitation code. The root code FGJGL is accepted only when
  entered explicitly; an empty invitation-code field is rejected.
- Checks phone existence in a persistent SQLite database; duplicate phone
  registration is rejected.
- Passwords are stored as salted password hashes, never plaintext.
- Generates a unique personal invitation code and link.
- Calculates LV1/LV2/LV3 aggregate invite counts (15%, 5%, 1% labels).
- Does not reveal invited users' names or phone numbers.
- At launch, the countdown panel is hidden permanently based on the fixed UTC
  launch timestamp. The gate's login remains as the access step; after successful
  phone/password login, the server serves the existing platform's original
  index.html without changing its file bytes.
- Does not rewrite or patch index.html.

INSTALL IN TERMUX (from your project root)
1. Extract this ZIP into ~/eastradge-capital so server.py and gate.html are
   directly inside that folder.
2. Install Python packages:
      pip install -r requirements.txt
3. Start:
      python server.py
4. Open:
      http://127.0.0.1:8080

Do NOT run `python -m http.server` for this add-on. It must run server.py.

DATABASE
- Local account records are stored in eastradge_accounts.sqlite3 in the project
  root. Back up this file. It is not part of the platform index.html.
- On Render, the filesystem may be ephemeral. Attach a persistent disk and set
  DATABASE_PATH to a path on that disk, or use a managed database, otherwise
  records can be lost on redeploy/restart.

RENDER DEPLOYMENT
- This add-on requires a Python web service, not a static-site-only deployment.
- Set Build Command: pip install -r requirements.txt
- Set Start Command: python server.py
- Set environment variable SECRET_KEY to a long random secret.
- Set DATABASE_PATH to a persistent disk path (for example /var/data/eastradge.sqlite3)
  and mount a persistent disk at /var/data.
- Set COOKIE_SECURE=1 when deployed over HTTPS.
- Ensure the existing index.html and all its assets remain in the same project root.
- Do not replace your existing render.yaml blindly; adapt your service settings
  while retaining any existing deployment configuration you need.

SECURITY / INTEGRATION LIMITS
- The launch gate is enforced by the server, not just the browser countdown.
- The phone-number duplicate check is global within this database.
- The invitation code root FGJGL is intentionally accepted as the system root.
- This package does not modify the platform's own internal login or balance
  system, nor does it automatically merge these accounts into Firebase or any
  existing platform database. It authenticates access through this gate and
  then serves the existing platform file unchanged. If the platform has its own
  separate login, that remains separate unless you authorize a backend
  integration.
- For production, configure a persistent database and strong SECRET_KEY.
- This is an add-on package, not a replacement copy of your platform.
