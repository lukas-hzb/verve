# Verve Development Guide

This is the canonical reference for local development, testing, troubleshooting, and repository commands. Production hosting and database operations are documented separately in [DEPLOYMENT.md](DEPLOYMENT.md).

## Requirements

- Python 3.12
- Git
- A PostgreSQL database for interactive local development; the automated tests use SQLite

## Clone the Repository

```bash
git clone https://github.com/lukas-hzb/verve.git
cd verve
```

## Create a Virtual Environment

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

In Windows Command Prompt:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

In Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Use the same activated environment for all commands in this guide.

## Configure the Environment

Copy the committed template to `.env.local`.

On macOS or Linux:

```bash
cp .env.example .env.local
```

In Windows Command Prompt:

```bat
copy .env.example .env.local
```

In Windows PowerShell:

```powershell
Copy-Item .env.example .env.local
```

Generate a development secret with Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set these values in `.env.local`:

- `SECRET_KEY`: a unique random value
- `FLASK_CONFIG=development`
- `SQLALCHEMY_DATABASE_URI`: a PostgreSQL connection string; use the pooled Neon endpoint for ordinary app traffic
- Optional `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`: enable Google OpenID Connect
- Optional `FLASK_HOST` and `FLASK_PORT`: default to `127.0.0.1:8080`

Never commit `.env`, `.env.local`, database dumps, or credentials.

## Run Verve

```bash
python devel.py
```

Open [http://127.0.0.1:8080](http://127.0.0.1:8080). The development startup creates missing application tables and seeds the built-in shared vocabulary set. Apply production constraints and indexes separately by following [DEPLOYMENT.md](DEPLOYMENT.md).

## Run Tests

The test suite creates an isolated SQLite database and does not require Neon or Google credentials.

```bash
python -m unittest discover -s tests
```

Compile all Python modules as an additional syntax check:

```bash
python -m compileall -q app config.py devel.py wsgi.py scripts
```

Run both checks after changing authentication, database models, imports, security headers, scheduling, or API behavior.

## Project Structure

```text
app/            Application factory, models, routes, services, and security helpers
migrations/     Idempotent SQL migrations
scripts/        Database, migration, and asset utilities
static/         Stylesheets, JavaScript, images, and icons
templates/      Jinja templates
tests/          Automated application-flow tests
config.py       Environment-specific Flask configuration
devel.py        Local development entry point
wsgi.py         Production WSGI entry point
```

## Troubleshooting

### The port is already in use

Stop the existing process or set another port in `.env.local`, for example:

```dotenv
FLASK_PORT=8081
```

### The database connection fails

Confirm that `SQLALCHEMY_DATABASE_URI` is present in `.env.local`, includes `sslmode=require` for Neon, and does not contain unescaped special characters. Test the configured endpoint without printing credentials:

```bash
python scripts/test_db_connection.py
```

### Google sign-in is unavailable

Google sign-in is available only when both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are configured. Local username and password accounts remain available without them.
