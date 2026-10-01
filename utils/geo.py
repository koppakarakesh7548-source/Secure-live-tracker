import ipaddress
import logging
import os
import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Standard ISO-3166-1 alpha-2 country code mapping to English names
ISO_COUNTRY_NAMES = {
    'AF': 'Afghanistan', 'AL': 'Albania', 'DZ': 'Algeria', 'AS': 'American Samoa', 'AD': 'Andorra',
    'AO': 'Angola', 'AI': 'Anguilla', 'AQ': 'Antarctica', 'AG': 'Antigua and Barbuda', 'AR': 'Argentina',
    'AM': 'Armenia', 'AW': 'Aruba', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan',
    'BS': 'Bahamas', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus',
    'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BM': 'Bermuda', 'BT': 'Bhutan',
    'BO': 'Bolivia', 'BA': 'Bosnia and Herzegovina', 'BW': 'Botswana', 'BR': 'Brazil', 'IO': 'British Indian Ocean Territory',
    'BN': 'Brunei Darussalam', 'BG': 'Bulgaria', 'BF': 'Burkina Faso', 'BI': 'Burundi', 'KH': 'Cambodia',
    'CM': 'Cameroon', 'CA': 'Canada', 'CV': 'Cape Verde', 'KY': 'Cayman Islands', 'CF': 'Central African Republic',
    'TD': 'Chad', 'CL': 'Chile', 'CN': 'China', 'CO': 'Colombia', 'KM': 'Comoros',
    'CG': 'Congo', 'CD': 'Congo, Democratic Republic of the', 'CR': 'Costa Rica', 'CI': "Cote d'Ivoire", 'HR': 'Croatia',
    'CU': 'Cuba', 'CY': 'Cyprus', 'CZ': 'Czech Republic', 'DK': 'Denmark', 'DJ': 'Djibouti',
    'DM': 'Dominica', 'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador',
    'GQ': 'Equatorial Guinea', 'ER': 'Eritrea', 'EE': 'Estonia', 'ET': 'Ethiopia', 'FI': 'Finland',
    'FR': 'France', 'GA': 'Gabon', 'GM': 'Gambia', 'GE': 'Georgia', 'DE': 'Germany',
    'GH': 'Ghana', 'GR': 'Greece', 'GD': 'Grenada', 'GT': 'Guatemala', 'GN': 'Guinea',
    'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti', 'HN': 'Honduras', 'HK': 'Hong Kong',
    'HU': 'Hungary', 'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia', 'IR': 'Iran',
    'IQ': 'Iraq', 'IE': 'Ireland', 'IL': 'Israel', 'IT': 'Italy', 'JM': 'Jamaica',
    'JP': 'Japan', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya', 'KR': 'Korea, Republic of',
    'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': 'Laos', 'LV': 'Latvia', 'LB': 'Lebanon',
    'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libya', 'LI': 'Liechtenstein', 'LT': 'Lithuania',
    'LU': 'Luxembourg', 'MO': 'Macao', 'MK': 'North Macedonia', 'MG': 'Madagascar', 'MW': 'Malawi',
    'MY': 'Malaysia', 'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 'MX': 'Mexico',
    'MD': 'Moldova', 'MC': 'Monaco', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MA': 'Morocco',
    'MZ': 'Mozambique', 'MM': 'Myanmar', 'NA': 'Namibia', 'NP': 'Nepal', 'NL': 'Netherlands',
    'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger', 'NG': 'Nigeria', 'NO': 'Norway',
    'OM': 'Oman', 'PK': 'Pakistan', 'PA': 'Panama', 'PG': 'Papua New Guinea', 'PY': 'Paraguay',
    'PE': 'Peru', 'PH': 'Philippines', 'PL': 'Poland', 'PT': 'Portugal', 'QA': 'Qatar',
    'RO': 'Romania', 'RU': 'Russian Federation', 'RW': 'Rwanda', 'SA': 'Saudi Arabia', 'SN': 'Senegal',
    'RS': 'Serbia', 'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore', 'SK': 'Slovakia',
    'SI': 'Slovenia', 'SO': 'Somalia', 'ZA': 'South Africa', 'ES': 'Spain', 'LK': 'Sri Lanka',
    'SD': 'Sudan', 'SE': 'Sweden', 'CH': 'Switzerland', 'SY': 'Syrian Arab Republic', 'TW': 'Taiwan',
    'TJ': 'Tajikistan', 'TZ': 'Tanzania', 'TH': 'Thailand', 'TL': 'Timor-Leste', 'TG': 'Togo',
    'TT': 'Trinidad and Tobago', 'TN': 'Tunisia', 'TR': 'Turkey', 'TM': 'Turkmenistan', 'UG': 'Uganda',
    'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom', 'US': 'United States', 'UY': 'Uruguay',
    'UZ': 'Uzbekistan', 'VE': 'Venezuela', 'VN': 'Viet Nam', 'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe'
}

