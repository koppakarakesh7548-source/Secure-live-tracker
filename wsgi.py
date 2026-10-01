import os
from app import create_app, db
from models import Admin, SystemSetting

# Create production WSGI application
env = os.environ.get('FLASK_ENV', 'production')
application = create_app(env)

# Initialize database on WSGI boot if not yet initialized
with application.app_context():
    db.create_all()
    if not SystemSetting.get('retention_days'):
        SystemSetting.set('retention_days', '90')
    admin_user = application.config.get('ADMIN_USERNAME', 'admin')
    if not Admin.query.filter_by(username=admin_user).first():
        admin = Admin(
            username=admin_user,
            email=application.config.get('ADMIN_EMAIL', 'admin@securetracker.local'),
            role='admin'
        )
        admin.set_password(application.config.get('ADMIN_PASSWORD', 'AdminPass123!'))
        db.session.add(admin)
        db.session.commit()
        print(f"[WSGI INIT] Admin '{admin_user}' initialized.")

app = application

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 5000))
    print(f"[*] Serving Secure Live Tracker via Waitress WSGI on port {port}...")
    serve(application, host='0.0.0.0', port=port, threads=6)
