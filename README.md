# AgriDoc Liberia

A web-based agricultural management system designed for Liberia's Ministry of Agriculture.

AgriDoc Liberia aims to provide a centralized system for farmer registration and agricultural data management. Development is being carried out incrementally, with a focus on simplicity, security, and maintainability.

## Table of Contents

- [Project Overview](#project-overview)
- [Current MVP Scope](#current-mvp-scope)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Database and Migrations](#database-and-migrations)
- [Authentication and Authorization](#authentication-and-authorization)
- [Frontend JavaScript](#frontend-javascript)
- [Security Guidelines](#security-guidelines)
- [Testing and Validation](#testing-and-validation)
- [Development Workflow](#development-workflow)
- [Current Development Status](#current-development-status)
- [Future Scope](#future-scope)

## Project Overview

AgriDoc Liberia is intended to support the digitization of farmer registration and agricultural administration in Liberia.

The initial goal is to establish a central farmer registry with controlled access for administrators and field officers.

The project is being developed as a small, maintainable application rather than implementing every planned agricultural feature at once.

## Current MVP Scope

The initial workflow focuses on three main responsibilities.

### Administrators

- Sign in to the application.
- Manage field officer access and permissions as the corresponding features are implemented.
- Control whether field officers are active and permitted to register farmers.

### Field Officers

- Sign in using their assigned accounts.
- Register farmers when their accounts are active and registration permission is enabled.
- Submit farmer information through the registration interface.
- Provide farmer photographs through the registration form where supported.

### Central Farmer Registry

- Store farmer records in Supabase PostgreSQL.
- Generate unique farmer identifiers in the intended `AGL-000001` format.
- Record which field officer registered each farmer.

The database design documents additional modules, but those modules are not automatically considered implemented simply because they appear in the design.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python and Flask |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth integration |
| Frontend | HTML, CSS, JavaScript |
| CSRF protection | Flask-SeaSurf |
| Configuration | Environment variables and python-dotenv |
| Development environment | Kali Linux and Visual Studio Code |
| AI-assisted development | Cline |

## Project Structure

The following is a simplified overview of important project files. Other files and templates may exist in the repository.

```text
agridoc-liberia/
├── app.py
├── create_admin.py
├── requirements.txt
├── .gitignore
├── README.md
├── docs/
│   └── database-design.md
├── supabase/
│   └── migrations/
├── static/
│   └── js/
│       ├── admin-dashboard.js
│       ├── field-officer.js
│       ├── login.js
│       └── register-farmer.js
└── templates/
    ├── login.html
    ├── admin/
    │   ├── dashboard.html
    │   └── ...
    └── field_officer/
        └── register_farmer.html
```

### Important files

- `app.py`: Flask application, routes, session handling, and application logic.
- `create_admin.py`: Administrative account setup utility. Review its implementation before running it.
- `requirements.txt`: Python dependencies.
- `docs/database-design.md`: Planned database structure and module documentation.
- `supabase/migrations/`: SQL migration files for creating and modifying database objects.
- `templates/`: HTML templates rendered by Flask.
- `static/js/`: External JavaScript files used by the frontend.

## Prerequisites

Install or prepare the following before running the application:

- Python 3 and `venv`.
- Git.
- Node.js, if you want to run the JavaScript syntax checks.
- A Supabase project for database and authentication integration.
- Access to the project's repository.

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/onlineconnection/agridoc-liberia.git
cd agridoc-liberia
```

The repository is private, so GitHub access must be granted to your account.

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root using the variable names required by the current application.

See [Environment Variables](#environment-variables) below.

Never commit `.env` or paste secret values into public issues, chat messages, or source control.

### 5. Review database requirements

Read `docs/database-design.md` and inspect the SQL files in `supabase/migrations/` before applying any database changes.

**Do not run migrations against Supabase until their SQL has been reviewed.**

### 6. Start the Flask application

```bash
python app.py
```

Use the development URL printed by Flask, normally:

```text
http://127.0.0.1:5000
```

This is a local development setup, not a production deployment configuration.

## Environment Variables

The application uses environment variables for configuration and Supabase access.

Variable names referenced by the project include:

| Variable | Purpose |
|---|---|
| `FLASK_SECRET_KEY` | Signs Flask session data. |
| `SUPABASE_URL` | Supabase project URL. |
| `SUPABASE_PUBLISHABLE_KEY` | Public/publishable Supabase key used by the application. |
| `SUPABASE_SERVICE_KEY` | Privileged Supabase key used by administrative setup code where required. |

Check `app.py`, `create_admin.py`, and any related configuration code for the exact variables required by each command.

Do not put real credentials in this README.

The service-role key is highly privileged. It must remain server-side and must never be exposed in browser JavaScript or committed to Git.

Use a strong, unique `FLASK_SECRET_KEY` outside local development. Do not rely on a development fallback in production.

## Database and Migrations

Supabase provides the PostgreSQL database and authentication services.

The project includes migration files intended to establish database objects, including:

- `profiles`: application user roles, account status, and farmer-registration permission.
- `farmers`: farmer records and generated farmer identifiers.
- `farmer_id_seq`: sequence used by the farmer identifier generation logic.

The broader database design documents additional planned modules, including land holdings, assistance programs, crop reporting, complaints, audit logs, USSD, notifications, imports, exports, and reporting.

These modules are planned design scope and should not be treated as implemented unless the corresponding application code and database objects exist.

### Migration review checklist

Before applying a migration:

1. Read the entire SQL file.
2. Confirm the operations are intentional and non-destructive.
3. Check table dependencies and migration order.
4. Review Row Level Security (RLS) on every relevant table.
5. Review policies for least-privilege access.
6. Check foreign keys, UUID usage, constraints, and indexes.
7. Consider whether existing records or objects could be affected.
8. Test in a development Supabase project where possible.
9. Apply changes only after explicit review and approval.

Enabling RLS without appropriate policies can block legitimate requests. Policies must be designed and tested carefully; do not weaken access controls just to make a query work.

## Authentication and Authorization

The application includes Flask login and logout routes and integrates with Supabase Auth.

The intended access model distinguishes between administrators and field officers.

For farmer registration, the intended rule is that a field officer must have an active account and registration permission.

Authorization must be enforced on the server for every protected operation. Hiding a button or disabling a form in the browser is not an authorization control.

Review session handling, token refresh and expiration, account status checks, and database policies when extending authentication features.

## Frontend JavaScript

Inline JavaScript was extracted from the active templates into separate files to improve maintainability.

| File | Responsibility |
|---|---|
| `static/js/admin-dashboard.js` | Mobile admin sidebar navigation. |
| `static/js/field-officer.js` | Field officer navigation toggle. |
| `static/js/login.js` | Show/hide password input. |
| `static/js/register-farmer.js` | Farmer photo validation, preview, and compression. |

The relevant templates load these files using Flask's `url_for('static', ...)` helper.

When modifying frontend behavior, update the appropriate JavaScript file rather than adding another inline script. Keep changes small and test the affected page after each change.

## Security Guidelines

Security is part of the development process, not a final step.

- Keep secrets in environment variables, never in source code.
- Never commit `.env` files.
- Use HTTPS and secure cookie settings in production.
- Enable and correctly configure CSRF protection for applicable state-changing requests.
- Validate all user input on the server.
- Enforce authentication and authorization on the server.
- Use Supabase RLS and least-privilege policies for database access.
- Never expose the Supabase service-role key to the frontend.
- Review file uploads for type, size, and content risks.
- Avoid logging passwords, access tokens, refresh tokens, or other secrets.
- Rotate exposed credentials and revoke compromised keys.
- Review SQL migrations before applying them.
- Do not disable security controls merely to work around an error.

Development settings may differ from production settings. In particular, production cookies should use HTTPS and the secure-cookie option should be enabled.

## Testing and Validation

Run these checks from the project root after making changes.

### Python syntax

```bash
python -m py_compile app.py
```

### JavaScript syntax

If Node.js is installed:

```bash
for f in static/js/*.js; do
    node --check "$f" || exit 1
done
```

### Git whitespace validation

```bash
git diff --check
```

These checks are useful but do not replace functional testing.

Manually test the affected workflows, including login and logout, password visibility, the mobile navigation menu, farmer form validation, and photo preview/compression.

Test authorization with accounts that should and should not have permission to register farmers. Do not assume a feature is secure merely because its page renders correctly.

## Development Workflow

AgriDoc Liberia is developed incrementally.

Recommended workflow:

1. Inspect the existing code before making changes.
2. Choose one small, clearly defined task.
3. Make the smallest change that solves it.
4. Run relevant syntax and whitespace checks.
5. Test the affected feature.
6. Review the diff.
7. Commit the change with a descriptive message.
8. Push to GitHub after confirming the change is ready.

Useful Git commands:

```bash
git status
git diff
git diff --check
git log --oneline -5
```

Example commit workflow:

```bash
git add <files-you-reviewed>
git commit -m "Describe the change"
git push origin main
```

Only stage files that belong to the intended change.

## Current Development Status

The current development effort has focused on the initial Flask application, Supabase integration, login/session handling, farmer registration, and maintainable frontend structure.

The following JavaScript refactoring was committed and pushed to the `main` branch:

- Commit: `7adf067`
- Message: `Extract inline JavaScript into static files`

The commit moved JavaScript from three active templates into four external files under `static/js/`.

Python syntax, JavaScript syntax, and Git whitespace checks passed during that refactoring.

These checks confirm syntax and formatting only. They do not establish that every workflow has been tested end-to-end.

Before extending the system, verify the current application routes, database connection, Supabase policies, and end-to-end registration workflow in the development environment.

## Future Scope

The database design documents additional capabilities that may be developed later, including:

- Land and farm holding records.
- Agricultural assistance programs and deliveries.
- Crop reporting and inspections.
- Complaints and investigations.
- Audit logging.
- USSD support.
- Notifications.
- Data imports, exports, and reporting.

These should be introduced incrementally after the core farmer-registration workflow is stable and secure.

---

## Project Repository

GitHub: https://github.com/onlineconnection/agridoc-liberia.git

AgriDoc Liberia is an evolving project. Keep this README updated whenever the architecture, setup process, database schema, or implemented features change.
