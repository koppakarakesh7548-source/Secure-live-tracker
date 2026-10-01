from models import Visit, TrackingLink, db

def test_track_route_renders_consent_page(client, sample_link):
    res = client.get(f'/track/{sample_link.token}')
    assert res.status_code == 200
    assert b'SECURE LIVE TRACKER' in res.data
    assert b'Educational Cybersecurity &amp; Security Awareness' in res.data or b'Educational Cybersecurity' in res.data
    assert b'Allow &amp; Continue' in res.data or b'ALLOW &amp; CONTINUE' in res.data
    assert b'Deny &amp; Continue' in res.data or b'DENY &amp; CONTINUE' in res.data
    assert b'Approximate location is derived from IP information' in res.data

def test_track_route_invalid_token(client):
    res = client.get('/track/NonExistentToken999')
    assert res.status_code == 404
    assert b'TRACKING LINK NOT FOUND' in res.data

def test_track_route_disabled_link(client, disabled_link):
    res = client.get(f'/track/{disabled_link.token}')
    assert res.status_code == 410
    assert b'LINK DEACTIVATED' in res.data

def test_track_route_expired_link(client, expired_link):
    res = client.get(f'/track/{expired_link.token}')
    assert res.status_code == 410
    assert b'LINK EXPIRED' in res.data

def test_consent_allow_decision_json(client, sample_link, app):
    payload = {
        'decision': 'allow',
        'screen_width': 1920,
        'screen_height': 1080,
        'language': 'en-US',
        'timezone': 'America/New_York'
    }
    res = client.post(
        f'/track/{sample_link.token}/decide',
        json=payload,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['redirect_url'] == sample_link.target_url

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id).first()
        assert visit is not None
        assert visit.consent_status == 'granted'
        assert visit.screen_width == 1920
        assert visit.screen_height == 1080
        assert visit.language == 'en-US'
        assert visit.timezone == 'America/New_York'
        assert visit.browser is not None
        assert visit.operating_system is not None
        assert visit.ip_address is not None

def test_consent_allow_decision_form(client, sample_link, app):
    res = client.post(
        f'/track/{sample_link.token}/decide',
        data={
            'decision': 'allow',
            'screen_width': '1440',
            'screen_height': '900',
            'language': 'en-GB',
            'timezone': 'Europe/London'
        },
        follow_redirects=False
    )
    assert res.status_code == 302
    assert res.location == sample_link.target_url

def test_consent_deny_decision_json(client, sample_link, app):
    payload = {
        'decision': 'deny',
        'screen_width': 2560,
        'screen_height': 1440,
        'language': 'de-DE',
        'timezone': 'Europe/Berlin'
    }
    res = client.post(
        f'/track/{sample_link.token}/decide',
        json=payload
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['redirect_url'] == sample_link.target_url

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id, consent_status='denied').first()
        assert visit is not None
        assert visit.consent_status == 'denied'
        # Mandatory privacy verification: NO optional parameters collected!
        assert visit.ip_address is None
        assert visit.browser is None
        assert visit.operating_system is None
        assert visit.screen_width is None
        assert visit.screen_height is None
        assert visit.language is None
        assert visit.timezone is None
        assert visit.approximate_country is None

def test_redirect_manipulation_prevention(client, sample_link):
    # Attempting to override redirect via query param or post body
    res = client.post(
        f'/track/{sample_link.token}/decide?redirect=https://evil-attacker.com',
        json={'decision': 'allow', 'target_url': 'https://evil-attacker.com'}
    )
    assert res.status_code == 200
    data = res.get_json()
    # Destination must strictly remain the administrator configured target_url
    assert data['redirect_url'] == sample_link.target_url

def test_api_track_consent_with_battery(client, sample_link, app):
    payload = {
        'decision': 'allow',
        'screen_width': 1920,
        'screen_height': 1080,
        'language': 'en-US',
        'timezone': 'America/New_York',
        'battery_percentage': 82,
        'battery_charging': True
    }
    res = client.post(
        f'/api/track/{sample_link.token}/consent',
        json=payload,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['redirect_url'] == sample_link.target_url

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id).order_by(Visit.id.desc()).first()
        assert visit is not None
        assert visit.consent_status == 'granted'
        assert visit.battery_percentage == 82
        assert visit.battery_charging is True
        assert visit.battery_display == '82%'
        assert visit.charging_display == 'Yes'

