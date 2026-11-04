"""Versioned public assets, served by the CDN in production and Flask locally."""
from functools import lru_cache
from hashlib import sha256
from pathlib import Path


@lru_cache(maxsize=4)
def asset_version(static_folder):
    digest = sha256()
    for path in sorted(Path(static_folder).rglob('*')):
        if path.is_file() and 'uploads' not in path.relative_to(static_folder).parts:
            digest.update(path.relative_to(static_folder).as_posix().encode())
            digest.update(b'\0')
            digest.update(path.read_bytes())
    return digest.hexdigest()[:20]


def init_assets(app):
    from flask import abort, request
    from flask.sessions import SecureCookieSessionInterface
    version_file = Path(app.root_path).parent / 'asset-version.txt'
    version = version_file.read_text().strip() if version_file.exists() else asset_version(app.static_folder)
    # The version is in the path so relative CSS URLs and ES module imports share it.
    def public_asset(filename):
        if 'uploads' in Path(filename).parts:
            abort(404)
        return app.send_static_file(filename)

    app.add_url_rule(f'/assets/{version}/<path:filename>', 'asset', public_asset)

    class AssetSessionInterface(SecureCookieSessionInterface):
        def save_session(self, application, session, response):
            # Flask-Login reads the session in its response hook even for public assets.
            # They never use or change it; omit the resulting Vary: Cookie as well.
            if request.endpoint != 'asset':
                super().save_session(application, session, response)

    app.session_interface = AssetSessionInterface()

    @app.context_processor
    def asset_urls():
        from flask import url_for

        def versioned_url_for(endpoint, **values):
            return url_for('asset' if endpoint == 'static' else endpoint, **values)
        return {'url_for': versioned_url_for}

    @app.after_request
    def cache_policy(response):
        if request.endpoint == 'asset' and response.status_code in (200, 304):
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Vercel-CDN-Cache-Control'] = 'public, s-maxage=31536000'
        elif request.endpoint != 'static':
            response.headers['Cache-Control'] = 'private, no-store'
        return response
