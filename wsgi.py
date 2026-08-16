"""Production WSGI entry point for Verve."""

import os

from app import create_app


os.environ.setdefault("FLASK_CONFIG", "production")

app = create_app(os.environ["FLASK_CONFIG"])


if __name__ == "__main__":
    app.run(debug=False)
