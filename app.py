import os
from datetime import datetime, timezone
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import Flask, flash, get_flashed_messages, redirect, render_template, request, session, url_for, send_from_directory
from flask_seasurf import SeaSurf

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

if not (SUPABASE_URL and SUPABASE_KEY and SECRET_KEY):
    raise RuntimeError(
        "Set SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and FLASK_SECRET_KEY in .env"
    )

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
csrf = SeaSurf(app)

DASHBOARDS = {
    "admin": "admin_dashboard",
    "field_officer": "field_officer_dashboard",
}


def fetch_profile(user_id, access_token):
    """Read this user's own row from public.profiles. Returns dict or None."""
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles",
            params={
                "id": f"eq.{user_id}",
                "select": "id,role,is_active,can_register_farmers,must_change_password",
            },
            headers={
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    except requests.exceptions.RequestException:
        pass
    return None


def authenticate(email, password):
    """Check email/password with Supabase and load the profile.

    Returns (user_dict, None) on success or (None, error_message).
    """
    if not email or not password:
        return None, "Please enter your email and password."

    try:
        resp = requests.post(
            f"{SUPABASE_URL}/auth/v1/token",
            params={"grant_type": "password"},
            headers={"apikey": SUPABASE_KEY},
            json={"email": email, "password": password},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return None, "Could not reach the server. Please try again."

    if resp.status_code != 200:
        return None, "Invalid email or password."

    data = resp.json()
    auth_user = data.get("user") or {}
    profile = fetch_profile(auth_user.get("id"), data.get("access_token"))

    if profile is None:
        return None, "Your account is not set up yet. Contact the administrator."
    if not profile["is_active"]:
        return None, "Your account is inactive. Contact the administrator."
    if profile["role"] not in DASHBOARDS:
        return None, "Access denied."

    return {
        "id": profile["id"],
        "email": auth_user.get("email"),
        "role": profile["role"],
        "can_register_farmers": profile["can_register_farmers"],
        "must_change_password": profile["must_change_password"],
    }, None


def role_required(*roles, login_endpoint="login"):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = session.get("user")
            if not user:
                return redirect(url_for(login_endpoint))
            if user.get("role") not in roles:
                return redirect(url_for(login_endpoint))
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/service-worker.js")
def service_worker():
    response = send_from_directory("static", "service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


def normalize_liberian_phone(phone):
    """Convert valid Liberian phone numbers to local 10-digit format."""
    import re

    digits = re.sub(r"\D", "", phone or "")

    if len(digits) == 12 and digits.startswith("231"):
        return "0" + digits[3:]

    if len(digits) == 10 and digits.startswith("0"):
        return digits

    return None


def find_registered_farmer_by_phone(phone):
    """Find exactly one registered farmer using their normalized phone."""
    local_phone = normalize_liberian_phone(phone)
    if not local_phone:
        return "invalid", None

    headers = service_headers()
    if not headers:
        return "unavailable", None

    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers=headers,
            params={
                "phone_number": f"eq.{local_phone}",
                "is_archived": "eq.false",
                "select": "id,county,district,community",
                "limit": 2,
            },
            timeout=10,
        )

        if response.status_code != 200:
            return "unavailable", None

        farmers = response.json()

        if len(farmers) == 0:
            return "not_found", None

        if len(farmers) > 1:
            return "ambiguous", None

        return "found", farmers[0]

    except (requests.exceptions.RequestException, ValueError, KeyError):
        return "unavailable", None


@app.route("/ussd", methods=["POST"])
def ussd_callback():
    """Receive USSD requests from Africa's Talking."""
    phone_number = (request.form.get("phoneNumber") or "").strip()

    if not phone_number:
        message = "END Unable to identify your phone number."
    else:
        status, farmer = find_registered_farmer_by_phone(phone_number)

        if status == "found":
            text = (request.form.get("text") or "").strip()

            if text == "":
                message = (
                    "CON Welcome to AgriDoc Liberia\n"
                    "1. Submit farm information\n"
                    "2. Report a farming problem\n"
                    "3. Request agricultural assistance\n"
                    "4. Check my submissions\n"
                    "5. Agricultural information\n"
                    "6. Update contact information\n"
                    "0. Exit"
                )

            elif text == "1":
                message = (
                    "CON What crops are you growing?\n"
                    "Example: Rice, Cassava, Maize"
                )

            elif text.startswith("1*"):
                crops = text[2:].strip()

                if not crops:
                    message = (
                        "CON Please enter the crops you are growing.\n"
                        "Example: Rice, Cassava, Maize"
                    )
                elif len(crops) > 200:
                    message = "END Your crop list is too long. Please try again with a shorter list."
                elif create_farmer_crop_report(farmer, crop_type=crops):
                    message = (
                        "END Thank you. Your crop information has been submitted "
                        "and is awaiting verification."
                    )
                else:
                    message = "END We could not save your information. Please try again later."

            elif text == "0":
                message = "END Thank you for using AgriDoc Liberia."

            elif text in {"2", "3", "4", "5", "6"}:
                message = "END This service is being prepared. Please try again later."

            else:
                message = "END Invalid selection. Please try again."

        elif status == "not_found":
            message = "END This phone number is not registered with AgriDoc. Please contact a Field Officer."
        elif status == "ambiguous":
            message = "END We could not verify your registration. Please contact an AgriDoc administrator."
        elif status == "invalid":
            message = "END Invalid phone number format."
        else:
            message = "END AgriDoc is temporarily unavailable. Please try again later."

    return message, 200, {
        "Content-Type": "text/plain; charset=utf-8"
    }

csrf.exempt(ussd_callback)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Staff (field officer) login."""
    error = None
    if request.method == "POST":
        user, error = authenticate(
            (request.form.get("email") or "").strip(),
            request.form.get("password") or "",
        )
        if user and user["role"] != "field_officer":
            user, error = None, "Administrators sign in at the admin login page."
        if user:
            session.clear()
            session["user"] = user
            return redirect(url_for("field_officer_dashboard"))
    return render_template("login.html", error=error)


@app.route("/forgot-password")
def forgot_password():
    """Explain the administrator-assisted password recovery process."""
    return render_template("forgot_password.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    """Administrator login."""
    error = None
    if request.method == "POST":
        user, error = authenticate(
            (request.form.get("email") or "").strip(),
            request.form.get("password") or "",
        )
        if user and user["role"] != "admin":
            user, error = None, "This page is for administrators only."
        if user:
            session.clear()
            session["user"] = user
            return redirect(url_for("admin_dashboard"))
    return render_template("admin/login.html", error=error)


@app.route("/admin")
def admin_root():
    return redirect(url_for("admin_dashboard" if (session.get("user") or {}).get("role") == "admin" else "admin_login"))


@app.route("/logout")
def logout():
    was_admin = (session.get("user") or {}).get("role") == "admin"
    session.clear()
    return redirect(url_for("admin_login" if was_admin else "index"))


@app.route("/admin/dashboard")
@role_required("admin", login_endpoint="admin_login")
def admin_dashboard():
    h = service_headers()
    county_stats = fetch_county_farmer_stats() if h else None
    district_stats = fetch_district_farmer_stats() if h else None

    return render_template(
        "admin/farmer_map.html",
        user=session.get("user"),
        county_stats=county_stats,
        district_stats=district_stats,
    )


@app.route("/admin/farmer-map")
@role_required("admin", login_endpoint="admin_login")
def admin_farmer_map():
    h = service_headers()
    county_stats = fetch_county_farmer_stats() if h else None
    district_stats = fetch_district_farmer_stats() if h else None

    return render_template(
        "admin/farmer_map.html",
        user=session.get("user"),
        county_stats=county_stats,
        district_stats=district_stats,
    )


@app.route("/admin/archived-farmers")
@role_required("admin", login_endpoint="admin_login")
def admin_archived_farmers():
    search_term = request.args.get("search", "").strip()

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    per_page = 20
    total_count = count_farmers_search(
        search_term or None,
        include_archived=True,
    )
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)

    farmers, error = fetch_farmer_records(
        page=page,
        search_term=search_term or None,
        per_page=per_page,
        include_error=True,
        include_archived=True,
    )

    return render_template(
        "admin/archived_farmers.html",
        user=session.get("user"),
        farmers=farmers,
        search_term=search_term,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        error=error,
    )


@app.route("/admin/farmers/<farmer_uuid>/archive", methods=["POST"])
@role_required("admin", login_endpoint="admin_login")
def admin_archive_farmer(farmer_uuid):
    h = service_headers()
    if not h:
        flash("Database service key is not configured.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers={**h, "Prefer": "return=representation"},
            params={
                "id": f"eq.{farmer_uuid}",
                "is_archived": "eq.false",
            },
            json={
                "is_archived": True,
                "archived_at": datetime.now(timezone.utc).isoformat(),
                "archived_by": session["user"]["id"],
            },
            timeout=10,
        )

        if resp.status_code == 200 and resp.json():
            flash("Farmer record archived successfully.", "ok")
        elif resp.status_code == 200:
            flash("Farmer record was not found or is already archived.", "error")
        else:
            app.logger.error(
                "Farmer archive failed: HTTP %s - %s",
                resp.status_code,
                resp.text[:500],
            )
            flash("Could not archive this farmer. Please try again.", "error")

    except requests.exceptions.RequestException:
        app.logger.exception("Could not connect to Supabase while archiving farmer.")
        flash("Could not reach the database. Please try again.", "error")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/farmers/<farmer_uuid>/restore", methods=["POST"])
@role_required("admin", login_endpoint="admin_login")
def admin_restore_farmer(farmer_uuid):
    h = service_headers()
    if not h:
        flash("Database service key is not configured.", "error")
        return redirect(url_for("admin_archived_farmers"))

    try:
        resp = requests.patch(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers={**h, "Prefer": "return=representation"},
            params={
                "id": f"eq.{farmer_uuid}",
                "is_archived": "eq.true",
            },
            json={
                "is_archived": False,
                "archived_at": None,
                "archived_by": None,
            },
            timeout=10,
        )

        if resp.status_code == 200 and resp.json():
            flash("Farmer record restored to the active registry.", "ok")
        elif resp.status_code == 200:
            flash("Farmer record was not found or is already active.", "error")
        else:
            app.logger.error(
                "Farmer restore failed: HTTP %s - %s",
                resp.status_code,
                resp.text[:500],
            )
            flash("Could not restore this farmer. Please try again.", "error")

    except requests.exceptions.RequestException:
        app.logger.exception("Could not connect to Supabase while restoring farmer.")
        flash("Could not reach the database. Please try again.", "error")

    return redirect(url_for("admin_archived_farmers"))


@app.route("/admin/farm-performance")
@role_required("admin", login_endpoint="admin_login")
def admin_farm_performance():
    county_stats = fetch_county_farmer_stats()
    return render_template(
        "admin/farm_performance.html",
        user=session.get("user"),
        county_stats=county_stats,
    )



@app.route("/admin/aid-requests")
@role_required("admin", login_endpoint="admin_login")
def admin_aid_requests():
    return render_template(
        "admin/aid_requests.html",
        user=session.get("user"),
    )


@app.route("/field-officer/dashboard")
@role_required("field_officer")
def field_officer_dashboard():
    user = session["user"]
    farmers, farmer_error = fetch_farmer_records(
        page=1,
        per_page=100,
        registered_by=user["id"],
        include_error=True,
    )

    return render_template(
        "field_officer/dashboard.html",
        user=user,
        farmers=farmers,
        farmer_error=farmer_error,
        title="Field Officer Dashboard",
    )


@app.route("/field-officer/register-farmer", methods=["GET", "POST"])
@role_required("field_officer")
def register_farmer():
    user = session.get("user")
    if not user or not user.get("can_register_farmers"):
        flash("You don't have permission to register farmers.", "error")
        return redirect(url_for("field_officer_dashboard"))
    
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        county = (request.form.get("county") or "").strip()
        district = (request.form.get("district") or "").strip()
        community = (request.form.get("community") or "").strip()
        age = request.form.get("age")
        tribe = (request.form.get("tribe") or "").strip()
        
        # Validate required fields
        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not phone:
            errors.append("Phone number is required.")
        if not county:
            errors.append("County is required.")
        if not district:
            errors.append("District is required.")
        if not community:
            errors.append("Community is required.")
        
        # Validate age if provided
        if age is not None and age != "":
            try:
                age_int = int(age)
                if age_int < 0 or age_int > 120:
                    errors.append("Age must be between 0 and 120.")
            except ValueError:
                errors.append("Age must be a valid integer.")
        
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("field_officer/register_farmer.html", user=user)
        
        # Save to Supabase - verify officer profile first
        h = service_headers()
        if not h:
            flash("SUPABASE_SERVICE_KEY is missing in .env", "error")
            return redirect(url_for("field_officer_dashboard"))
        
        # Verify the officer's profile from Supabase
        try:
            profile_resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/profiles",
                headers=h,
                params={"id": f"eq.{user['id']}", "select": "id,role,is_active,can_register_farmers"},
                timeout=10,
            )
            if profile_resp.status_code != 200:
                flash("Could not verify your profile. Please try again.", "error")
                return redirect(url_for("field_officer_dashboard"))
            
            profile_rows = profile_resp.json()
            if not profile_rows:
                flash("Your profile could not be found. Contact the administrator.", "error")
                return redirect(url_for("field_officer_dashboard"))
            
            profile = profile_rows[0]
            
            # Verify profile is active, has correct role, and can register farmers
            if profile.get("role") != "field_officer":
                flash("Access denied. Your role is not permitted.", "error")
                return redirect(url_for("field_officer_dashboard"))
            if not profile.get("is_active", False):
                flash("Your account is inactive. Contact the administrator.", "error")
                return redirect(url_for("field_officer_dashboard"))
            if not profile.get("can_register_farmers", False):
                flash("You don't have permission to register farmers.", "error")
                return redirect(url_for("field_officer_dashboard"))
            
            # Use the verified profile ID for the registered_by field
            verified_user_id = profile["id"]
        except requests.exceptions.RequestException:
            flash("Could not reach the server. Please try again.", "error")
            return redirect(url_for("field_officer_dashboard"))
        
        try:
            # Insert farmer record with registered_by set to the verified field officer's profile ID
            p = requests.post(
                f"{SUPABASE_URL}/rest/v1/farmers",
                headers={**h, "Prefer": "return=minimal"},
                timeout=15,
                json={
                    "full_name": full_name,
                    "phone_number": phone,
                    "county": county,
                    "district": district,
                    "community": community,
                    "age": int(age) if age else None,
                    "tribe": tribe,
                    "registered_by": verified_user_id,
                },
            )
            if p.status_code in (200, 201):
                flash(f"Farmer {full_name} registered successfully.", "ok")
            else:
                flash("Could not register the farmer. Please try again.", "error")
        except requests.exceptions.RequestException:
            flash("Could not reach the server. Please try again.", "error")
        
        return redirect(url_for("field_officer_dashboard"))
    
    return render_template("field_officer/register_farmer.html", user=user)



@app.route("/field-officer/farmers/<farmer_uuid>/edit", methods=["GET", "POST"])
@role_required("field_officer")
def edit_farmer(farmer_uuid):
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    h = service_headers()
    if not h:
        flash("Server configuration error.", "error")
        return redirect(url_for("field_officer_dashboard"))

    try:
        profile_resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles",
            headers=h,
            params={
                "id": f"eq.{user['id']}",
                "select": "id,role,is_active,can_register_farmers",
            },
            timeout=10,
        )

        if profile_resp.status_code != 200:
            flash("Could not verify your account.", "error")
            return redirect(url_for("field_officer_dashboard"))

        profiles = profile_resp.json()
        if not profiles:
            flash("Profile not found.", "error")
            return redirect(url_for("field_officer_dashboard"))

        profile = profiles[0]
        if (
            profile.get("role") != "field_officer"
            or not profile.get("is_active")
            or not profile.get("can_register_farmers")
        ):
            flash("You are not permitted to edit farmer records.", "error")
            return redirect(url_for("field_officer_dashboard"))

        officer_id = profile["id"]

        farmer_resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers=h,
            params={
                "id": f"eq.{farmer_uuid}",
                "registered_by": f"eq.{officer_id}",
                "select": "id,farmer_id,full_name,phone_number,age,county,district,community,tribe",
            },
            timeout=10,
        )

        if farmer_resp.status_code != 200:
            flash("Could not load farmer record.", "error")
            return redirect(url_for("field_officer_dashboard"))

        rows = farmer_resp.json()
        if not rows:
            flash("Farmer not found or you cannot edit this record.", "error")
            return redirect(url_for("field_officer_dashboard"))

        farmer = rows[0]

    except requests.exceptions.RequestException:
        flash("Could not reach the server.", "error")
        return redirect(url_for("field_officer_dashboard"))

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        county = (request.form.get("county") or "").strip()
        district = (request.form.get("district") or "").strip()
        community = (request.form.get("community") or "").strip()
        age = (request.form.get("age") or "").strip()
        tribe = (request.form.get("tribe") or "").strip()

        errors = []
        for value, message in [
            (full_name, "Full name is required."),
            (phone, "Phone number is required."),
            (county, "County is required."),
            (district, "District is required."),
            (community, "Community is required."),
        ]:
            if not value:
                errors.append(message)

        age_value = None
        if age:
            try:
                age_value = int(age)
                if not 0 <= age_value <= 120:
                    errors.append("Age must be between 0 and 120.")
            except ValueError:
                errors.append("Age must be a valid integer.")

        if errors:
            for error in errors:
                flash(error, "error")
            farmer.update({
                "full_name": full_name,
                "phone_number": phone,
                "age": age,
                "county": county,
                "district": district,
                "community": community,
                "tribe": tribe,
            })
            return render_template(
                "field_officer/edit_farmer.html",
                user=user,
                farmer=farmer,
            )

        try:
            update = requests.patch(
                f"{SUPABASE_URL}/rest/v1/farmers",
                headers={**h, "Prefer": "return=representation"},
                params={
                    "id": f"eq.{farmer_uuid}",
                    "registered_by": f"eq.{officer_id}",
                    "select": "id",
                },
                json={
                    "full_name": full_name,
                    "phone_number": phone,
                    "age": age_value,
                    "county": county,
                    "district": district,
                    "community": community,
                    "tribe": tribe,
                },
                timeout=15,
            )

            if update.status_code in (200, 204) and (
                update.status_code == 204 or update.json()
            ):
                flash("Farmer record updated successfully.", "ok")
            else:
                flash("Could not update farmer. Please try again.", "error")

        except requests.exceptions.RequestException:
            flash("Could not reach the server.", "error")

        return redirect(url_for("field_officer_dashboard"))

    return render_template(
        "field_officer/edit_farmer.html",
        user=user,
        farmer=farmer,
    )


def service_headers():
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not key:
        return None
    return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def create_farmer_crop_report(farmer, crop_type, farm_size=None, farm_size_unit=None, activity=None):
    """Save a farmer's USSD crop report using their registered location."""
    headers = service_headers()
    if not headers:
        return False

    payload = {
        "farmer_id": farmer["id"],
        "crop_type": crop_type,
        "farm_size": farm_size,
        "farm_size_unit": farm_size_unit,
        "activity": activity or None,
        "county": farmer["county"],
        "district": farmer["district"],
        "community": farmer["community"],
        "status": "pending",
        "source": "ussd",
    }

    try:
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/farmer_crop_reports",
            headers={**headers, "Prefer": "return=minimal"},
            json=payload,
            timeout=10,
        )
        return response.status_code == 201
    except requests.exceptions.RequestException:
        return False


def fetch_farmer_stats():
    """Fetch farmer registration statistics from Supabase.
    
    Returns dict with total_farmers, active_farmers (if applicable).
    Returns None if service key is missing or on error.
    """
    h = service_headers()
    if not h:
        return None
    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers=h,
            params={"select": "id", "count": "true"},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"total_farmers": resp.json().get("count", 0)}
    except requests.exceptions.RequestException:
        pass
    return None



