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
    admin = Admin.query.filter_by(username=admin_user).first()
    if not admin:
        admin = Admin(
            username=admin_user,
            email=application.config.get('ADMIN_EMAIL', 'admin@securetracker.local'),
            role='admin'
        )
        admin.set_password(application.config.get('ADMIN_PASSWORD', 'AdminPass123!'))
        db.session.add(admin)
        db.session.commit()
        print(f"[WSGI INIT] Admin '{admin_user}' initialized.")

    admin_id = admin.id if admin else 1

    from models import TrackingLink
    seed_links = [
        ("DemoSecure7", "https://example.com/product", "Educational Security Awareness Demo Link"),
        ("SZWqfwf6E5", "https://example.com/product", "Demo Link"),
        ("cZTn2WOFkc", "https://dl.flipkart.com/s/IirbnyNNNN", "Flipkart Product Link"),
        ("DnkLsiESto6AfE1Jt6hEpL", "https://amzn.in/d/05UuRFzm", "Amazon Product Link"),
        ("0PJQjNyQ0xX8EEmdb96gra", "https://dl.flipkart.com/s/aVOeCEuuuN", "Flipkart Item"),
        ("4rqKYo06lX0vuOZ3LF41Pw", "https://dl.flipkart.com/s/a5QaIkuuuN", "Flipkart Item 2")
    ]
    for token, target, title in seed_links:
        if not TrackingLink.query.filter_by(token=token).first():
            db.session.add(TrackingLink(
                token=token,
                target_url=target,
                name=title,
                created_by_id=admin_id
            ))
    db.session.commit()

app = application

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 5000))
    print(f"[*] Serving Secure Live Tracker via Waitress WSGI on port {port}...")
    serve(application, host='0.0.0.0', port=port, threads=6)
