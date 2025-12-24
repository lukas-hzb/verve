# Verve - Vocabulary Learning App

A modern, Flask-based spaced repetition system for efficient vocabulary learning. Verve uses the SM2 (SuperMemo 2) algorithm to optimize your study sessions by showing cards at scientifically calculated intervals.

## Features

- **Spaced Repetition System**: Uses the proven SM2 algorithm to optimize learning
- **Multiple Vocabulary Sets**: Organize your vocabulary into different sets
- **Practice Mode**: Review all cards in random order without affecting progress
- **Progress Tracking**: Visual statistics showing your learning progress
- **Keyboard Shortcuts**: Efficient navigation with keyboard controls
- **Modern UI**: Clean, responsive design with collapsible sidebar
- **Undo Functionality**: Revert accidental card ratings with the "Back" button
- **Profile Management**: Secure account deletion and data management
- **Card Shuffling**: Randomize card order for varied practice

## Installation

...

## License

This project is open source and available for personal and educational use.

## Credits

- SM2 Algorithm: [SuperMemo](https://www.supermemo.com/)
- Icons: [Feather Icons](https://feathericons.com/)
- Font: [Google Fonts - Poppins](https://fonts.google.com/specimen/Poppins)

## Support

For issues, questions, or contributions, please refer to the project repository.

---

**Happy Learning! 📚✨**

## Deployment

### PythonAnywhere Setup

1.  **Code Setup**:
    *   Upload this code to PythonAnywhere.
    *   Open a Bash console and navigate to the project folder.
    *   Create a virtual environment: `mkvirtualenv --python=/usr/bin/python3.10 my-virtualenv`
    *   Install dependencies: `pip install -r requirements.txt`

2.  **Environment Variables**:
    *   Create a `.env` file in the project root (use `.env.example` as a template).
    *   **CRITICAL**: Set `SECRET_KEY` to a random secure string.
    *   Set `SQLALCHEMY_DATABASE_URI` to your Supabase connection string.

3.  **Web App Configuration**:
    *   Go to the "Web" tab on PythonAnywhere.
    *   Add a new web app, select "Manual Configuration".
    *   Select Python 3.10 (or matching your venv).
    *   **Virtualenv**: Enter the path to your virtualenv (e.g., `/home/username/.virtualenvs/my-virtualenv`).
    *   **WSGI Configuration File**: Click the link to edit the WSGI file. Replace its content with:

    ```python
    import sys
    import os

    # Add project directory to sys.path
    path = '/home/yourusername/Verve_NewDesign_Supabase'
    if path not in sys.path:
        sys.path.append(path)

    # Import the app from prod.py
    from prod import app as application
    ```

4.  **Reload**:
    *   Click the green "Reload" button at the top.

### Local vs. Production

*   **Development**: Run `python run.py`. This uses `config.DevelopmentConfig`, enables debug mode, and runs on port 8080.
*   **Production**: The `prod.py` file is designed to be imported by a WSGI server (like Gunicorn or PythonAnywhere). It uses `config.ProductionConfig` and enforces security settings.