LIBERIA_COUNTIES = [
    "Bomi", "Bong", "Gbarpolu", "Grand Bassa", "Grand Cape Mount",
    "Grand Gedeh", "Grand Kru", "Lofa", "Margibi", "Maryland",
    "Montserrado", "Nimba", "River Cess", "River Gee", "Sinoe",
]


def fetch_county_farmer_stats():
    """Count registered farmers by county, including counties with zero."""
    h = service_headers()
    if not h:
        return None

    counts = {county: 0 for county in LIBERIA_COUNTIES}
    offset = 0
    page_size = 1000

    try:
        while True:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/farmers",
                headers=h,
                params={
                    "select": "county",
                    "limit": page_size,
                    "offset": offset,
                    "order": "id.asc",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                app.logger.error(
                    "County statistics request failed: HTTP %s",
                    resp.status_code,
                )
                return None

            records = resp.json()
            for record in records:
                value = (record.get("county") or "").strip().casefold()
                if value == "rivercess":
                    value = "river cess"

                for county in LIBERIA_COUNTIES:
                    if value == county.casefold():
                        counts[county] += 1
                        break

            if len(records) < page_size:
                break
            offset += page_size

    except (requests.exceptions.RequestException, ValueError):
        app.logger.exception("Could not calculate county farmer statistics")
        return None

    total = sum(counts.values())
    return [
        {
            "county": county,
            "farmer_count": counts[county],
            "percentage": round(counts[county] * 100 / total, 1) if total else 0,
        }
        for county in LIBERIA_COUNTIES
    ]



def fetch_district_farmer_stats():
    """Count registered farmers by county and district."""
    h = service_headers()
    if not h:
        return None

    counts = {}
    offset = 0
    page_size = 1000

    try:
        while True:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/farmers",
                headers=h,
                params={
                    "select": "county,district",
                    "limit": page_size,
                    "offset": offset,
                    "order": "id.asc",
                },
                timeout=15,
            )

            if resp.status_code != 200:
                app.logger.error(
                    "District statistics request failed: HTTP %s",
                    resp.status_code,
                )
                return None

            records = resp.json()

            for record in records:
                county = (record.get("county") or "").strip()
                district = (record.get("district") or "").strip()

                if not county or not district:
                    continue

                if county.casefold() == "rivercess":
                    county = "River Cess"

                key = (county.casefold(), district.casefold())

                if key not in counts:
                    counts[key] = {
                        "county": county,
                        "district": district,
                        "farmer_count": 0,
                    }

                counts[key]["farmer_count"] += 1

            if len(records) < page_size:
                break

            offset += page_size

    except (requests.exceptions.RequestException, ValueError):
        app.logger.exception(
            "Could not calculate district farmer statistics"
        )
        return None

    return list(counts.values())


