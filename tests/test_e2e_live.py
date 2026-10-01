import json
import pytest
from app import create_app, db
from models import Admin, TrackingLink, Visit, SystemSetting
from utils.security import validate_target_url

def test_full_primary_workflow():
    """
    Test the complete primary workflow as specified:
    Admin -> Admin Login -> Dashboard -> Enter Target URL -> Generate Unique Tracking Link
    -> Copy/Share Tracking Link -> Visitor Opens Tracking Link -> Consent Page
    -> Visitor chooses [ Allow & Continue ] OR [ Deny & Continue ]
    -> If Allow: Collect permitted info, save, redirect to target URL
    -> If Deny: Do not collect optional visitor info, record consent decision, redirect to target URL
    """
    app = create_app('testing')
    app.url_map.strict_slashes = False
    client = app.test_client()

    with app.app_context():
        db.create_all()
        # 1. Create Admin
        admin = Admin(username='sysadmin', email='sysadmin@example.com', role='admin')
        admin.set_password('AdminPassword2026!')
        db.session.add(admin)
        db.session.commit()

        # 2. Admin Login
        login_res = client.post('/login', data={
            'username': 'sysadmin',
            'password': 'AdminPassword2026!'
        }, follow_redirects=True)
        assert login_res.status_code == 200
        assert b'Telemetry Overview' in login_res.data

        # 3. Enter Target URL & Generate Unique Tracking Link
        target_destination = 'https://example.com/product'
        create_res = client.post('/dashboard/links/create', data={
            'name': 'Live Verification Campaign',
            'target_url': target_destination,
            'description': 'End-to-end verification test link'
        }, follow_redirects=True)
        assert create_res.status_code == 200

        link = TrackingLink.query.filter_by(name='Live Verification Campaign').first()
        assert link is not None
        assert link.target_url == target_destination
        assert link.active is True
        token = link.token

        # 4. Visitor Opens Tracking Link (/track/<token>)
        # Before consent, NO visit records exist!
        assert Visit.query.filter_by(tracking_link_id=link.id).count() == 0

        visitor_client = app.test_client()
        consent_page_res = visitor_client.get(f'/track/{token}')
        assert consent_page_res.status_code == 200
        assert b'SECURE LIVE TRACKER' in consent_page_res.data
        assert b'Educational Cybersecurity &amp; Security Awareness' in consent_page_res.data
        assert b'Approximate location is derived from IP information and is not precise GPS location' in consent_page_res.data
        assert b'ALLOW &amp; CONTINUE' in consent_page_res.data
        assert b'DENY &amp; CONTINUE' in consent_page_res.data

        # Check that simply opening the page DID NOT log any visit yet!
        assert Visit.query.filter_by(tracking_link_id=link.id).count() == 0

        # 5. Visitor 1 chooses: [ Allow & Continue ]
        allow_payload = {
            'decision': 'allow',
            'screen_width': 1920,
            'screen_height': 1080,
            'language': 'en-US',
            'timezone': 'America/New_York'
        }
        allow_res = visitor_client.post(
            f'/track/{token}/decide',
            json=allow_payload,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
        )
        assert allow_res.status_code == 200
        allow_data = allow_res.get_json()
        assert allow_data['success'] is True
        assert allow_data['redirect_url'] == target_destination

        # Verify allowed visit in database
        allowed_visit = Visit.query.filter_by(tracking_link_id=link.id, consent_status='granted').first()
        assert allowed_visit is not None
        assert allowed_visit.screen_width == 1920
        assert allowed_visit.screen_height == 1080
        assert allowed_visit.language == 'en-US'
        assert allowed_visit.timezone == 'America/New_York'
        assert allowed_visit.ip_address is not None
        assert allowed_visit.browser == 'Chrome 120'
        assert allowed_visit.operating_system == 'Windows 10/11'
        assert allowed_visit.approximate_country is not None

        # 6. Visitor 2 chooses: [ Deny & Continue ]
        deny_payload = {
            'decision': 'deny',
            'screen_width': 2560,
            'screen_height': 1440,
            'language': 'fr-FR',
            'timezone': 'Europe/Paris'
        }
        deny_res = visitor_client.post(
            f'/track/{token}/decide',
            json=deny_payload
        )
        assert deny_res.status_code == 200
        deny_data = deny_res.get_json()
        assert deny_data['success'] is True
        assert deny_data['redirect_url'] == target_destination

        # Verify denied visit in database: strictly zero optional technical data!
        denied_visit = Visit.query.filter_by(tracking_link_id=link.id, consent_status='denied').first()
        assert denied_visit is not None
        assert denied_visit.consent_status == 'denied'
        assert denied_visit.ip_address is None
        assert denied_visit.browser is None
        assert denied_visit.operating_system is None
        assert denied_visit.screen_width is None
        assert denied_visit.screen_height is None
        assert denied_visit.language is None
        assert denied_visit.timezone is None
        assert denied_visit.approximate_country is None

        # 7. Verify Admin Dashboard & Visit Records Table
        records_res = client.get('/dashboard/visits')
        assert records_res.status_code == 200
        assert b'CONSENT GRANTED' in records_res.data
        assert b'CONSENT DENIED' in records_res.data
        assert b'&mdash; Not Collected (Denied)' in records_res.data or b'Not Collected (Denied)' in records_res.data

        # 8. Disable Link & Verify
        client.post(f'/dashboard/links/{link.id}/toggle', follow_redirects=True)
        disabled_res = visitor_client.get(f'/track/{token}')
        assert disabled_res.status_code == 410
        assert b'LINK DEACTIVATED' in disabled_res.data

        print("[SUCCESS] All primary workflow verification checks passed with 100% precision.")

if __name__ == '__main__':
    test_full_primary_workflow()
