import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, abort, current_app
from flask_login import login_required, current_user
from models import db, Visit, TrackingLink, AuditLog
from utils.security import get_client_ip

visits_bp = Blueprint('visits', __name__, url_prefix='/dashboard/visits')

@visits_bp.route('/')
@login_required
def list_visits():
    link_id = request.args.get('link_id', type=int)
    consent_filter = request.args.get('consent', '').strip().lower()

    query = Visit.query

    if link_id:
        query = query.filter_by(tracking_link_id=link_id)

    if consent_filter in ('granted', 'denied'):
        query = query.filter_by(consent_status=consent_filter)

    visits = query.order_by(Visit.timestamp.desc()).limit(200).all()
    all_links = TrackingLink.query.order_by(TrackingLink.name.asc()).all()

    return render_template(
        'dashboard/visits.html',
        visits=visits,
        all_links=all_links,
        selected_link_id=link_id,
        selected_consent=consent_filter
    )

@visits_bp.route('/<int:visit_id>/snapshot')
@login_required
def view_snapshot(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    if not visit.snapshot_path:
        abort(404)
    filename = os.path.basename(visit.snapshot_path)
    snap_dir = os.path.join(current_app.instance_path, 'snapshots')
    return send_from_directory(snap_dir, filename)

@visits_bp.route('/<int:visit_id>/snapshot/delete', methods=['POST'])
@login_required
def delete_snapshot(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    if visit.snapshot_path:
        try:
            abs_p = os.path.join(current_app.instance_path, visit.snapshot_path)
            if os.path.exists(abs_p):
                os.remove(abs_p)
        except Exception:
            pass
        visit.snapshot_path = None
        visit.snapshot_timestamp = None
        db.session.commit()

        AuditLog.record(
            action='SNAPSHOT_DELETED',
            admin_id=current_user.id,
            target_type='visit',
            target_id=visit_id,
            details=f'Deleted camera snapshot for visit ID {visit_id}',
            ip_address=get_client_ip()
        )
        flash('Stored camera snapshot deleted successfully.', 'info')
    return redirect(request.referrer or url_for('visits.list_visits'))

@visits_bp.route('/<int:visit_id>/delete', methods=['POST'])
@login_required
def delete_single(visit_id):
    visit = db.get_or_404(Visit, visit_id)
    link_id = visit.tracking_link_id
    if visit.snapshot_path:
        try:
            abs_p = os.path.join(current_app.instance_path, visit.snapshot_path)
            if os.path.exists(abs_p):
                os.remove(abs_p)
        except Exception:
            pass
    db.session.delete(visit)
    db.session.commit()

    AuditLog.record(
        action='VISIT_RECORD_DELETED',
        admin_id=current_user.id,
        target_type='visit',
        target_id=visit_id,
        details=f'Deleted single visit log from link ID {link_id}',
        ip_address=get_client_ip()
    )

    flash('Visit record deleted successfully.', 'info')
    return redirect(request.referrer or url_for('visits.list_visits'))

@visits_bp.route('/purge-link/<int:link_id>', methods=['POST'])
@login_required
def purge_link_visits(link_id):
    link = db.get_or_404(TrackingLink, link_id)
    deleted_count = Visit.query.filter_by(tracking_link_id=link_id).delete(synchronize_session=False)
    db.session.commit()

    AuditLog.record(
        action='LINK_VISITS_PURGED',
        admin_id=current_user.id,
        target_type='link',
        target_id=link_id,
        details=f'Purged all {deleted_count} visit records for link {link.token}',
        ip_address=get_client_ip()
    )

    flash(f'Purged {deleted_count} visit record(s) for link "{link.name}".', 'warning')
    return redirect(request.referrer or url_for('links.detail', link_id=link_id))
