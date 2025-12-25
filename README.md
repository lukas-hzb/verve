# Verve

A modern Flask-based spaced repetition system for vocabulary learning. Verve uses the SM2 (SuperMemo 2) algorithm to optimize study sessions through scientifically calculated intervals.

---

## Features

- **Spaced Repetition (SM2)** — Cards appear at optimal intervals for long-term retention
- **Vocabulary Sets** — Organize vocabulary into customizable sets
- **Practice Mode** — Review all cards without affecting progress (random order)
- **Progress Tracking** — Visual statistics and learning analytics
- **Undo Functionality** — Revert accidental card ratings
- **Card Shuffling** — Randomize card order for varied practice
- **Keyboard Shortcuts** — Efficient navigation via hotkeys
- **Profile Management** — Secure account handling and data management
- **Responsive UI** — Clean design with collapsible sidebar

---

## Tech Stack

| Layer        | Technology             |
|--------------|------------------------|
| Backend      | Flask 2.3.3            |
| Database     | PostgreSQL (Supabase)  |
| ORM          | Flask-SQLAlchemy 3.1.1 |
| Auth         | Flask-Login 0.6.3      |
| Password     | bcrypt 4.1.2           |
| Validation   | email-validator 2.1.0  |
| WSGI Server  | Gunicorn 21.2.0        |
| Hosting      | Koyeb                  |
| Environment  | python-dotenv 1.0.0    |

---

## Services & Setup

### Supabase (Database)

The app uses Supabase's PostgreSQL database.

**Connection String Format:**
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

**Setup:**
1. Create a project at [supabase.com](https://supabase.com)
2. Go to **Settings → Database → Connection string**
3. Copy the connection string (Session/Transaction pooling mode)
4. Replace `[YOUR-PASSWORD]` with your database password

---

### Koyeb (Hosting)

Verve is deployed on [Koyeb](https://www.koyeb.com/).

**Deployment Settings:**

| Setting        | Value                                              |
|----------------|----------------------------------------------------|
| Build Command  | `pip install -r requirements.txt`                  |
| Run Command    | `gunicorn app:app`                                 |
| Port           | `8000` (default)                                   |

**Required Environment Variables:**

| Variable                   | Description                          | Example                                      |
|----------------------------|--------------------------------------|----------------------------------------------|
| `SECRET_KEY`               | Flask secret key (random string)     | `your-secure-random-string-here`             |
| `SQLALCHEMY_DATABASE_URI`  | Supabase connection string           | `postgresql://postgres.[REF]:...`            |
| `FLASK_CONFIG`             | Configuration mode                   | `production`                                 |

**Setting Environment Variables on Koyeb:**
1. Go to your Koyeb service dashboard
2. Navigate to **Settings → Environment variables**
3. Add each variable with its value
4. Redeploy the service

---

## Local vs. Production

| Aspect             | Local (`local.py`)           | Production (`app.py`)           |
|--------------------|------------------------------|---------------------------------|
| Configuration      | `DevelopmentConfig`          | `ProductionConfig`              |
| Debug Mode         | Enabled                      | Disabled                        |
| Server             | Flask dev server             | Gunicorn                        |
| Port               | `8080`                       | `8000`                          |
| Secret Key         | Fallback allowed             | **Required** via env variable   |
| Secure Cookies     | Disabled                     | Enabled (HTTPS only)            |

### Running Locally

```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up .env file (copy template and fill values)
cp .env.example .env

# 4. Run the development server
python local.py
```

The app will start at: `http://127.0.0.1:8080`

---

## Project Structure

```
Verve_NewDesign_Supabase_Production/
├── app/
│   ├── __init__.py        # App factory
│   ├── database.py        # Database initialization
│   ├── models/            # SQLAlchemy models
│   ├── routes/            # Flask route blueprints
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── static/                # CSS, JS, images
├── templates/             # Jinja2 templates
├── app.py                 # Production WSGI entry point
├── local.py               # Local development entry point
├── config.py              # Configuration classes
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (not in repo)
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secure-random-string
SQLALCHEMY_DATABASE_URI=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
FLASK_CONFIG=development
FLASK_HOST=127.0.0.1
FLASK_PORT=8080
```

> **Note:** Never commit `.env` to version control.

---

## Credits

- **SM2 Algorithm** — [SuperMemo](https://www.supermemo.com/)
- **Icons** — [Material Symbols](https://fonts.google.com/icons)
- **Font** — [Poppins (Google Fonts)](https://fonts.google.com/specimen/Poppins)

---

## License

This project is available for personal and educational use.