def fetch_farmer_records(
    page=1,
    search_term=None,
    per_page=20,
    registered_by=None,
    include_error=False,
    include_archived=False,
):
    """Fetch active or archived farmer records."""
    h = service_headers()
    if not h:
        result = ([], "Database service key is not configured.")
        return result if include_error else result[0]

    params = {
        "select": "id,farmer_id,full_name,county,district,community,registered_by,created_at",
        "is_archived": f"eq.{str(bool(include_archived)).lower()}",
        "order": "created_at.desc",
        "limit": per_page,
        "offset": (page - 1) * per_page,
    }

    if registered_by:
        params["registered_by"] = f"eq.{registered_by}"

    if search_term:
        term = search_term.replace(",", "").replace("(", "").replace(")", "")
        params["or"] = f"(farmer_id.ilike.*{term}*,full_name.ilike.*{term}*)"

    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers=h,
            params=params,
            timeout=10,
        )

        if resp.status_code == 200:
            farmers = resp.json()

            officer_ids = sorted({
                farmer["registered_by"]
                for farmer in farmers
                if farmer.get("registered_by")
            })

            officer_names = {}
            if officer_ids:
                profiles_response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/profiles",
                    headers=h,
                    params={
                        "select": "id,full_name",
                        "id": f"in.({','.join(officer_ids)})",
                    },
                    timeout=10,
                )

                if profiles_response.status_code == 200:
                    officer_names = {
                        profile["id"]: profile.get("full_name")
                        for profile in profiles_response.json()
                    }
                else:
                    app.logger.error(
                        "Officer name lookup failed: HTTP %s",
                        profiles_response.status_code,
                    )

            for farmer in farmers:
                officer_id = farmer.get("registered_by")
                farmer["registered_by_name"] = (
                    officer_names.get(officer_id) or "Name unavailable"
                )

            result = (farmers, None)
        else:
            app.logger.error(
                "Farmer query failed: HTTP %s - %s",
                resp.status_code,
                resp.text[:500],
            )
            result = ([], "Could not load farmer records. Please try again.")

    except requests.exceptions.RequestException:
        app.logger.exception("Could not connect to Supabase while fetching farmers.")
        result = ([], "Could not connect to the database. Please try again.")

    return result if include_error else result[0]


