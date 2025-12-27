# Verve

A modern Flask-based spaced repetition system for vocabulary learning. Verve uses the SM2 (SuperMemo 2) algorithm to optimize study sessions through scientifically calculated intervals.

---

## Features

- **Spaced Repetition (SM2)** — Cards appear at optimal intervals for long-term retention
- **Vocabulary Sets** — Organize vocabulary into customizable sets
- **Practice Mode** — Review all cards without affecting progress (random order)
- **Progress Tracking** — Visual statistics and learning analytics
- **Undo Functionality** — Revert accidental card ratings
- **Keyboard Shortcuts** — Efficient navigation via hotkeys
- **Profile Management** — Secure account handling with data export
- **Responsive UI** — Clean design with collapsible sidebar

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database (or Supabase account)

### Local Setup

```bash
# 1. Clone and navigate to project
cd Verve

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment (create .env file, see below)

# 5. Start development server
python devel.py
```

The app runs at: **http://127.0.0.1:8080**

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

| Variable                  | Required | Description                          |
|---------------------------|----------|--------------------------------------|
| `SECRET_KEY`              | Yes¹     | Flask secret key (random string)     |
| `SQLALCHEMY_DATABASE_URI` | Yes      | PostgreSQL connection string         |
| `FLASK_CONFIG`            | No       | `development` / `production`         |
| `FLASK_HOST`              | No       | Host address (default: `127.0.0.1`)  |
| `FLASK_PORT`              | No       | Port number (default: `8080`)        |

¹ Required in production, optional in development.

> **Security:** Never commit `.env` to version control.

### Development vs Production

| Aspect             | Development (`devel.py`)  | Production (`prod.py`)    |
|--------------------|---------------------------|---------------------------|
| Config Class       | `DevelopmentConfig`       | `ProductionConfig`        |
| Debug Mode         | Enabled                   | Disabled                  |
| Server             | Flask dev server          | Gunicorn                  |
| Port               | `8080`                    | `8000`                    |
| Secret Key         | Fallback allowed          | Required via env          |
| Secure Cookies     | Disabled                  | Enabled (HTTPS)           |

---

## Deployment

### Docker

Verve includes a `Dockerfile` for containerized deployment.

**Configuration:**

| Setting          | Value        |
|------------------|--------------|
| Dockerfile Path  | `Dockerfile` |
| Port             | `8000`       |

**Required Environment Variables:**

| Variable                  | Value                          |
|---------------------------|--------------------------------|
| `SECRET_KEY`              | Secure random string           |
| `SQLALCHEMY_DATABASE_URI` | PostgreSQL connection string   |
| `FLASK_CONFIG`            | `production`                   |

### Recommended Platforms

| Platform | Notes |
|----------|-------|
| [Koyeb](https://www.koyeb.com/) | Docker support, auto-deploy from GitHub |
| [Railway](https://railway.app/) | Simple setup, Dockerfile auto-detection |

### Database

Verve works with **any PostgreSQL database**. There is no dependency on a specific provider.

**Recommended Providers:**

| Provider | Notes |
|----------|-------|
| [Supabase](https://supabase.com/) | Easy setup, generous free tier |

**Example: Supabase Setup**

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string**
3. Select **Transaction pooling** mode
4. Copy connection string and replace `[YOUR-PASSWORD]`

```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

---

## Project Structure

```
Verve/
├── app/
│   ├── __init__.py        # App factory
│   ├── database.py        # Database initialization
│   ├── models/            # SQLAlchemy models
│   ├── routes/            # Flask blueprints
│   ├── services/          # Business logic (SM2, backup, etc.)
│   └── utils/             # Helper functions
├── static/                # CSS, JS, images
├── templates/             # Jinja2 templates
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── prod.py                # Production entry point
├── devel.py               # Development entry point
├── config.py              # Configuration classes
├── requirements.txt       # Dependencies
├── Procfile               # Koyeb/Heroku config

└── .env                   # Local config (not in repo)
```

---

## Tech Stack

| Layer        | Technology                             |
|--------------|----------------------------------------|
| Backend      | Flask 2.3.3                            |
| Database     | PostgreSQL (Supabase)                  |
| ORM          | Flask-SQLAlchemy 3.1.1                 |
| DB Driver    | psycopg2-binary 2.9.9                  |
| Auth         | Flask-Login 0.6.3, bcrypt 4.1.2        |
| Image        | Pillow 10.0.0                          |
| Server       | Gunicorn 21.2.0                        |
| Hosting      | Koyeb                                  |

---

## Utility Commands

```bash
# Run development server
python devel.py

# Create database backup
python devel.py backup

# Test database connection
python scripts/test_db_connection.py
```

---

## Credits

- **SM2 Algorithm** — [SuperMemo](https://www.supermemo.com/)
- **Icons** — [Material Symbols](https://fonts.google.com/icons)
- **Font** — [Poppins (Google Fonts)](https://fonts.google.com/specimen/Poppins)

---

## License

This project is available for personal and educational use.