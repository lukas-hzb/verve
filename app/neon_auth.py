"""Neon Auth transport for Flask; identity and OAuth are managed by Neon.

The browser uses the official Neon SDK through a same-origin proxy. Cookie
forwarding follows the SDK server proxy contract; Flask never validates Google
responses or accepts client-supplied identities.
"""

from http.cookies import SimpleCookie
import re
from urllib.parse import urlparse

import requests
from flask import abort, current_app, g, request

UPSTREAM_COOKIE_PREFIX = '__Secure-neon-auth'
LOCAL_COOKIE_PREFIX = 'verve_neon'
ALLOWED_ENDPOINTS = {
    'get-session': 'GET',
    'sign-in/social': 'POST',
    'sign-in/email': 'POST',
    'sign-up/email': 'POST',
    'sign-out': 'POST',
    'email-otp/request-password-reset': 'POST',
    'email-otp/reset-password': 'POST',
    'change-password': 'POST',
    'email-otp/send-verification-otp': 'POST',
    'email-otp/verify-email': 'POST',
}


def auth_request(path, method='GET', *, data=None, params=None):
    base_url = current_app.config.get('NEON_AUTH_BASE_URL', '').rstrip('/')
    if not base_url or urlparse(base_url).scheme != 'https':
        abort(503, description='Neon Auth is not configured.')
    cookies = '; '.join(
        f'{name.replace(LOCAL_COOKIE_PREFIX, UPSTREAM_COOKIE_PREFIX, 1)}={value}'
        for name, value in request.cookies.items()
        if name.startswith(LOCAL_COOKIE_PREFIX + '.')
    )
    try:
        upstream = requests.request(
            method, f'{base_url}/{path}', json=data, params=params,
            headers={
                'Cookie': cookies,
                'Origin': request.host_url.rstrip('/'),
                'User-Agent': request.headers.get('User-Agent', 'Verve'),
                'x-neon-auth-middleware': 'true',
            },
            timeout=(5, 15), allow_redirects=False,
        )
        if not upstream.ok:
            try:
                error_code = upstream.json().get('code', 'UNKNOWN')
            except ValueError:
                error_code = 'NON_JSON_RESPONSE'
            current_app.logger.warning('Neon Auth %s failed: status=%s code=%s cookie_names=%s',
                path, upstream.status_code, error_code,
                [name for name in request.cookies if name.startswith(LOCAL_COOKIE_PREFIX)])
        return upstream
    except requests.RequestException:
        current_app.logger.warning('Neon Auth request failed: %s', path)
        abort(503, description='Authentication is temporarily unavailable. Please try again.')


def copy_auth_cookies(upstream, response):
    """Keep managed cookies on the app origin, with HTTP-only browser access."""
    for header in upstream.raw.headers.getlist('Set-Cookie'):
        cookies = SimpleCookie()
        # Python 3.12 SimpleCookie rejects the CHIPS Partitioned attribute.
        # The SDK proxy also removes it for same-origin cookies.
        cookies.load(re.sub(r';\s*Partitioned(?=;|$)', '', header, flags=re.I))
        for name, cookie in cookies.items():
            if not name.startswith(UPSTREAM_COOKIE_PREFIX + '.'):
                continue
            local_name = name.replace(UPSTREAM_COOKIE_PREFIX, LOCAL_COOKIE_PREFIX, 1)
            response.set_cookie(
                local_name, cookie.value, path='/', httponly=True,
                secure=current_app.config['SESSION_COOKIE_SECURE'], samesite='Lax',
                max_age=int(cookie['max-age']) if cookie['max-age'] else None,
                expires=cookie['expires'] or None,
            )
    response.headers['Cache-Control'] = 'no-store'
    return response


def get_identity():
    """Validate the managed session on every request, including revoked sessions."""
    if 'neon_identity' in g:
        return g.neon_identity
    g.neon_identity = None
    if not request.cookies.get(LOCAL_COOKIE_PREFIX + '.session_token'):
        return None
    upstream = auth_request('get-session', params={'disableCookieCache': 'true'})
    g.neon_session_response = upstream
    if upstream.status_code == 401:
        return None
    if not upstream.ok:
        abort(503, description='Authentication is temporarily unavailable.')
    try:
        payload = upstream.json()
    except ValueError:
        abort(503, description='Authentication is temporarily unavailable.')
    if payload and payload.get('session') and payload.get('user'):
        g.neon_identity = payload['user']
    return g.neon_identity


def init_neon_auth(app):
    @app.after_request
    def refresh_managed_cookies(response):
        upstream = g.get('neon_session_response')
        if upstream is not None:
            copy_auth_cookies(upstream, response)
        return response
