"""OAuth client configuration for external identity providers."""

from authlib.integrations.flask_client import OAuth


oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile email"},
)


def init_oauth(app) -> None:
    """Bind the OAuth registry to a Flask application."""
    oauth.init_app(app)
