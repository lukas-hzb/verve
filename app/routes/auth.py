"""
Authentication routes for user registration and login.

This module provides routes for user authentication including
registration, login, and logout functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session, g
from flask_login import login_required, current_user

from app.services import UserService, VocabService
from app.security import is_safe_redirect_target
from app.utils.exceptions import UserAlreadyExistsError, InvalidInputError


# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login')
@auth_bp.route('/register', endpoint='register')
@auth_bp.route('/callback', endpoint='auth_callback')
@auth_bp.route('/reset-password', endpoint='reset_password')
def login():
    if not request.args.get('neon_auth_session_verifier') and not request.path.endswith('/reset-password') and current_user.is_authenticated:
        return redirect(url_for('main.index'))
    mode = 'register' if request.path.endswith('/register') else 'reset-password' if request.path.endswith('/reset-password') else 'login'
    next_page = request.args.get('next')
    if not is_safe_redirect_target(next_page):
        next_page = url_for('main.index')
    return render_template('auth/login.html', mode=mode, next_page=next_page)


@auth_bp.route('/neon/<path:endpoint>', methods=['GET', 'POST'])
def neon_proxy(endpoint):
    from flask import jsonify
    from app.neon_auth import ALLOWED_ENDPOINTS, auth_request, copy_auth_cookies
    if ALLOWED_ENDPOINTS.get(endpoint) != request.method:
        return jsonify({'message': 'Unsupported authentication endpoint.'}), 404
    data = request.get_json(silent=True) if request.method == 'POST' else None
    upstream = auth_request(endpoint, request.method, data=data, params=request.args)
    response = current_app.response_class(
        upstream.content, status=upstream.status_code, content_type='application/json',
    )
    return copy_auth_cookies(upstream, response)


@auth_bp.route('/logout', methods=['POST'])
def logout():
    from app.neon_auth import auth_request, copy_auth_cookies, LOCAL_COOKIE_PREFIX
    upstream = auth_request('sign-out', 'POST', data={})
    if not upstream.ok:
        flash('Logout failed. Please try again.', 'error')
        return redirect(url_for('auth.profile'))
    session.clear()
    g.pop('neon_session_response', None)
    response = redirect(url_for('auth.login'))
    copy_auth_cookies(upstream, response)
    for name in request.cookies:
        if name.startswith(LOCAL_COOKIE_PREFIX + '.') or name == 'remember_token':
            response.delete_cookie(name, path='/')
    return response


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    # Get stats for the user
    sets = VocabService.get_all_set_names(current_user.id)
    
    total_cards = 0
    due_cards = 0
    
    for s in sets:
        total_cards += s.get('card_count', 0)
        due_cards += s.get('due_count', 0)
        
    sidebar_collapsed = request.cookies.get('sidebar_collapsed', 'false') == 'true'
    
    return render_template('profile.html',
                         current_user=current_user,
                         sets=sets,
                         total_cards=total_cards,
                         due_cards=due_cards,
                         sidebar_collapsed=sidebar_collapsed)


@auth_bp.route('/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information."""
    from flask import jsonify

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    avatar_file = request.files.get('avatar')
    remove_avatar = request.form.get('remove_avatar', 'false') == 'true'
    
    try:
        updated_user = UserService.update_user_profile(current_user.id, username, email, avatar_file, remove_avatar)
        
        flash('Profile updated successfully!', 'success')

        # Check if it's an AJAX request (accepts JSON)
        if request.headers.get('Accept') == 'application/json':
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully!',
                'username': updated_user.username,
                'email': updated_user.email,
                'avatar_url': updated_user.avatar_file,
                'initials': updated_user.username[0].upper()
            })
            
    except UserAlreadyExistsError:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': 'Invalid profile data or username already in use'}), 400
        flash('Invalid profile data or username already in use', 'error')
    except InvalidInputError:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': 'Invalid profile data or username already in use'}), 400
        flash('Invalid profile data or username already in use', 'error')
    except Exception:
        current_app.logger.exception('Profile update failed')
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': 'Profile update failed. Please try again.'}), 500
        flash('Profile update failed. Please try again.', 'error')
        
    return redirect(url_for('auth.profile'))


@auth_bp.route('/change-password')
@login_required
def change_password():
    return render_template('auth/login.html', mode='change-password', next_page=url_for('auth.profile'))


@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Permanently delete the current user's account and ALL associated data."""
    from app.neon_auth import LOCAL_COOKIE_PREFIX
    try:
        UserService.delete_user(current_user.id)
        session.clear()
        g.pop('neon_session_response', None)
        response = redirect(url_for('auth.login'))
        for name in request.cookies:
            if name.startswith(LOCAL_COOKIE_PREFIX + '.') or name == 'remember_token':
                response.delete_cookie(name, path='/')
        return response
    except Exception:
        current_app.logger.exception('Account deletion failed')
        flash('Account deletion failed. Please try again.', 'error')
        return redirect(url_for('auth.profile'))
