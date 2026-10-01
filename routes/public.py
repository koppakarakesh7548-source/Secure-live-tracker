from flask import Blueprint, render_template, current_app, jsonify
from models import TrackingLink, Visit

public_bp = Blueprint('public', __name__)

@public_bp.route('/health')
def health_check():
    """Production health check endpoint for uptime monitoring and load balancers."""
    return jsonify({"status": "ok"}), 200

@public_bp.route('/')
def index():
    """Public educational landing page."""
    total_links = TrackingLink.query.count()
    total_visits = Visit.query.count()
    return render_template('landing.html', total_links=total_links, total_visits=total_visits)

@public_bp.route('/privacy-info')
def privacy_info():
    """Detailed educational privacy documentation and responsible use guidelines."""
    return render_template('privacy_info.html')
