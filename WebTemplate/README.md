# Web Project Template (Python Flask)

This is a modern web project structure using a Python Flask backend.

## Structure

```
/
├── app.py              # Flask Application
├── requirements.txt    # Python Dependencies
├── templates/          # HTML Templates (Jinja2)
│   └── index.html
├── static/             # Static Assets
│   ├── css/
│   │   ├── variables.css
│   │   ├── reset.css
│   │   └── style.css
│   ├── js/
│   │   ├── app.js
│   │   └── components/
│   └── assets/
```

## Getting Started

1.  **Create a virtual environment (optional but recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application**:
    ```bash
    python app.py
    ```

4.  **View**: Open `http://127.0.0.1:5000` in your browser.

## Customization

*   **Logic**: Edit `app.py` for backend logic, `static/js/app.js` for frontend logic.
*   **Styles**: Edit `static/css/style.css`.
*   **Templates**: Edit `templates/index.html`.
