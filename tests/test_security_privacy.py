from datetime import datetime, timedelta, timezone
from models import Visit, TrackingLink, SystemSetting, db

def test_security_headers_present(client):
    res = client.get('/')
    assert 'Content-Security-Policy' in res.headers
    assert 'X-Content-Type-Options' in res.headers
    assert res.headers['X-Content-Type-Options'] == 'nosniff'
    assert 'X-Frame-Options' in res.headers
    assert res.headers['X-Frame-Options'] == 'DENY'
    assert 'Permissions-Policy' in res.headers
    assert 'camera=()' in res.headers['Permissions-Policy']
    assert 'microphone=()' in res.headers['Permissions-Policy']
    assert 'geolocation=(self)' in res.headers['Permissions-Policy']

def test_delete_individual_visit_record(auth_client, sample_link, app):
    with app.app_context():
        visit = Visit(
            tracking_link_id=sample_link.id,
            consent_status='granted',
            ip_address='192.168.1.100'
        )
        db.session.add(visit)
        db.session.commit()
        visit_id = visit.id

    res = auth_client.post(f'/dashboard/visits/{visit_id}/delete', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        assert db.session.get(Visit, visit_id) is None

def test_cascade_delete_link_removes_visits(auth_client, sample_link, app):
    with app.app_context():
        v1 = Visit(tracking_link_id=sample_link.id, consent_status='granted')
        v2 = Visit(tracking_link_id=sample_link.id, consent_status='denied')
        db.session.add_all([v1, v2])
        db.session.commit()
        assert Visit.query.filter_by(tracking_link_id=sample_link.id).count() == 2

    # Delete the link
    res = auth_client.post(f'/dashboard/links/{sample_link.id}/delete', follow_redirects=True)
    assert res.status_code == 200

    with app.app_context():
        assert db.session.get(TrackingLink, sample_link.id) is None
        # All associated visits must be deleted
        assert Visit.query.filter_by(tracking_link_id=sample_link.id).count() == 0

def test_data_retention_purge(app, sample_link):
    with app.app_context():
        SystemSetting.set('retention_days', '30')
        now = datetime.now(timezone.utc)
        
        # Recent visit (10 days old)
        recent_visit = Visit(
            tracking_link_id=sample_link.id,
            timestamp=now - timedelta(days=10),
            consent_status='granted'
        )
        # Old visit (45 days old)
        old_visit = Visit(
            tracking_link_id=sample_link.id,
            timestamp=now - timedelta(days=45),
            consent_status='granted'
        )
        db.session.add_all([recent_visit, old_visit])
        db.session.commit()

        # Execute retention purge
        days = int(SystemSetting.get('retention_days', 30))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        purged = Visit.query.filter(Visit.timestamp < cutoff).delete(synchronize_session=False)
        db.session.commit()

        assert purged == 1
        assert Visit.query.count() == 1
        remaining = Visit.query.first()
        assert remaining.id == recent_visit.id

def test_client_ip_anti_spoofing_untrusted_direct(app):
    from utils.security import get_client_ip
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '203.0.113.195'}, headers={
        'X-Forwarded-For': '8.8.8.8, 1.1.1.1',
        'CF-Connecting-IP': '8.8.4.4',
        'X-Real-IP': '9.9.9.9'
    }):
        # Direct untrusted connection: spoofed forwarding headers MUST be ignored!
        ip = get_client_ip()
        assert ip == '203.0.113.195'

def test_client_ip_trusted_proxy_cf_header(app):
    from utils.security import get_client_ip
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}, headers={
        'CF-Connecting-IP': '198.51.100.42'
    }):
        # Trusted reverse proxy tunnel sends Cloudflare client IP
        ip = get_client_ip()
        assert ip == '198.51.100.42'

def test_client_ip_trusted_proxy_x_forwarded_for(app):
    from utils.security import get_client_ip
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}, headers={
        'X-Forwarded-For': '198.51.100.77, 10.0.0.5'
    }):
        # Traverses right-to-left past trusted internal proxy 10.0.0.5 to find remote client
        ip = get_client_ip()
        assert ip == '198.51.100.77'

def test_client_ip_ipv6_handling(app):
    from utils.security import get_client_ip
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '::1'}, headers={
        'CF-Connecting-IP': '2001:db8:85a3::8a2e:370:7334'
    }):
        ip = get_client_ip()
        assert ip == '2001:db8:85a3::8a2e:370:7334'

