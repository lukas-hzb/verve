"""
Authentication routes for user registration and login.

This module provides routes for user authentication including
registration, login, and logout functionality.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
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
                flash('Passwörter stimmen nicht überein.', 'error')
                return render_template('auth/register.html', 
                                     username=username, 
                                     email=email)
            
            # Create user
            user = UserService.create_user(username, email, password)
            
            # Auto-login after registration
            login_user(user, remember=True)
            
            flash(f'Willkommen {username}! Ihr Konto wurde erfolgreich erstellt.', 'success')
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
            flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'error')
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
            
            flash(f'Willkommen zurück, {user.username}!', 'success')
            return redirect(url_for('main.index'))
            
        except InvalidCredentialsError:
            flash('Ungültiger Benutzername/E-Mail oder Passwort.', 'error')
            return render_template('auth/login.html', 
                                 username_or_email=username_or_email)
        except Exception as e:
            flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'error')
            return render_template('auth/login.html', 
                                 username_or_email=username_or_email)
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out the current user."""
    username = current_user.username
    logout_user()
    flash(f'Auf Wiedersehen, {username}!', 'info')
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
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    avatar_file = request.files.get('avatar')
    remove_avatar = request.form.get('remove_avatar', 'false') == 'true'
    
    try:
        UserService.update_user_profile(current_user.id, username, email, avatar_file, remove_avatar)
        flash('Profil erfolgreich aktualisiert!', 'success')
    except UserAlreadyExistsError as e:
        flash(str(e), 'error')
    except InvalidInputError as e:
        flash(str(e), 'error')
    except Exception as e:
        flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'error')
        
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
                flash('Die neuen Passwörter stimmen nicht überein.', 'error')
                return render_template('auth/change_password.html')
                
            UserService.change_password(current_user.id, current_password, new_password)
            flash('Passwort erfolgreich geändert!', 'success')
            return redirect(url_for('auth.profile'))
            
        except InvalidCredentialsError as e:
            flash(str(e), 'error')
        except InvalidInputError as e:
            flash(str(e), 'error')
        except Exception as e:
            flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'error')
            
    return render_template('auth/change_password.html')


@auth_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Permanently delete the current user's account and ALL associated data."""
    try:
        from app.models.vocab_set import VocabSet
        from app.models.card import Card
        from app.database import db
        import os
        from flask import current_app
        
        # Get user ID before deletion
        user_id = current_user.id
        avatar_file = current_user.avatar_file
        
        # Step 1: Delete all cards belonging to user's vocab sets
        # Since foreign keys are disabled, we need to manually cascade
        user_set_ids = [vs.id for vs in VocabSet.query.filter_by(user_id=user_id).all()]
        if user_set_ids:
            Card.query.filter(Card.vocab_set_id.in_(user_set_ids)).delete(synchronize_session=False)
        
        # Step 2: Delete all vocab sets
        VocabSet.query.filter_by(user_id=user_id).delete()
        
        # Step 3: Delete avatar file from filesystem if exists
        if avatar_file:
            try:
                avatar_path = current_app.config['UPLOAD_FOLDER'] / avatar_file
                if avatar_path.exists():
                    avatar_path.unlink()
            except Exception as e:
                # Log but don't fail the deletion if avatar removal fails
                current_app.logger.error(f"Failed to delete avatar file: {e}")
        
        # Step 4: Delete the user account
        db.session.delete(current_user)
        
        # Commit all deletions
        db.session.commit()
        
        # Step 5: Log out the user
        logout_user()
        
        flash('Ihr Account und alle zugehörigen Daten wurden erfolgreich gelöscht.', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting account: {e}")
        flash(f'Ein Fehler ist aufgetreten: {str(e)}', 'error')
        return redirect(url_for('auth.profile'))