def normalize_country(country_raw):
    """Normalize country code or raw name to standard full name."""
    if not country_raw or not isinstance(country_raw, str):
        return None
    val = country_raw.strip()
    if len(val) == 2 and val.upper() in ISO_COUNTRY_NAMES:
        return ISO_COUNTRY_NAMES[val.upper()]
    return val

class GeolocationResult:
    """
    Standardized Geolocation Result with accuracy, confidence, and provider tracking.
    Supports tuple unpacking: country, region, city = result
    """
    def __init__(self, country=None, region=None, city=None, timezone=None,
                 accuracy_radius=None, confidence_score=None, provider=None, is_mobile=False):
        self.country = normalize_country(country) if country and country != 'Local Network (Private/Loopback)' and country != 'Location unavailable' else country
        self.region = region.strip() if region and isinstance(region, str) else None
        self.city = city.strip() if city and isinstance(city, str) else None
        self.timezone = timezone.strip() if timezone and isinstance(timezone, str) else None
        self.accuracy_radius = int(accuracy_radius) if accuracy_radius is not None else None
        self.confidence_score = float(confidence_score) if confidence_score is not None else None
        self.provider = str(provider) if provider else None
        self.is_mobile = bool(is_mobile)

    def __iter__(self):
        # Enables tuple unpacking: country, region, city = get_approximate_geolocation(...)
        return iter((self.country, self.region, self.city))

    def __getitem__(self, index):
        return (self.country, self.region, self.city)[index]

    @property
    def location_display(self):
        """Format human-readable approximate IP location."""
        if self.country == 'Local Network (Private/Loopback)':
            return 'Local Network (Private/Loopback)'
        
        parts = []
        if self.city and self.city not in ('Unknown', 'Location unavailable'):
            parts.append(self.city)
        if self.region and self.region not in ('Unknown', 'Location unavailable'):
            parts.append(self.region)
        if self.country and self.country not in ('Unknown', 'Location unavailable'):
            parts.append(self.country)

        if not parts:
            return "Location unavailable"

        base = ", ".join(parts)
        if self.accuracy_radius and self.accuracy_radius > 0:
            return f"{base} (~{self.accuracy_radius} km accuracy radius)"
        return base

    def to_dict(self):
        return {
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'timezone': self.timezone,
            'accuracy_radius': self.accuracy_radius,
            'confidence_score': self.confidence_score,
            'provider': self.provider,
            'is_mobile': self.is_mobile,
            'location_display': self.location_display
        }

    def __repr__(self):
        return f"<GeolocationResult '{self.location_display}' [provider={self.provider}]>"

def is_private_or_loopback(ip_str):
    """
    Check if an IP address belongs to loopback, private, or reserved ranges:
    - 127.0.0.1, ::1
    - 10.0.0.0/8
    - 172.16.0.0/12
    - 192.168.0.0/16
    """
    if not ip_str or not isinstance(ip_str, str):
        return False
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return ip.is_loopback or ip.is_private or ip.is_reserved or ip.is_unspecified or ip.is_link_local
    except ValueError:
        return False

# ==========================================
# Individual Geolocation Provider Callbacks
# ==========================================

