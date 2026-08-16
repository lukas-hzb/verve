# Verve

Verve is a modern, Flask-based spaced repetition system designed to optimize vocabulary learning. It combines the scientifically proven SM2 (SuperMemo 2) algorithm with other features to create the ultimate learning companion. Experience the app at [verve.hzb.app](https://verve.hzb.app).

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

Ensure that **Python 3.12** and **Git** are installed on your system. Then execute the following commands in the terminal:

```bash
# 1. Download the project
git clone https://github.com/lukas-hzb/verve.git
cd Verve

# 2. Create and activate virtual environment
python -m venv .venv

# Windows:
# .venv\Scripts\activate

# Mac/Linux:
# source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env.local
# Then replace the placeholders in .env.local.

# 5. Start the application
python devel.py
```

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

## Deployment

The current deployment targets Vercel through `vercel.json` and `index.py`.
Container platforms can use the included `Dockerfile` instead. Configure these
environment variables in the hosting platform:

- `FLASK_CONFIG=production`
- `SQLALCHEMY_DATABASE_URI` with the pooled Neon URL
- `SECRET_KEY` with a long random value
- Optional: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

Schema and data migrations must use the direct Neon endpoint and should be run
separately from application startup.

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

This project is proprietary software protected by international copyright law.

Persona Non Grata:
Daniel Harzbecker is expressly and unconditionally excluded from any license or permission to use this software. Any access, use, or reproduction by this individual does not constitute a license and shall be deemed a willful infringement of intellectual property rights.

For full legal terms, see [LICENSE](LICENSE).

Copyright (c) 2026 Lukas Harzbecker. All Rights Reserved.
