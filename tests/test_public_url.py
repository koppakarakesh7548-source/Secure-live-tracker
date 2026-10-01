def test_public_base_url_rendered_in_dashboard(auth_client, sample_link, app):
    res = auth_client.get(f'/dashboard/links/{sample_link.id}')
    assert res.status_code == 200
    # Must use public base URL configured in TestingConfig (https://test-tracker.example.com)
    expected_public_url = f"https://test-tracker.example.com/track/{sample_link.token}"
    assert expected_public_url.encode() in res.data
    # Must NOT generate localhost or 127.0.0.1 for the shareable public link
    assert b"127.0.0.1:5000/track" not in res.data

def test_health_check_endpoint(client):
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data == {"status": "ok"}