def _lookup_ipinfo(ip_str, api_key=None, timeout=2.5):
    """Query IPinfo provider (https://ipinfo.io)."""
    try:
        url = f"https://ipinfo.io/{ip_str}/json"
        headers = {'User-Agent': 'SecureLiveTracker/2.0'}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
        
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            country = data.get('country')
            region = data.get('region')
            city = data.get('city')
            tz = data.get('timezone')
            
            # Filter bogon or empty response
            if data.get('bogon'):
                return None
            if not country and not region and not city:
                return None

            # Standard IPinfo city accuracy radius is ~50 km
            accuracy_radius = 50 if city else (100 if region else 250)
            confidence = 0.85 if (city and region) else (0.75 if region else 0.60)
            
            return GeolocationResult(
                country=country,
                region=region,
                city=city,
                timezone=tz,
                accuracy_radius=accuracy_radius,
                confidence_score=confidence,
                provider='ipinfo',
                is_mobile=False
            )
    except Exception as e:
        logger.warning(f"IPinfo lookup error for {ip_str}: {e}")
    return None

def _lookup_maxmind(ip_str, api_key=None, timeout=2.5):
    """
    Query MaxMind GeoIP2 Precision City web service or configured credentials.
    Supports MAXMIND_ACCOUNT_ID and MAXMIND_LICENSE_KEY or GEOLOCATION_API_KEY.
    """
    account_id = os.environ.get('MAXMIND_ACCOUNT_ID', '')
    license_key = api_key or os.environ.get('MAXMIND_LICENSE_KEY', '') or os.environ.get('GEOLOCATION_API_KEY', '')

    if not license_key:
        logger.debug("MaxMind lookup skipped: no MAXMIND_LICENSE_KEY or GEOLOCATION_API_KEY provided.")
        return None

    try:
        url = f"https://geoip.maxmind.com/geoip/v2.1/city/{ip_str}"
        auth = (account_id or license_key, license_key)
        headers = {'User-Agent': 'SecureLiveTracker/2.0'}

        response = requests.get(url, auth=auth, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            city_data = data.get('city', {})
            city = city_data.get('names', {}).get('en')

            subdivs = data.get('subdivisions', [])
            region = subdivs[0].get('names', {}).get('en') if subdivs else None

            country_data = data.get('country', {})
            country = country_data.get('names', {}).get('en') or country_data.get('iso_code')

            loc = data.get('location', {})
            accuracy_radius = loc.get('accuracy_radius', 50)
            tz = loc.get('time_zone')

            traits = data.get('traits', {})
            is_mobile = bool(traits.get('is_cellular', False))

            confidence = 0.90 if (accuracy_radius and accuracy_radius <= 25) else 0.80

            return GeolocationResult(
                country=country,
                region=region,
                city=city,
                timezone=tz,
                accuracy_radius=accuracy_radius,
                confidence_score=confidence,
                provider='maxmind',
                is_mobile=is_mobile
            )
        else:
            logger.info(f"MaxMind service returned status {response.status_code} for {ip_str}")
    except Exception as e:
        logger.warning(f"MaxMind lookup error for {ip_str}: {e}")
    return None

def _lookup_ipapi(ip_str, api_key=None, timeout=2.5):
    """Query IP-API provider (http://ip-api.com)."""
    try:
        url = f"http://ip-api.com/json/{ip_str}?fields=status,message,country,countryCode,regionName,city,timezone,mobile"
        if api_key:
            url += f"&key={api_key}"
        
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                country = data.get('country')
                region = data.get('regionName')
                city = data.get('city')
                tz = data.get('timezone')
                is_mobile = bool(data.get('mobile', False))

                accuracy_radius = 100 if is_mobile else 50
                confidence = 0.65 if is_mobile else (0.80 if city else 0.70)

                return GeolocationResult(
                    country=country,
                    region=region,
                    city=city,
                    timezone=tz,
                    accuracy_radius=accuracy_radius,
                    confidence_score=confidence,
                    provider='ip-api',
                    is_mobile=is_mobile
                )
            else:
                logger.info(f"IP-API non-success for {ip_str}: {data.get('message')}")
    except Exception as e:
        logger.warning(f"IP-API lookup error for {ip_str}: {e}")
    return None

def _lookup_ipapico(ip_str, api_key=None, timeout=2.5):
    """Query ipapi.co provider (https://ipapi.co)."""
    try:
        url = f"https://ipapi.co/{ip_str}/json/"
        headers = {'User-Agent': 'SecureLiveTracker/2.0'}
        if api_key:
            headers['Authorization'] = f"Bearer {api_key}"
            
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if not data.get('error'):
                country = data.get('country_name') or data.get('country')
                region = data.get('region')
                city = data.get('city')
                tz = data.get('timezone')

                return GeolocationResult(
                    country=country,
                    region=region,
                    city=city,
                    timezone=tz,
                    accuracy_radius=50,
                    confidence_score=0.75,
                    provider='ipapi.co',
                    is_mobile=False
                )
    except Exception as e:
        logger.warning(f"ipapi.co lookup error for {ip_str}: {e}")
    return None

PROVIDERS = {
    'ipinfo': _lookup_ipinfo,
    'maxmind': _lookup_maxmind,
    'ip-api': _lookup_ipapi,
    'ipapi.co': _lookup_ipapico
}

# ==========================================
# Main Multi-Provider Fallback Orchestrator
# ==========================================

def get_approximate_geolocation(ip_address, primary_provider=None, api_key=None, timeout=2.5):
    """
    Look up approximate geographic location derived strictly from a genuine public IP address.
    
    Architecture & Fallback:
    1. Loopback / Private IP Check:
       - Returns "Local Network (Private/Loopback)" without querying any external service.
    2. Primary Provider:
       - Configurable via GEOLOCATION_PROVIDER env (e.g. ipinfo, maxmind, ip-api).
    3. Secondary / Fallback Providers:
       - Executes fallback chain if primary fails or returns incomplete results.
       - Disagreement Resolution: Prefers provider with higher confidence / smaller accuracy radius.
    4. Mobile Network Handling:
       - Mobile/cellular IPs map to ISP gateways; does not present city as exact physical location.
       - If city confidence is low or uncertain, falls back to regional or country level.
    5. Failure Graceful Degradation:
       - If all providers fail: returns "Location unavailable". Never fabricates or guesses location.
       - Never claims to be precise GPS location.

    Returns:
        GeolocationResult: tuple-unpackable into (country, region, city)
    """
    if not ip_address or not isinstance(ip_address, str):
        return GeolocationResult(country="Location unavailable", provider="none")

    clean_ip = ip_address.strip()

    # 1. Private and Loopback IP handling (Section 9)
    if is_private_or_loopback(clean_ip):
        return GeolocationResult(
            country="Local Network (Private/Loopback)",
            region=None,
            city=None,
            timezone=None,
            accuracy_radius=None,
            confidence_score=1.0,
            provider="internal",
            is_mobile=False
        )

    # Validate IP format
    try:
        ipaddress.ip_address(clean_ip)
    except ValueError:
        return GeolocationResult(country="Location unavailable", provider="none")

    # 2. Determine provider order from configuration
    provider_name = primary_provider
    provider_key = api_key

    try:
        if current_app:
            if not provider_name:
                provider_name = current_app.config.get('GEOLOCATION_PROVIDER')
            if not provider_key:
                provider_key = current_app.config.get('GEOLOCATION_API_KEY')
    except Exception:
        pass

    if not provider_name:
        provider_name = os.environ.get('GEOLOCATION_PROVIDER', 'ipinfo').lower().strip()
    if not provider_key:
        provider_key = os.environ.get('GEOLOCATION_API_KEY', '').strip()

    fallback_name = os.environ.get('GEOLOCATION_FALLBACK_PROVIDER', 'ip-api').lower().strip()

    # Build prioritized provider execution chain without duplicates
    chain = []
    for p in [provider_name, fallback_name, 'ipinfo', 'ip-api', 'ipapi.co']:
        if p and p in PROVIDERS and p not in chain:
            chain.append(p)

    best_candidate = None

    # 3. Provider Fallback Pipeline
    for p_name in chain:
        handler = PROVIDERS[p_name]
        try:
            res = handler(clean_ip, api_key=provider_key, timeout=timeout)
            if res and res.country:
                # Handle mobile network IP gateway uncertainty (Section 5)
                # If identified as mobile network and city is uncertain, drop city to region level
                if res.is_mobile and res.confidence_score and res.confidence_score < 0.70:
                    res.city = None

                # If this provider gives solid confidence (e.g. >= 0.75), accept immediately
                if res.confidence_score and res.confidence_score >= 0.75 and res.city:
                    return res

                # Keep track of best candidate with valid geographical data
                if best_candidate is None:
                    best_candidate = res
                else:
                    # Compare confidence/accuracy: prefer provider with higher confidence or smaller accuracy radius
                    curr_score = (res.confidence_score or 0.5) - (0.001 * (res.accuracy_radius or 100))
                    best_score = (best_candidate.confidence_score or 0.5) - (0.001 * (best_candidate.accuracy_radius or 100))
                    if curr_score > best_score:
                        best_candidate = res

                # If candidate has at least city and region, return it
                if best_candidate.city and best_candidate.region:
                    return best_candidate
        except Exception as e:
            logger.warning(f"Provider {p_name} failed during fallback pipeline for {clean_ip}: {e}")
            continue

    if best_candidate:
        return best_candidate

    # 4. Total Provider Failure / Unreachable (Section 3)
    # Never invent fake data or guess nearby cities
    return GeolocationResult(
        country="Location unavailable",
        region=None,
        city=None,
        timezone=None,
        accuracy_radius=None,
        confidence_score=0.0,
        provider="fallback_exhausted",
        is_mobile=False
    )

def validate_coordinates(lat, lon, accuracy=None):
    """
    Validate latitude (-90 to +90), longitude (-180 to +180), and accuracy (>= 0).
    Returns (is_valid: bool, cleaned_lat: float, cleaned_lon: float, cleaned_accuracy: float)
    """
    if lat is None or lon is None:
        return False, None, None, None
    try:
        lat_f = float(lat)
        lon_f = float(lon)
        if not (-90.0 <= lat_f <= 90.0):
            return False, None, None, None
        if not (-180.0 <= lon_f <= 180.0):
            return False, None, None, None
        
        acc_f = None
        if accuracy is not None and accuracy != '':
            acc_f = float(accuracy)
            if acc_f < 0:
                return False, None, None, None
        return True, lat_f, lon_f, acc_f
    except (ValueError, TypeError):
        return False, None, None, None

def reverse_geocode_coordinates(latitude, longitude, timeout=3.5):
    """
    Convert (latitude, longitude) into (city, region, country) using reputable reverse-geocoding.
    Uses BigDataCloud with OpenStreetMap Nominatim fallback.
    If reverse-geocoding fails: returns (None, None, None) so dashboard shows 'Coordinates available'.
    """
    is_valid, lat_f, lon_f, _ = validate_coordinates(latitude, longitude)
    if not is_valid:
        return None, None, None

    # 1. Primary: BigDataCloud Reverse Geocoding Client API
    try:
        url = f"https://api.bigdatacloud.net/data/reverse-geocode-client?latitude={lat_f}&longitude={lon_f}&localityLanguage=en"
        resp = requests.get(url, headers={'User-Agent': 'SecureLiveTracker/2.0'}, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            city = data.get('city') or data.get('locality')
            region = data.get('principalSubdivision')
            country = data.get('countryName')
            if country or city or region:
                return city, region, country
    except Exception as e:
        logger.warning(f"BigDataCloud reverse geocoding error for ({lat_f}, {lon_f}): {e}")

    # 2. Secondary Fallback: OpenStreetMap Nominatim
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat_f}&lon={lon_f}&zoom=14&addressdetails=1"
        resp = requests.get(url, headers={'User-Agent': 'SecureLiveTracker/2.0 (contact: admin@securetracker.local)'}, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get('address', {})
            city = addr.get('city') or addr.get('town') or addr.get('village') or addr.get('municipality')
            region = addr.get('state') or addr.get('region') or addr.get('state_district')
            country = addr.get('country')
            if country or city or region:
                return city, region, country
    except Exception as e:
        logger.warning(f"Nominatim reverse geocoding error for ({lat_f}, {lon_f}): {e}")

    # Fallback if external reverse geocoding is unavailable: return None without inventing a city
    return None, None, None

