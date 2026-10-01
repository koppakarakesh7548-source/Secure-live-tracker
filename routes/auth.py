from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Admin, AuditLog
from utils.security import get_client_ip

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.overview'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return render_template('auth/login.html'), 400

        admin = Admin.query.filter_by(username=username).first()
        client_ip = get_client_ip()

        if admin and admin.check_password(password):
            login_user(admin, remember=False)
            admin.last_login_at = datetime.now(timezone.utc)
            db.session.commit()

            AuditLog.record(
                action='ADMIN_LOGIN_SUCCESS',
                admin_id=admin.id,
                target_type='admin',
                target_id=admin.id,
                details=f'Successful administrator authentication for {username}',
                ip_address=client_ip
            )

            flash(f'Welcome back, {admin.username}. Authentication successful.', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard.overview'))
        else:
            AuditLog.record(
                action='ADMIN_LOGIN_FAILED',
                admin_id=admin.id if admin else None,
                target_type='admin',
                target_id=username,
                details=f'Failed login attempt for username: {username}',
                ip_address=client_ip
            )
            flash('Invalid administrator credentials provided. Please verify and try again.', 'danger')
            return render_template('auth/login.html'), 401

    return render_template('auth/login.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    client_ip = get_client_ip()
    AuditLog.record(
        action='ADMIN_LOGOUT',
        admin_id=current_user.id,
        target_type='admin',
        target_id=current_user.id,
        details='Administrator terminated session',
        ip_address=client_ip
    )
    logout_user()
    flash('You have been securely signed out.', 'info')
    return redirect(url_for('auth.login'))
