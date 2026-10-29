"""One-time script: create the first admin (auth user + profiles row)."""
import os
import sys
from getpass import getpass

import requests
from dotenv import load_dotenv

load_dotenv()

URL = os.getenv("SUPABASE_URL", "").rstrip("/")
if not URL:
    sys.exit("SUPABASE_URL missing in .env")

service_key = os.getenv("SUPABASE_SERVICE_KEY") or getpass("Supabase secret key (hidden): ")
email = input("Admin email: ").strip()
password = getpass("Admin password (min 6 chars, hidden): ")

headers = {
    "apikey": service_key,
    "Authorization": f"Bearer {service_key}",
    "Content-Type": "application/json",
}

# 1. Create the auth user (already confirmed)
r = requests.post(
    f"{URL}/auth/v1/admin/users",
    headers=headers,
    json={"email": email, "password": password, "email_confirm": True},
    timeout=15,
)

if r.status_code in (200, 201):
    user_id = r.json()["id"]
    print("Created auth user.")
else:
    # User may already exist: look it up
    lst = requests.get(
        f"{URL}/auth/v1/admin/users", headers=headers, params={"per_page": 200}, timeout=15
    )
    users = lst.json().get("users", []) if lst.status_code == 200 else []
    match = [u for u in users if (u.get("email") or "").lower() == email.lower()]
    if not match:
        sys.exit(f"Could not create user: {r.status_code} {r.text}")
    user_id = match[0]["id"]
    print("Auth user already exists, reusing it.")

# 2. Create or update the profile row as admin
p = requests.post(
    f"{URL}/rest/v1/profiles",
    headers={**headers, "Prefer": "resolution=merge-duplicates,return=minimal"},
    json={"id": user_id, "role": "admin", "is_active": True, "can_register_farmers": True},
    timeout=15,
)
if p.status_code in (200, 201, 204):
    print(f"Done. {email} is now an admin. You can log in at /login.")
else:
    sys.exit(f"Profile insert failed: {p.status_code} {p.text}")