def test_api_track_consent_unsupported_battery(client, sample_link, app):
    payload = {
        'decision': 'allow',
        'screen_width': 1440,
        'screen_height': 900,
        'language': 'en-US',
        'timezone': 'America/Chicago',
        'battery_percentage': None,
        'battery_charging': None
    }
    res = client.post(
        f'/api/track/{sample_link.token}/consent',
        json=payload
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id).order_by(Visit.id.desc()).first()
        assert visit is not None
        assert visit.consent_status == 'granted'
        assert visit.battery_percentage is None
        assert visit.battery_charging is None
        assert visit.battery_display == 'Not available'
        assert visit.charging_display == 'Not available'

def test_api_track_consent_denied(client, sample_link, app):
    payload = {
        'decision': 'deny',
        'battery_percentage': 95,
        'battery_charging': False
    }
    res = client.post(
        f'/api/track/{sample_link.token}/consent',
        json=payload
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert data['redirect_url'] == sample_link.target_url

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id, consent_status='denied').order_by(Visit.id.desc()).first()
        assert visit is not None
        assert visit.consent_status == 'denied'
        assert visit.battery_percentage is None
        assert visit.battery_charging is None
        assert visit.ip_address is None
        assert visit.device_location_consent is None
        assert visit.device_latitude is None

def test_api_track_device_location_granted(client, sample_link, app, monkeypatch):
    import utils.geo as geo_mod
    monkeypatch.setattr(geo_mod, 'reverse_geocode_coordinates', lambda lat, lon: ('Hyderabad', 'Telangana', 'India'))

    payload = {
        'decision': 'allow',
        'screen_width': 1920,
        'screen_height': 1080,
        'language': 'en-IN',
        'timezone': 'Asia/Kolkata',
        'battery_percentage': 85,
        'battery_charging': True,
        'device_location_consent': 'granted',
        'device_latitude': 17.3850,
        'device_longitude': 78.4867,
        'device_accuracy_meters': 35.2
    }
    res = client.post(
        f'/api/track/{sample_link.token}/consent',
        json=payload
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id).order_by(Visit.id.desc()).first()
        assert visit is not None
        assert visit.consent_status == 'granted'
        assert visit.device_location_consent == 'granted'
        assert visit.device_permission_display == 'Granted'
        assert visit.device_latitude == 17.3850
        assert visit.device_longitude == 78.4867
        assert visit.device_accuracy_meters == 35.2
        assert visit.device_accuracy_display == '~35 meters'
        assert visit.device_city == 'Hyderabad'
        assert visit.device_region == 'Telangana'
        assert visit.device_country == 'India'
        assert visit.device_location_display == 'Hyderabad, Telangana, India'
        # IP approximate location remains separate!
        assert visit.location_display is not None

def test_api_track_device_location_denied(client, sample_link, app):
    payload = {
        'decision': 'allow',
        'screen_width': 1440,
        'screen_height': 900,
        'device_location_consent': 'denied'
    }
    res = client.post(
        f'/api/track/{sample_link.token}/consent',
        json=payload
    )
    assert res.status_code == 200

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id).order_by(Visit.id.desc()).first()
        assert visit is not None
        assert visit.consent_status == 'granted'
        assert visit.device_location_consent == 'denied'
        assert visit.device_permission_display == 'Denied'
        assert visit.device_location_display == 'Not shared'
        assert visit.device_accuracy_display == 'Not available'
        assert visit.device_latitude is None
        assert visit.device_longitude is None

def test_api_track_continue_without_location(client, sample_link, app):
    payload = {
        'decision': 'allow',
        'screen_width': 1440,
        'screen_height': 900,
        'device_location_consent': 'not_requested'
    }
    res = client.post(
        f'/api/track/{sample_link.token}/consent',
        json=payload
    )
    assert res.status_code == 200

    with app.app_context():
        visit = Visit.query.filter_by(tracking_link_id=sample_link.id).order_by(Visit.id.desc()).first()
        assert visit is not None
        assert visit.consent_status == 'granted'
        assert visit.device_location_consent == 'not_requested'
        assert visit.device_permission_display == 'Not requested'
        assert visit.device_location_display == 'Not shared'
        assert visit.device_latitude is None