def count_farmers_search(search_term=None, include_archived=False):
    """Count active or archived farmers matching an optional search term."""
    h = service_headers()
    if not h:
        return 0

    params = {
        "select": "id",
        "is_archived": f"eq.{str(bool(include_archived)).lower()}",
    }

    if search_term:
        term = search_term.replace(",", "").replace("(", "").replace(")", "")
        params["or"] = f"(farmer_id.ilike.*{term}*,full_name.ilike.*{term}*)"

    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/farmers",
            headers={**h, "Prefer": "count=exact"},
            params=params,
            timeout=10,
        )
        if resp.status_code == 200:
            content_range = resp.headers.get("Content-Range", "")
            if "/" in content_range:
                total = content_range.rsplit("/", 1)[1]
                if total.isdigit():
                    return int(total)

            return len(resp.json())
    except requests.exceptions.RequestException:
        app.logger.exception("Could not count farmer records.")

    return 0


def fetch_agricultural_report_stats():
    """Fetch agricultural report counts; return None on errors."""
    h = service_headers()
    if not h:
        return None

    try:
        resp = requests.get(
            f"{SUPABASE_URL}/rest/v1/agricultural_reports",
            headers=h,
            params={"select": "id,status,report_type"},
            timeout=10,
        )
        if resp.status_code != 200:
            app.logger.error(
                "Could not fetch agricultural reports: HTTP %s",
                resp.status_code,
            )
            return None

        reports = resp.json()
        stats = {
            "total_reports": len(reports),
            "pending_reports": 0,
            "under_review_reports": 0,
            "verified_reports": 0,
            "dismissed_reports": 0,
            "pest_disease_reports": 0,
        }

        for report in reports:
            status = report.get("status")
            if status in ("pending", "under_review", "verified", "dismissed"):
                stats[f"{status}_reports"] += 1
            if report.get("report_type") in ("pest", "disease"):
                stats["pest_disease_reports"] += 1

        return stats
    except (requests.exceptions.RequestException, ValueError):
        app.logger.exception("Error fetching agricultural report statistics")
        return None


