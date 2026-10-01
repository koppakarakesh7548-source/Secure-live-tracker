from utils.geo import get_approximate_geolocation, is_private_or_loopback, GeolocationResult, normalize_country

def test_private_and_loopback_ip_ranges():
    """Verify Section 9: Private & Loopback IPs must return Local Network without hitting external API."""
    private_ips = [
        '127.0.0.1',
        '127.0.0.2',
        '10.0.0.1',
        '10.254.0.1',
        '172.16.0.1',
        '172.31.255.254',
        '192.168.1.1',
        '192.168.0.105',
        '::1'
    ]
    for ip in private_ips:
        assert is_private_or_loopback(ip) is True
        res = get_approximate_geolocation(ip)
        assert res.country == "Local Network (Private/Loopback)"
        assert res.region is None
        assert res.city is None
        assert res.provider == "internal"
        # Tuple unpacking compatibility test
        c, r, ct = res
        assert c == "Local Network (Private/Loopback)"

def test_public_ip_failure_returns_location_unavailable():
    """Verify Section 3: If provider fails or is unreachable, return Location unavailable. Never invent location."""
    # Invalid or non-routable IP to force provider failure
    res = get_approximate_geolocation("198.51.100.999")
    assert res.country == "Location unavailable"
    assert res.region is None
    assert res.city is None
    assert res.location_display == "Location unavailable"

def test_accuracy_radius_display_formatting():
    """Verify Section 6: When accuracy radius exists, display it as (~50 km accuracy radius)."""
    res = GeolocationResult(
        country="India",
        region="Karnataka",
        city="Bengaluru",
        accuracy_radius=50,
        provider="ipinfo"
    )
    assert res.location_display == "Bengaluru, Karnataka, India (~50 km accuracy radius)"

def test_regional_and_country_granularity_display():
    """Verify Section 3 & 6: Display regional or country level when city is uncertain."""
    # Only region and country
    res_region = GeolocationResult(
        country="India",
        region="Karnataka",
        city=None
    )
    assert res_region.location_display == "Karnataka, India"

    # Only country
    res_country = GeolocationResult(
        country="India",
        region=None,
        city=None
    )
    assert res_country.location_display == "India"

def test_iso_country_normalization():
    """Verify ISO alpha-2 codes normalize to full country names."""
    assert normalize_country("US") == "United States"
    assert normalize_country("IN") == "India"
    assert normalize_country("GB") == "United Kingdom"
    assert normalize_country("DE") == "Germany"
    assert normalize_country("Unknown") == "Unknown"

def test_geolocation_result_tuple_unpacking():
    """Verify GeolocationResult can be unpacked as 3-tuple (country, region, city)."""
    res = GeolocationResult(
        country="India",
        region="Karnataka",
        city="Bengaluru",
        accuracy_radius=50,
        provider="ipinfo"
    )
    c, r, ct = res
    assert c == "India"
    assert r == "Karnataka"
    assert ct == "Bengaluru"
    assert res.accuracy_radius == 50
    assert res.provider == "ipinfo"

def test_provider_fallback_execution(monkeypatch):
    """Verify Section 2: If primary provider fails, fallback provider is executed."""
    import utils.geo as geo_mod

    def failing_primary(ip, api_key=None, timeout=2.5):
        return None

    def successful_secondary(ip, api_key=None, timeout=2.5):
        return GeolocationResult(
            country="India",
            region="Karnataka",
            city="Bengaluru",
            accuracy_radius=50,
            confidence_score=0.85,
            provider="secondary_mock"
        )

    monkeypatch.setitem(geo_mod.PROVIDERS, 'mock_fail', failing_primary)
    monkeypatch.setitem(geo_mod.PROVIDERS, 'mock_succ', successful_secondary)

    # Call with mock_fail as primary
    res = geo_mod.get_approximate_geolocation("8.8.8.8", primary_provider='mock_fail')
    assert res is not None
    # Must have gotten data from fallback chain
    assert res.country is not None
    assert res.country != "Location unavailable"

def test_validate_coordinates():
    from utils.geo import validate_coordinates
    # Valid
    ok, lat, lon, acc = validate_coordinates(17.3850, 78.4867, 35)
    assert ok is True
    assert lat == 17.3850
    assert lon == 78.4867
    assert acc == 35.0

    # Negative accuracy invalid
    ok, _, _, _ = validate_coordinates(17.3850, 78.4867, -10)
    assert ok is False

    # Out of range lat/lon
    ok, _, _, _ = validate_coordinates(95.0, 78.4867, 30)
    assert ok is False
    ok, _, _, _ = validate_coordinates(17.3850, 200.0, 30)
    assert ok is False

    # Non-numeric
    ok, _, _, _ = validate_coordinates("invalid", "coords", 30)
    assert ok is False

def test_reverse_geocode_coordinates(monkeypatch):
    from utils.geo import reverse_geocode_coordinates
    import requests

    class MockResponse:
        status_code = 200
        def json(self):
            return {
                'city': 'Hyderabad',
                'principalSubdivision': 'Telangana',
                'countryName': 'India'
            }

    monkeypatch.setattr(requests, 'get', lambda *args, **kwargs: MockResponse())
    city, region, country = reverse_geocode_coordinates(17.3850, 78.4867)
    assert city == 'Hyderabad'
    assert region == 'Telangana'
    assert country == 'India'

