"""
Authentication routes for user registration and login.

This module provides routes for user authentication including
registration, login, and logout functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.services import UserService, VocabService
from app.utils.exceptions import UserAlreadyExistsError, InvalidCredentialsError, InvalidInputError


# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        
        try:
            # Validate password confirmation
            if password != password_confirm:
                flash('Passwords do not match.', 'error')
                return render_template('auth/register.html', 
                                     username=username, 
                                     email=email)
            
            # Create user
            user = UserService.create_user(username, email, password)
            
            # Auto-login after registration
            login_user(user, remember=True)
            
            flash(f'Welcome {username}! Your account was created successfully.', 'success')
            return redirect(url_for('main.index'))
            
        except UserAlreadyExistsError as e:
            flash(str(e), 'error')
            return render_template('auth/register.html', 
                                 username=username, 
                                 email=email)
        except InvalidInputError as e:
            flash(str(e), 'error')
            return render_template('auth/register.html', 
                                 username=username, 
                                 email=email)
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/register.html', 
                                 username=username, 
                                 email=email)
    
    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'
        
        try:
            # Authenticate user
            user = UserService.authenticate_user(username_or_email, password)
            
            # Log in user
            login_user(user, remember=remember)
            
            # Redirect to next page or index
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('main.index'))
            
        except InvalidCredentialsError:
            flash('Invalid username/email or password.', 'error')
            return render_template('auth/login.html', 
                                 username_or_email=username_or_email)
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('auth/login.html', 
                                 username_or_email=username_or_email)
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}!', 'info')
    return redirect(url_for('auth.login'))


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
        
        # Check if it's an AJAX request (accepts JSON)
        if request.headers.get('Accept') == 'application/json':
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully!',
                'username': updated_user.username,
                'email': updated_user.email,
                'avatar_url': updated_user.avatar_file
            })
            
        flash('Profile updated successfully!', 'success')
    except UserAlreadyExistsError as e:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': str(e)}), 400
        flash(str(e), 'error')
    except InvalidInputError as e:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': str(e)}), 400
        flash(str(e), 'error')
    except Exception as e:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500
        flash(f'An error occurred: {str(e)}', 'error')
        
    return redirect(url_for('auth.profile'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        try:
            if new_password != confirm_password:
                flash('New passwords do not match.', 'error')
                return render_template('auth/change_password.html')
                
            UserService.change_password(current_user.id, current_password, new_password)
            flash('Password changed successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except InvalidCredentialsError as e:
            flash(str(e), 'error')
        except InvalidInputError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
            
    return render_template('auth/change_password.html')


@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Permanently delete the current user's account and ALL associated data."""
    try:
        # Delete user and all data via service
        UserService.delete_user(current_user.id)
        
        # Log out the user
        logout_user()
        
        flash('Your account and all associated data have been successfully deleted.', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"Error deleting account: {e}")
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('auth.profile'))