@app.route("/admin/officers", methods=["GET", "POST"])
@role_required("admin", login_endpoint="admin_login")
def admin_officers():
    h = service_headers()
    if not h:
        flash("SUPABASE_SERVICE_KEY is missing in .env", "error")
        return render_template("admin/officers.html", officers=[], user=session["user"])

    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        phone_number = (request.form.get("phone_number") or "").strip()
        password = request.form.get("password") or ""
        can_register = request.form.get("can_register") == "on"

        if not full_name or not email or not phone_number or len(password) < 8:
            flash("Enter full name, email, phone number, and a password of at least 8 characters.", "error")
            return redirect(url_for("admin_officers"))

        uid = None
        try:
            r = requests.post(
                f"{SUPABASE_URL}/auth/v1/admin/users",
                headers=h,
                timeout=15,
                json={"email": email, "password": password, "email_confirm": True},
            )
            if r.status_code not in (200, 201):
                flash("Could not create the account. The email may already exist.", "error")
                return redirect(url_for("admin_officers"))

            uid = r.json()["id"]
            p = requests.post(
                f"{SUPABASE_URL}/rest/v1/profiles",
                headers={**h, "Prefer": "return=minimal"},
                timeout=15,
                json={
                    "id": uid,
                    "role": "field_officer",
                    "is_active": True,
                    "can_register_farmers": can_register,
                    "full_name": full_name,
                    "phone_number": phone_number,
                    "must_change_password": True,
                },
            )

            if p.status_code not in (200, 201, 204):
                try:
                    requests.delete(
                        f"{SUPABASE_URL}/auth/v1/admin/users/{uid}",
                        headers=h,
                        timeout=15,
                    )
                except requests.exceptions.RequestException:
                    app.logger.exception("Could not clean up incomplete officer account")
                flash("Could not save the officer profile. Please check the database and try again.", "error")
            else:
                flash(f"Field officer {full_name} created. They must change their temporary password.", "ok")

        except requests.exceptions.RequestException:
            app.logger.exception("Network error during officer account creation")
            if uid:
                try:
                    requests.delete(
                        f"{SUPABASE_URL}/auth/v1/admin/users/{uid}",
                        headers=h,
                        timeout=15,
                    )
                except requests.exceptions.RequestException:
                    app.logger.exception("Could not clean up incomplete officer account")
            flash("Could not complete the request. Please try again.", "error")
        except (ValueError, KeyError):
            app.logger.exception("Unexpected response creating officer account")
            flash("Could not complete account creation. Please try again.", "error")

        return redirect(url_for("admin_officers"))

    officers = []
    try:
        pr = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles",
            headers=h,
            timeout=15,
            params={
                "role": "eq.field_officer",
                "select": "id,full_name,phone_number,is_active,can_register_farmers,must_change_password,created_at",
                "order": "created_at.desc",
            },
        )
        ur = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=h,
            timeout=15,
            params={"per_page": 200},
        )

        if ur.status_code != 200:
            flash("Could not load account emails from Supabase Auth.", "error")
        if pr.status_code == 200:
            emails = {
                u["id"]: u.get("email")
                for u in ur.json().get("users", [])
                if u.get("id")
            } if ur.status_code == 200 else {}
            officers = [
                {**o, "email": emails.get(o["id"], "(unknown)")}
                for o in pr.json()
            ]
        else:
            flash("Could not load field officers.", "error")

    except requests.exceptions.RequestException:
        app.logger.exception("Error loading field officers")
        flash("Could not load officers. Please try again.", "error")

    return render_template("admin/officers.html", officers=officers, user=session["user"])


