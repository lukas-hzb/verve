# Verve

Verve is a Flask-based spaced-repetition web application for vocabulary learning. It combines SM-2-style review scheduling with vocabulary sets, imports, practice sessions, and progress statistics. The hosted application is available at [verve.hzb.app](https://verve.hzb.app).

## Features

- **Spaced Repetition (SM2)**: The core algorithm schedules reviews based on performance, maximizing long-term retention.
- **Smart Import**: Vocabulary can be imported from CSV or text files with custom separators.
- **Google Login**: Optional one-click sign-in via Google OpenID Connect.
- **Vocabulary Sets**: Words can be organized into custom sets (e.g., "Spanish Basics").
- **Practice Mode**: Cards can be reviewed without affecting the spaced repetition schedule.
- **Profile Customization**: Avatars and personal profile details are fully manageable.
- **Progress Tracking**: Learning progress is visualized with intuitive charts and statistics.
- **Responsive UI**: A clean, modern interface that functions seamlessly, especially on desktop devices.

### Screenshots

|                                  Dashboard View                                  |                                   Add Card Dialog                                   |
| :-------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------: |
| <img src="static/images/dashboard_preview.png" alt="Dashboard" width="400" /> | <img src="static/images/add_card_dialog.png" alt="Add Card" width="400" /> |

|                              Study Session                              |                                 Statistics                                 |
| :-------------------------------------------------------------------------: | :-------------------------------------------------------------------------: |
| <img src="static/images/study_session.png" alt="Study Session" width="400" /> | <img src="static/images/statistics.png" alt="Statistics" width="400" /> |

## Installation

### Local Setup

Install **Python 3.12** and **Git** first. The commands below use `python`; on systems where Python 3 is exposed as `python3` or `py -3.12`, use that command consistently instead.

```bash
# 1. Download the project
git clone https://github.com/lukas-hzb/verve.git
cd verve

# 2. Create and activate virtual environment
python -m venv .venv

# Windows:
# .venv\Scripts\activate

# Mac/Linux:
# source .venv/bin/activate

# 3. Install dependencies
python -m pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env.local
# Then replace the placeholders in .env.local.

# 5. Start the application
python devel.py
```

The development server listens on `http://127.0.0.1:8080` by default. Change `FLASK_HOST` or `FLASK_PORT` in `.env.local` when needed.

## Usage

1. Register a local account or use Google sign-in when the deployment has OpenID Connect configured.
2. Create a vocabulary set or import cards from a supported text or CSV file.
3. Start a scheduled review to update the repetition plan, or use practice mode without changing it.
4. Review set-level progress and statistics from the dashboard.

## Configuration

Verve uses the committed `.env.example` as a safe template and `.env.local` for
machine-specific secrets. `.env.local` is ignored by Git.

**Step-by-Step:**

1. Copy `.env.example` to `.env.local`.
2. Generate a strong `SECRET_KEY`, for example with `openssl rand -hex 32`.
3. Add the pooled Neon connection string as `SQLALCHEMY_DATABASE_URI`.
4. Add `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` only when Google login is enabled.

## Database Setup

Verve uses **Neon Postgres**. Application data and password hashes live in the
same PostgreSQL database; passwords are never stored in plain text.

**Step-by-Step:**

1. Create a project at [neon.com](https://neon.com).
2. Open **Connect** in the Neon dashboard.
3. Enable **Connection pooling** for application/serverless traffic.
4. Copy the connection string into `.env.local` as `SQLALCHEMY_DATABASE_URI`.
5. Keep `sslmode=require` in the connection string.

Use a direct, non-pooled connection only for schema and data migrations.

After creating or importing the database, apply the idempotent constraints and
indexes with:

```bash
python scripts/apply_neon_schema.py
```

The script automatically converts a configured pooled Neon endpoint to its
direct migration endpoint and verifies every applied index and constraint.

### Migrating an existing Supabase database

Keep the old Supabase URL in `SQLALCHEMY_DATABASE_URI` temporarily, install the
dependencies, and run:

```bash
python scripts/migrate_to_neon.py
```

Enter the direct Neon URL at the hidden prompt. The migration copies users,
password hashes, Google identity links, vocabulary sets, and cards, then verifies
row counts and foreign-key integrity. After it succeeds, replace the deployment
and local `SQLALCHEMY_DATABASE_URI` with the pooled Neon URL and remove all old
Supabase secrets.

## Tests

The test suite uses an isolated temporary SQLite database and does not require Neon credentials:

```bash
python -m unittest discover -s tests
```

Run the tests after changing authentication, imports, database models, security headers, or API behavior.

## Deployment

The current deployment targets Vercel through the automatically detected
`wsgi.py` entry point. Docker and Procfile deployments use the same WSGI app.
Container platforms can use the included `Dockerfile` instead. Configure these
environment variables in the hosting platform:

- `FLASK_CONFIG=production`
- `SQLALCHEMY_DATABASE_URI` with the pooled Neon URL
- `SECRET_KEY` with a long random value
- Optional: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

Schema and data migrations must use the direct Neon endpoint and should be run
separately from application startup.

## Data and External Services

- Account data, password hashes, vocabulary sets, cards, and learning progress are stored in the configured database.
- Google OpenID Connect is optional and is contacted only when it is configured and a user chooses Google sign-in.
- The interface loads Google-hosted fonts and the Google sign-in mark from external URLs.
- Database credentials, session secrets, and OAuth credentials belong in `.env.local` or protected deployment secrets and must never be committed.

## Tech Stack

| Layer              | Technology  | Version |
| :----------------- | :---------- | :------ |
| **Backend**  | Flask       | 2.3.3   |
| **Language** | Python      | 3.12    |
| **Database** | Neon Postgres | -     |
| **ORM**      | Flask-SQLAlchemy | 3.1.1 |
| **Auth**     | Flask-Login / Authlib | 0.6.3 / 1.7.2 |
| **Server**   | Gunicorn    | 21.2.0  |

## Credits

Verve is built using the following projects and resources:

- **[SuperMemo 2 (SM2)](https://www.supermemo.com/)**: The algorithm for spaced repetition.
- **[Flask](https://flask.palletsprojects.com/)**: The Python web framework.
- **[Material Symbols](https://fonts.google.com/icons)**: Icons by Google.
- **[Poppins](https://fonts.google.com/specimen/Poppins)**: The font family used.

## License

This project is proprietary source-available software protected by copyright law. Private, personal, educational, and informational use is permitted only under the conditions in [LICENSE](LICENSE); redistribution and commercial use require prior written permission.

Persona Non Grata:
Daniel Harzbecker is expressly and unconditionally excluded from any license or permission to use this software. Any access, use, or reproduction by this individual does not constitute a license and shall be deemed a willful infringement of intellectual property rights.

Third-party packages and resources remain subject to their respective license terms.

Copyright (c) 2026 Lukas Harzbecker. All Rights Reserved.
