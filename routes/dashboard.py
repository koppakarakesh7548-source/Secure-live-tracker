from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from models import db, TrackingLink, Visit, SystemSetting, AuditLog
from utils.security import get_client_ip

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def overview():
    total_links = TrackingLink.query.count()
    all_links = TrackingLink.query.all()
    
    active_links = sum(1 for l in all_links if l.is_accessible())
    expired_links = sum(1 for l in all_links if l.is_expired())
    
    total_visits = Visit.query.count()
    consent_granted = Visit.query.filter_by(consent_status='granted').count()
    consent_denied = Visit.query.filter_by(consent_status='denied').count()

    consent_rate = round((consent_granted / total_visits * 100), 1) if total_visits > 0 else 0

    # Recent visits
    recent_visits = Visit.query.order_by(Visit.timestamp.desc()).limit(10).all()
    recent_links = TrackingLink.query.order_by(TrackingLink.created_at.desc()).limit(5).all()

    # Browser & OS breakdown for consented records
    browser_stats = db.session.query(
        Visit.browser, func.count(Visit.id)
    ).filter(Visit.consent_status == 'granted', Visit.browser != None).group_by(Visit.browser).limit(5).all()

    os_stats = db.session.query(
        Visit.operating_system, func.count(Visit.id)
    ).filter(Visit.consent_status == 'granted', Visit.operating_system != None).group_by(Visit.operating_system).limit(5).all()

    return render_template(
        'dashboard/overview.html',
        total_links=total_links,
        active_links=active_links,
        expired_links=expired_links,
        total_visits=total_visits,
        consent_granted=consent_granted,
        consent_denied=consent_denied,
        consent_rate=consent_rate,
        recent_visits=recent_visits,
        recent_links=recent_links,
        browser_stats=browser_stats,
        os_stats=os_stats
    )

@dashboard_bp.route('/privacy')
@login_required
def privacy():
    """Privacy management center and data lifecycle controls."""
    retention_days = int(SystemSetting.get('retention_days', 90))
    total_visits = Visit.query.count()
    granted_visits = Visit.query.filter_by(consent_status='granted').count()
    denied_visits = Visit.query.filter_by(consent_status='denied').count()

    # Calculate count of visits older than retention days
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    expired_records_count = Visit.query.filter(Visit.timestamp < cutoff).count()

    return render_template(
        'dashboard/privacy.html',
        retention_days=retention_days,
        total_visits=total_visits,
        granted_visits=granted_visits,
        denied_visits=denied_visits,
        expired_records_count=expired_records_count,
        cutoff=cutoff
    )

@dashboard_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    retention_days = int(SystemSetting.get('retention_days', 90))
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(25).all()

    if request.method == 'POST':
        action_type = request.form.get('action_type')

        if action_type == 'update_retention':
            try:
                new_days = int(request.form.get('retention_days', 90))
                if new_days < 1 or new_days > 365:
                    flash('Retention period must be between 1 and 365 days.', 'danger')
                else:
                    SystemSetting.set('retention_days', str(new_days))
                    AuditLog.record(
                        action='CONFIG_RETENTION_UPDATED',
                        admin_id=current_user.id,
                        target_type='setting',
                        target_id='retention_days',
                        details=f'Retention period updated to {new_days} days',
                        ip_address=get_client_ip()
                    )
                    flash(f'Data retention policy successfully updated to {new_days} days.', 'success')
                    return redirect(url_for('dashboard.settings'))
            except ValueError:
                flash('Please enter a valid number of days.', 'danger')

        elif action_type == 'change_password':
            current_pass = request.form.get('current_password', '')
            new_pass = request.form.get('new_password', '')
            confirm_pass = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pass):
                flash('Current password verification failed.', 'danger')
            elif len(new_pass) < 8:
                flash('New password must be at least 8 characters long.', 'danger')
            elif new_pass != confirm_pass:
                flash('New password and confirmation do not match.', 'danger')
            else:
                current_user.set_password(new_pass)
                db.session.commit()
                AuditLog.record(
                    action='ADMIN_PASSWORD_CHANGED',
                    admin_id=current_user.id,
                    target_type='admin',
                    target_id=current_user.id,
                    details='Administrator credentials rotated',
                    ip_address=get_client_ip()
                )
                flash('Your administrator password has been updated securely.', 'success')
                return redirect(url_for('dashboard.settings'))

        elif action_type == 'purge_expired':
            days = int(SystemSetting.get('retention_days', 90))
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            purged = Visit.query.filter(Visit.timestamp < cutoff).delete(synchronize_session=False)
            db.session.commit()

            AuditLog.record(
                action='DATA_PURGE_EXECUTED',
                admin_id=current_user.id,
                target_type='visit',
                details=f'Purged {purged} visitor records older than {days} days',
                ip_address=get_client_ip()
            )
            flash(f'Data purge complete: Removed {purged} record(s) older than {days} days.', 'info')
            return redirect(url_for('dashboard.privacy'))

    return render_template(
        'dashboard/settings.html',
        retention_days=retention_days,
        audit_logs=audit_logs
    )