@app.route("/admin/officers/<officer_id>/edit", methods=["GET", "POST"])
@role_required("admin", login_endpoint="admin_login")
def admin_officer_edit(officer_id):
    h = service_headers()
    if not h:
        flash("SUPABASE_SERVICE_KEY is missing in .env", "error")
        return redirect(url_for("admin_officers"))

    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles",
            headers=h,
            params={
                "id": f"eq.{officer_id}",
                "role": "eq.field_officer",
                "select": "id,full_name,phone_number,is_active,can_register_farmers",
            },
            timeout=15,
        )

        if response.status_code != 200 or not response.json():
            flash("Field officer not found.", "error")
            return redirect(url_for("admin_officers"))

        officer = response.json()[0]

        users_response = requests.get(
            f"{SUPABASE_URL}/auth/v1/admin/users",
            headers=h,
            params={"per_page": 200},
            timeout=15,
        )
        email = ""
        if users_response.status_code == 200:
            email = next(
                (
                    item.get("email", "")
                    for item in users_response.json().get("users", [])
                    if item.get("id") == officer_id
                ),
                "",
            )

        officer["email"] = email

        if request.method == "POST":
            full_name = (request.form.get("full_name") or "").strip()
            phone_number = (request.form.get("phone_number") or "").strip()
            new_email = (request.form.get("email") or "").strip()
            can_register = request.form.get("can_register") == "on"

            if not full_name or not phone_number or not new_email:
                flash("Name, phone number, and email are required.", "error")
                return render_template(
                    "admin/officer_edit.html",
                    officer={**officer, "full_name": full_name,
                             "phone_number": phone_number, "email": new_email},
                    user=session["user"],
                )

            if new_email != email:
                email_response = requests.put(
                    f"{SUPABASE_URL}/auth/v1/admin/users/{officer_id}",
                    headers=h,
                    json={"email": new_email, "email_confirm": True},
                    timeout=15,
                )
                if email_response.status_code not in (200, 201):
                    flash("Could not update the login email. Other details were not saved.", "error")
                    return redirect(url_for("admin_officer_edit", officer_id=officer_id))

            update_response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/profiles",
                headers={**h, "Prefer": "return=minimal"},
                params={
                    "id": f"eq.{officer_id}",
                    "role": "eq.field_officer",
                },
                json={
                    "full_name": full_name,
                    "phone_number": phone_number,
                    "can_register_farmers": can_register,
                },
                timeout=15,
            )

            if update_response.status_code not in (200, 204):
                flash("Could not save the officer details. Please try again.", "error")
                return redirect(url_for("admin_officer_edit", officer_id=officer_id))

            flash("Field officer details updated.", "ok")
            return redirect(url_for("admin_officers"))

        return render_template(
            "admin/officer_edit.html",
            officer=officer,
            user=session["user"],
        )

    except requests.exceptions.RequestException:
        app.logger.exception("Error editing field officer")
        flash("Could not reach the server. Please try again.", "error")
        return redirect(url_for("admin_officers"))


