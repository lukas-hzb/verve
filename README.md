# Verve

Verve is a modern, Flask-based spaced repetition system designed to optimize vocabulary learning. It combines the scientifically proven SM2 (SuperMemo 2) algorithm with other features to create the ultimate learning companion.

## Features

- **Spaced Repetition (SM2)**: The core algorithm schedules reviews based on performance, maximizing long-term retention.
- **Smart Import**: Vocabulary can be imported from CSV or text files with custom separators.
- **Google Login**: One-click secure sign-in via Supabase OAuth.
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

Ensure that **Python 3.11** or higher and **Git** are installed on your system. Then execute the following commands in the terminal:

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
# (Create a .env file as described in the Configuration section below)

# 5. Start the application
python devel.py
```

## Configuration

Verve uses a `.env` file to securely store settings. This file is not shared in the code repository to protect secrets.

**Step-by-Step:**

1. Create a new file named `.env` in the root folder.
2. Copy the content below and paste it into the file.
3. Replace the placeholder values (like `[YOUR_DB_URI]`) with the actual credentials.

```ini
# .env file content

# Security: Generate a random string (e.g., using 'openssl rand -hex 32')
SECRET_KEY=the-super-secret-key-goes-here

# Database: See "Database Setup" section below for how to get this URI
SQLALCHEMY_DATABASE_URI=postgresql://postgres:[PASSWORD]...

# Optional: Set to 'production' only when deploying
FLASK_CONFIG=development
```

## Database Setup

Verve is optimized for **Supabase**, a free and powerful PostgreSQL provider.

**Step-by-Step:**

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. Get Credentials:
   - Click the "Connect" button at the top of the Supabase dashboard.
   - In the modal that appears, click the "ORMs" tab.
   - In the dropdown, select "Prisma".
3. Copy the provided `DATABASE_URL`. It will look like this: `postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres`
4. Paste this URI into your `.env` file as the `SQLALCHEMY_DATABASE_URI`. Replace `[password]` with your actual database password. (If you forgot it, click the "Connect" button again, then click the "Database Settings" link at the bottom of the modal, and scroll down to "Reset database password". It's only shown once.)

## Deployment

In general, the deployment process is quite simple. Most services will autmatically deploy from GitHub and detect the `Dockerfile`. You will need to set `FLASK_CONFIG` to `production`, `DATABASE_URL` and `SECRET_KEY` environment variables manually (using the same values as your local `.env`).

| Platform                               | Pros                                                   | Cons                                                    |
| :------------------------------------- | :----------------------------------------------------- | :------------------------------------------------------ |
| **[Koyeb](https://www.koyeb.com/)** | Simple setup, Docker support, auto-deploy from GitHub. | No custom domain in free tier.                          |
| **[Railway](https://railway.app/)** | Simple setup, One custom domain per project.           | Free tier ends after one month.                         |
| **[Vercel](https://vercel.com/)**   | Custom domain in free tier.                            | Not as intuitive as the others, very slow in free tier. |

## Tech Stack

| Layer              | Technology  | Version |
| :----------------- | :---------- | :------ |
| **Backend**  | Flask       | 2.3.3   |
| **Language** | Python      | 3.11    |
| **Database** | PostgreSQL  | -       |
| **ORM**      | SQLAlchemy  | 3.1.1   |
| **Auth**     | Flask-Login | 0.6.3   |
| **Server**   | Gunicorn    | 21.2.0  |

## Credits

Verve is built using the following projects and resources:

- **[SuperMemo 2 (SM2)](https://www.supermemo.com/)**: The algorithm for spaced repetition.
- **[Flask](https://flask.palletsprojects.com/)**: The Python web framework.
- **[Material Symbols](https://fonts.google.com/icons)**: Icons by Google.
- **[Poppins](https://fonts.google.com/specimen/Poppins)**: The font family used.

## License

...
