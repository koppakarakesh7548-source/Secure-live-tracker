import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import Admin, TrackingLink, Visit, SystemSetting

@pytest.fixture
def app():
    app = create_app('testing')
    app.url_map.strict_slashes = False
    with app.app_context():
        db.create_all()
        SystemSetting.set('retention_days', '90')
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_user(app):
    with app.app_context():
        admin = Admin(
            username='testadmin',
            email='testadmin@securetracker.local',
            role='admin'
        )
        admin.set_password('CorrectPassword123!')
        db.session.add(admin)
        db.session.commit()
        admin_id = admin.id
        return db.session.get(Admin, admin_id)

@pytest.fixture
def auth_client(client, admin_user):
    client.post('/login', data={
        'username': 'testadmin',
        'password': 'CorrectPassword123!'
    }, follow_redirects=True)
    return client

@pytest.fixture
def sample_link(app, admin_user):
    with app.app_context():
        admin = Admin.query.first()
        link = TrackingLink(
            token='ValidTok123',
            name='Test Product Campaign',
            description='Test description for link',
            target_url='https://example.com/target-product',
            active=True,
            created_by_id=admin.id if admin else None
        )
        db.session.add(link)
        db.session.commit()
        link_id = link.id
        return db.session.get(TrackingLink, link_id)

@pytest.fixture
def disabled_link(app, admin_user):
    with app.app_context():
        admin = Admin.query.first()
        link = TrackingLink(
            token='DisabledTkn',
            name='Disabled Link Test',
            target_url='https://example.com/disabled-dest',
            active=False,
            created_by_id=admin.id if admin else None
        )
        db.session.add(link)
        db.session.commit()
        link_id = link.id
        return db.session.get(TrackingLink, link_id)

@pytest.fixture
def expired_link(app, admin_user):
    with app.app_context():
        admin = Admin.query.first()
        link = TrackingLink(
            token='ExpiredTkn',
            name='Expired Link Test',
            target_url='https://example.com/expired-dest',
            active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=2),
            created_by_id=admin.id if admin else None
        )
        db.session.add(link)
        db.session.commit()
        link_id = link.id
        return db.session.get(TrackingLink, link_id)
