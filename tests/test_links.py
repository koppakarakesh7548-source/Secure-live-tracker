from datetime import datetime, timedelta, timezone
from models import TrackingLink, db
from utils.security import generate_secure_token, validate_target_url

def test_token_randomness_and_uniqueness():
    """Verify minimum 128 bits of randomness (>20 chars from 62-char alphabet) and uniqueness."""
    tokens = set()
    for _ in range(100):
        tok = generate_secure_token(22)
        assert len(tok) == 22
        assert tok.isalnum()
        tokens.add(tok)
    # Ensure all 100 generated tokens are unique
    assert len(tokens) == 100

def test_url_validation_valid():
    valid_urls = [
        'https://example.com',
        'http://example.org/page?query=param',
        'https://sub.domain.co.uk/path/file.html#hash'
    ]
    for url in valid_urls:
        ok, res = validate_target_url(url)
        assert ok is True
        assert res == url

def test_url_validation_invalid():
    invalid_urls = [
        'javascript:alert(1)',
        'data:text/html,<script>alert(1)</script>',
        'ftp://example.com/file',
        'file:///etc/passwd',
        'not-a-valid-url',
        '',
        None
    ]
    for url in invalid_urls:
        ok, res = validate_target_url(url)
        assert ok is False

def test_create_link_endpoint_valid(auth_client, app):
    res = auth_client.post('/dashboard/links/create', data={
        'name': 'New Marketing Campaign',
        'target_url': 'https://example.com/destination',
        'description': 'Marketing tracking link test'
    }, follow_redirects=False)

    assert res.status_code == 302
    with app.app_context():
        link = TrackingLink.query.filter_by(name='New Marketing Campaign').first()
        assert link is not None
        assert link.target_url == 'https://example.com/destination'
        assert link.active is True
        assert len(link.token) == 22

def test_create_link_endpoint_invalid_url(auth_client):
    res = auth_client.post('/dashboard/links/create', data={
        'name': 'Bad URL Test',
        'target_url': 'javascript:alert(1)'
    })
    assert res.status_code == 400
    assert b'Invalid Target URL' in res.data

def test_toggle_link_status(auth_client, sample_link, app):
    # Toggle to inactive
    res = auth_client.post(f'/dashboard/links/{sample_link.id}/toggle', follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        l = db.session.get(TrackingLink, sample_link.id)
        assert l.active is False

    # Toggle back to active
    res = auth_client.post(f'/dashboard/links/{sample_link.id}/toggle', follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        l = db.session.get(TrackingLink, sample_link.id)
        assert l.active is True

def test_set_expiration_endpoint(auth_client, sample_link, app):
    future_time = (datetime.now(timezone.utc) + timedelta(days=5)).strftime('%Y-%m-%dT%H:%M')
    res = auth_client.post(f'/dashboard/links/{sample_link.id}/expiration', data={
        'expires_at': future_time
    }, follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        l = db.session.get(TrackingLink, sample_link.id)
        assert l.expires_at is not None

def test_search_and_filter_links(auth_client, sample_link):
    # Search by token
    res = auth_client.get(f'/dashboard/links/?q={sample_link.token}')
    assert res.status_code == 200
    assert sample_link.name.encode() in res.data

    # Filter by status
    res_active = auth_client.get('/dashboard/links/?status=active')
    assert res_active.status_code == 200

def test_delete_link(auth_client, sample_link, app):
    link_id = sample_link.id
    res = auth_client.post(f'/dashboard/links/{link_id}/delete', follow_redirects=True)
    assert res.status_code == 200
    with app.app_context():
        assert db.session.get(TrackingLink, link_id) is None
