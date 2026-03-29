from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from database import get_db, reset_db
import re
import datetime

auth_bp = Blueprint('auth', __name__)


def init_auth(bcrypt):
    """Initialize auth routes with bcrypt instance."""

    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if 'user_id' in session:
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            errors = []
            if not username or len(username) < 3:
                errors.append('Username must be at least 3 characters.')
            if not email or not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
                errors.append('Please enter a valid email address.')
            if not password or len(password) < 6:
                errors.append('Password must be at least 6 characters.')
            if password != confirm_password:
                errors.append('Passwords do not match.')

            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('register.html', username=username, email=email)

            try:
                current_db = get_db()
                if current_db is None:
                    reset_db()   # clear stale cached failure
                    current_db = get_db()
                if current_db is None:
                    raise ConnectionFailure('No DB connection')

                if current_db.users.find_one({'email': email}):
                    flash('An account with this email already exists.', 'error')
                    return render_template('register.html', username=username, email=email)

                if current_db.users.find_one({'username': username}):
                    flash('This username is already taken.', 'error')
                    return render_template('register.html', username=username, email=email)

                hashed = bcrypt.generate_password_hash(password).decode('utf-8')
                current_db.users.insert_one({
                    'username': username,
                    'email': email,
                    'password': hashed,
                    'created_at': datetime.datetime.utcnow()
                })
                flash('Account created successfully! Please log in.', 'success')
                return redirect(url_for('auth.login'))

            except (ConnectionFailure, ServerSelectionTimeoutError):
                flash('Database unavailable. Please check your connection and try again.', 'error')
                return render_template('register.html', username=username, email=email)
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
                return render_template('register.html', username=username, email=email)

        return render_template('register.html')

    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if 'user_id' in session:
            return redirect(url_for('main.dashboard'))

        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

            if not email or not password:
                flash('Please fill in all fields.', 'error')
                return render_template('login.html', email=email)

            try:
                current_db = get_db()
                if current_db is None:
                    reset_db()   # clear stale cached failure
                    current_db = get_db()
                if current_db is None:
                    raise ConnectionFailure('No DB connection')
                user = current_db.users.find_one({'email': email})
            except (ConnectionFailure, ServerSelectionTimeoutError):
                flash('Database unavailable. Please check your connection and try again.', 'error')
                return render_template('login.html', email=email)
            except Exception as e:
                flash(f'Error: {str(e)}', 'error')
                return render_template('login.html', email=email)

            if user and bcrypt.check_password_hash(user['password'], password):
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('main.dashboard'))
            else:
                flash('Invalid email or password.', 'error')
                return render_template('login.html', email=email)

        return render_template('login.html')

    @auth_bp.route('/logout')
    def logout():
        session.clear()
        flash('Logged out successfully.', 'info')
        return redirect(url_for('main.index'))

    return auth_bp
