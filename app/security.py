"""Application-wide web security helpers."""

from urllib.parse import urljoin, urlparse

from flask import flash, jsonify, redirect, request, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect


csrf = CSRFProtect()


def is_safe_redirect_target(target: str | None) -> bool:
    """Allow redirects only to HTTP(S) URLs on the current host."""
    if not target or "\\" in target or any(ord(char) < 32 for char in target):
        return False

    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return (
        redirect_url.scheme in {"http", "https"}
        and redirect_url.netloc == host_url.netloc
    )


def init_security(app) -> None:
    """Enable CSRF protection and conservative browser security headers."""
    csrf.init_app(app)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.method == 'POST' and not request.is_json:
            if request.endpoint == 'main.import_into_set':
                destination = url_for('main.set_overview', set_id=request.view_args['set_id'])
            elif request.endpoint == 'main.import_set':
                destination = url_for('main.import_set')
            else:
                destination = None
            if destination:
                flash('The import could not be verified. Please open the import form and try again.', 'error')
                return redirect(destination, code=303)

        if request.path.startswith("/api/") or request.is_json:
            return jsonify({
                "status": "error",
                "message": "The Request could not be verified. Please reload the Page and try again.",
            }), 400
        return error.description, 400

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()",
        )
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response
