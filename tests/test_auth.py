from models import Admin

def test_password_hashing(app):
    with app.app_context():
        admin = Admin(username='hash_test')
        admin.set_password('SecretP@ssw0rd!2026')
        assert admin.password_hash is not None
        assert admin.password_hash != 'SecretP@ssw0rd!2026'
        assert admin.password_hash.startswith('scrypt:') or len(admin.password_hash) > 20
        assert admin.check_password('SecretP@ssw0rd!2026') is True
        assert admin.check_password('WrongP@ssword') is False

def test_login_successful(client, admin_user):
    res = client.post('/login', data={
        'username': 'testadmin',
        'password': 'CorrectPassword123!'
    }, follow_redirects=False)
    assert res.status_code == 302
    assert '/dashboard' in res.location

def test_login_invalid_password(client, admin_user):
    res = client.post('/login', data={
        'username': 'testadmin',
        'password': 'WrongPassword999'
    })
    assert res.status_code == 401
    assert b'Invalid administrator credentials' in res.data

def test_login_unknown_user(client, admin_user):
    res = client.post('/login', data={
        'username': 'nonexistent',
        'password': 'CorrectPassword123!'
    })
    assert res.status_code == 401
    assert b'Invalid administrator credentials' in res.data

def test_login_missing_fields(client):
    res = client.post('/login', data={'username': ''})
    assert res.status_code == 400

def test_logout(auth_client):
    res = auth_client.post('/logout', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location

def test_unauthorized_dashboard_access_redirects(client):
    res = client.get('/dashboard/', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location

def test_unauthorized_links_access_redirects(client):
    res = client.get('/dashboard/links/', follow_redirects=False)
    assert res.status_code == 302
    assert '/login' in res.location
