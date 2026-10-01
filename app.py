import os
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, jsonify
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_wtf.csrf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from config import config_by_name, BASE_DIR
from models import db, Admin, TrackingLink, Visit, SystemSetting, AuditLog
from utils.security import add_security_headers, get_client_ip, get_public_base_url
from routes import public_bp, auth_bp, dashboard_bp, links_bp, visits_bp, tracker_bp

login_manager = LoginManager()
limiter = Limiter(key_func=get_client_ip)
csrf = CSRFProtect()

def create_app(config_name=None):
    if not config_name:
        config_name = os.environ.get('FLASK_ENV', 'production')

    app = Flask(__name__)
    cfg = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(cfg)
    app.url_map.strict_slashes = False

    # Apply ProxyFix middleware if configured behind reverse proxy/tunnel
    if app.config.get('BEHIND_PROXY', False) and not app.config.get('TESTING', False):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    # Ensure database directory exists
    db_dir = os.path.join(BASE_DIR, 'database')
    os.makedirs(db_dir, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please authenticate with your administrator credentials.'
    login_manager.login_message_category = 'info'

    csrf.init_app(app)

    if not app.config.get('TESTING', False) and app.config.get('RATELIMIT_ENABLED', True):
        limiter.init_app(app)
        limiter.limit("20 per minute")(auth_bp)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Admin, int(user_id))

    # Apply strict security headers on every response
    @app.after_request
    def apply_headers(response):
        return add_security_headers(response)

    # Custom Error Handlers
    @app.errorhandler(400)
    def bad_request(e):
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return render_template('errors/429.html'), 429

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Register Blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(visits_bp)
    app.register_blueprint(tracker_bp)

    # The public tracking decision endpoint accepts anonymous visitor submissions
    csrf.exempt(tracker_bp)

    # Context processors for template globals
    @app.context_processor
    def inject_globals():
        return {
            'app_name': 'Secure Live Tracker',
            'current_year': datetime.now().year,
            'default_retention_days': SystemSetting.get('retention_days', '90'),
            'public_base_url': get_public_base_url(),
            'development_url': 'http://127.0.0.1:5000'
        }

    def ensure_schema_updated():
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            if 'visits' in inspector.get_table_names():
                cols = [c['name'] for c in inspector.get_columns('visits')]
                with db.engine.connect() as conn:
                    if 'battery_percentage' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN battery_percentage INTEGER'))
                    if 'battery_charging' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN battery_charging BOOLEAN'))
                    if 'accuracy_radius' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN accuracy_radius INTEGER'))
                    if 'confidence_score' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN confidence_score FLOAT'))
                    if 'geolocation_provider' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN geolocation_provider VARCHAR(50)'))
                    if 'is_mobile' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN is_mobile BOOLEAN'))
                    if 'device_latitude' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_latitude FLOAT'))
                    if 'device_longitude' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_longitude FLOAT'))
                    if 'device_accuracy_meters' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_accuracy_meters FLOAT'))
                    if 'device_city' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_city VARCHAR(100)'))
                    if 'device_region' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_region VARCHAR(100)'))
                    if 'device_country' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_country VARCHAR(100)'))
                    if 'device_location_consent' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_location_consent VARCHAR(20)'))
                    if 'device_location_timestamp' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN device_location_timestamp DATETIME'))
                    if 'camera_permission' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN camera_permission VARCHAR(20) DEFAULT "not_requested"'))
                    if 'snapshot_path' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN snapshot_path VARCHAR(255)'))
                    if 'snapshot_timestamp' not in cols:
                        conn.execute(text('ALTER TABLE visits ADD COLUMN snapshot_timestamp DATETIME'))
                    conn.commit()
        except Exception:
            pass

    # CLI Commands
    @app.cli.command('init-db')
    def init_db():
        """Initialize database tables and create initial administrator account."""
        with app.app_context():
            db.create_all()
            ensure_schema_updated()
            
            # Retention setting default
            if not SystemSetting.get('retention_days'):
                SystemSetting.set('retention_days', '90')

            admin_user = app.config.get('ADMIN_USERNAME', 'admin')
            admin_pass = app.config.get('ADMIN_PASSWORD', 'AdminPass123!')
            admin_email = app.config.get('ADMIN_EMAIL', 'admin@securetracker.local')

            admin = Admin.query.filter_by(username=admin_user).first()
            if not admin:
                admin = Admin(
                    username=admin_user,
                    email=admin_email,
                    role='admin'
                )
                admin.set_password(admin_pass)
                db.session.add(admin)
                db.session.commit()
                print(f"[SUCCESS] Database initialized. Admin '{admin_user}' created.")
            else:
                print(f"[INFO] Admin '{admin_user}' already exists.")

    @app.cli.command('purge-data')
    def purge_data():
        """Purge visit records older than the configured retention policy."""
        with app.app_context():
            days = int(SystemSetting.get('retention_days', 90))
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            old_visits = Visit.query.filter(Visit.timestamp < cutoff).all()
            for v in old_visits:
                if v.snapshot_path:
                    try:
                        abs_p = os.path.join(BASE_DIR, 'instance', v.snapshot_path)
                        if os.path.exists(abs_p):
                            os.remove(abs_p)
                    except Exception:
                        pass
                db.session.delete(v)
            purged = len(old_visits)
            db.session.commit()
            print(f"[SUCCESS] Purged {purged} visit records older than {days} days.")

    return app

# WSGI application instance
app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not SystemSetting.get('retention_days'):
            SystemSetting.set('retention_days', '90')
        admin_user = app.config.get('ADMIN_USERNAME', 'admin')
        if not Admin.query.filter_by(username=admin_user).first():
            admin = Admin(
                username=admin_user,
                email=app.config.get('ADMIN_EMAIL', 'admin@securetracker.local'),
                role='admin'
            )
            admin.set_password(app.config.get('ADMIN_PASSWORD', 'AdminPass123!'))
            db.session.add(admin)
            db.session.commit()
            print(f"[AUTO-INIT] Created default administrator '{admin_user}'")

    port = int(os.environ.get('PORT', 5000))
    print(f"[*] Starting Secure Live Tracker development server on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)