@app.route("/admin/officers/<officer_id>/reset-password", methods=["GET", "POST"])
@role_required("admin", login_endpoint="admin_login")
def admin_officer_reset_password(officer_id):
    h = service_headers()
    if not h:
        flash("SUPABASE_SERVICE_KEY is missing in .env", "error")
        return redirect(url_for("admin_officers"))

    try:
        profile_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/profiles",
            headers=h,
            params={
                "id": f"eq.{officer_id}",
                "role": "eq.field_officer",
                "select": "id,full_name,phone_number,is_active,must_change_password",
            },
            timeout=15,
        )

        if profile_response.status_code != 200 or not profile_response.json():
            flash("Field officer not found.", "error")
            return redirect(url_for("admin_officers"))

        officer = profile_response.json()[0]

        if request.method == "POST":
            password = request.form.get("password") or ""
            confirm_password = request.form.get("confirm_password") or ""

            if len(password) < 8:
                flash("The temporary password must be at least 8 characters.", "error")
            elif password != confirm_password:
                flash("The passwords do not match.", "error")
            else:
                reset_response = requests.put(
                    f"{SUPABASE_URL}/auth/v1/admin/users/{officer_id}",
                    headers=h,
                    json={"password": password},
                    timeout=15,
                )

                if reset_response.status_code not in (200, 201):
                    app.logger.error(
                        "Supabase password reset failed: HTTP %s",
                        reset_response.status_code,
                    )
                    flash("Could not reset the password. Please try again.", "error")
                else:
                    profile_update = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/profiles",
                        headers={**h, "Prefer": "return=minimal"},
                        params={
                            "id": f"eq.{officer_id}",
                            "role": "eq.field_officer",
                        },
                        json={"must_change_password": True},
                        timeout=15,
                    )

                    if profile_update.status_code not in (200, 204):
                        app.logger.error(
                            "Password changed but must_change_password could not be set: HTTP %s",
                            profile_update.status_code,
                        )
                        flash(
                            "Password was reset, but the forced-change flag could not be saved. "
                            "Please correct the profile before the officer signs in.",
                            "error",
                        )
                    else:
                        flash(
                            "Temporary password set. The officer must change it after signing in.",
                            "ok",
                        )
                        return redirect(url_for("admin_officers"))

        return render_template(
            "admin/officer_reset_password.html",
            officer=officer,
            user=session["user"],
        )

    except requests.exceptions.RequestException:
        app.logger.exception("Error resetting field officer password")
        flash("Could not reach the server. Please try again.", "error")
        return redirect(url_for("admin_officers"))


@app.route("/admin/officers/<officer_id>/active", methods=["POST"])
@role_required("admin", login_endpoint="admin_login")
def admin_officer_active(officer_id):
    h = service_headers()
    if h:
        try:
            requests.patch(f"{SUPABASE_URL}/rest/v1/profiles", headers={**h, "Prefer": "return=minimal"}, timeout=15,
                           params={"id": f"eq.{officer_id}", "role": "eq.field_officer"},
                           json={"is_active": request.form.get("active") == "1"})
        except requests.exceptions.RequestException:
            flash("Could not update the officer.", "error")
    return redirect(url_for("admin_officers"))




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
