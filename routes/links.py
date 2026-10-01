from datetime import datetime, timezone
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from models import db, TrackingLink, Visit, AuditLog
from utils.security import generate_secure_token, validate_target_url, get_client_ip, get_public_base_url

links_bp = Blueprint('links', __name__, url_prefix='/dashboard/links')

@links_bp.route('/')
@login_required
def list_links():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', '').strip().lower()

    query = TrackingLink.query

    if search_query:
        query = query.filter(
            (TrackingLink.name.ilike(f'%{search_query}%')) | 
            (TrackingLink.token.ilike(f'%{search_query}%')) |
            (TrackingLink.target_url.ilike(f'%{search_query}%'))
        )

    links = query.order_by(TrackingLink.created_at.desc()).all()

    # Apply in-memory status filter if selected
    if status_filter == 'active':
        links = [l for l in links if l.is_accessible()]
    elif status_filter == 'disabled':
        links = [l for l in links if not l.active]
    elif status_filter == 'expired':
        links = [l for l in links if l.is_expired()]

    return render_template(
        'dashboard/links.html',
        links=links,
        search_query=search_query,
        status_filter=status_filter
    )

@links_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        target_url = request.form.get('target_url', '').strip()
        description = request.form.get('description', '').strip()
        expires_at_raw = request.form.get('expires_at', '').strip()

        # Validation
        if not name:
            flash('Link Name is required.', 'danger')
            return render_template('dashboard/create_link.html', form_data=request.form), 400

        is_valid, cleaned_url = validate_target_url(target_url)
        if not is_valid:
            flash(f'Invalid Target URL: {cleaned_url}', 'danger')
            return render_template('dashboard/create_link.html', form_data=request.form), 400

        expires_at = None
        if expires_at_raw:
            try:
                expires_at = datetime.fromisoformat(expires_at_raw).replace(tzinfo=timezone.utc)
                if expires_at <= datetime.now(timezone.utc):
                    flash('Expiration date must be in the future.', 'danger')
                    return render_template('dashboard/create_link.html', form_data=request.form), 400
            except ValueError:
                flash('Invalid expiration date format.', 'danger')
                return render_template('dashboard/create_link.html', form_data=request.form), 400

        # Generate unique token with >= 128 bits of cryptographic randomness (22 chars)
        for _ in range(10):
            candidate_token = generate_secure_token(22)
            if not TrackingLink.query.filter_by(token=candidate_token).first():
                break
        else:
            flash('Failed to generate a unique token. Please try again.', 'danger')
            return render_template('dashboard/create_link.html', form_data=request.form), 500

        new_link = TrackingLink(
            token=candidate_token,
            name=name,
            description=description if description else None,
            target_url=cleaned_url,
            expires_at=expires_at,
            active=True,
            created_by_id=current_user.id
        )

        db.session.add(new_link)
        db.session.commit()

        AuditLog.record(
            action='LINK_CREATED',
            admin_id=current_user.id,
            target_type='link',
            target_id=new_link.id,
            details=f'Created tracking link {new_link.token} targeting {cleaned_url}',
            ip_address=get_client_ip()
        )

        flash(f'Tracking link "{new_link.name}" generated successfully!', 'success')
        return redirect(url_for('links.detail', link_id=new_link.id))

    return render_template('dashboard/create_link.html', form_data={})

@links_bp.route('/<int:link_id>')
@login_required
def detail(link_id):
    link = db.get_or_404(TrackingLink, link_id)
    visits = link.visits.order_by(Visit.timestamp.desc()).limit(50).all()
    
    granted_count = link.consent_granted_count
    denied_count = link.consent_denied_count
    total_count = link.total_visits
    consent_pct = round((granted_count / total_count * 100), 1) if total_count > 0 else 0

    return render_template(
        'dashboard/link_detail.html',
        link=link,
        visits=visits,
        granted_count=granted_count,
        denied_count=denied_count,
        total_count=total_count,
        consent_pct=consent_pct
    )

@links_bp.route('/<int:link_id>/expiration', methods=['POST'])
@login_required
def set_expiration(link_id):
    link = db.get_or_404(TrackingLink, link_id)
    raw_exp = request.form.get('expires_at', '').strip()

    if not raw_exp:
        link.expires_at = None
        db.session.commit()
        flash('Link expiration cleared (campaign set to indefinite).', 'info')
    else:
        try:
            exp = datetime.fromisoformat(raw_exp).replace(tzinfo=timezone.utc)
            if exp <= datetime.now(timezone.utc):
                flash('Expiration timestamp must be in the future.', 'danger')
            else:
                link.expires_at = exp
                db.session.commit()
                flash('Link expiration updated successfully.', 'success')
        except ValueError:
            flash('Invalid expiration datetime format.', 'danger')

    return redirect(url_for('links.detail', link_id=link.id))

@links_bp.route('/<int:link_id>/toggle', methods=['POST'])
@login_required
def toggle(link_id):
    link = db.get_or_404(TrackingLink, link_id)
    link.active = not link.active
    db.session.commit()

    action = 'LINK_ENABLED' if link.active else 'LINK_DISABLED'
    AuditLog.record(
        action=action,
        admin_id=current_user.id,
        target_type='link',
        target_id=link.id,
        details=f'Tracking link {link.token} status set to active={link.active}',
        ip_address=get_client_ip()
    )

    status_str = "activated" if link.active else "disabled"
    flash(f'Tracking link "{link.name}" has been {status_str}.', 'info')
    return redirect(request.referrer or url_for('links.list_links'))

@links_bp.route('/<int:link_id>/delete', methods=['POST'])
@login_required
def delete(link_id):
    link = db.get_or_404(TrackingLink, link_id)
    token = link.token
    name = link.name
    
    db.session.delete(link)
    db.session.commit()

    AuditLog.record(
        action='LINK_DELETED',
        admin_id=current_user.id,
        target_type='link',
        target_id=link_id,
        details=f'Deleted tracking link {token} ({name}) and associated visit records',
        ip_address=get_client_ip()
    )

    flash(f'Tracking link "{name}" and all associated visit logs have been permanently deleted.', 'warning')
    return redirect(url_for('links.list_links'))
