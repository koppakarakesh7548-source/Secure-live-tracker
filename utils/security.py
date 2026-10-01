import ipaddress
import re
import secrets
import string
from urllib.parse import urlparse
from flask import request, current_app

# Cryptographically secure random token alphabet: unambiguous alphanumeric characters
TOKEN_ALPHABET = string.ascii_letters + string.digits

DEFAULT_TRUSTED_PROXIES = ['127.0.0.1', '::1', '10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16']

def generate_secure_token(length=10):
    """Generate a cryptographically secure random alphanumeric token."""
    return ''.join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))

def validate_target_url(url):
    """
    Validate target URL:
    - Must start with http:// or https://
    - Must have a valid network location (host)
    - Must not use forbidden schemes (javascript, data, vbscript, file, etc.)
    - Must not contain control characters or dangerous characters
    Returns (is_valid: bool, cleaned_url_or_error: str)
    """
    if not url or not isinstance(url, str):
        return False, "Target URL is required."
    
    url = url.strip()
    if len(url) > 1024:
        return False, "Target URL exceeds maximum length of 1024 characters."

    # Check for forbidden control characters
    if re.search(r'[\r\n\t\x00]', url):
        return False, "Target URL contains illegal characters."

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Malformed URL format."

    if parsed.scheme.lower() not in ('http', 'https'):
        return False, "Target URL must use either HTTP or HTTPS protocol."

    if not parsed.netloc:
        return False, "Target URL must contain a valid domain or host name."

    # Prevent scheme manipulation like javascript: or data:
    forbidden_terms = ['javascript:', 'data:', 'vbscript:', 'file:']
    lower_url = url.lower()
    for term in forbidden_terms:
        if term in lower_url and not lower_url.startswith('http'):
            return False, f"URL scheme containing '{term}' is strictly prohibited."

    return True, url

def clean_and_validate_ip(ip_str):
    """
    Clean, normalize and validate an IPv4 or IPv6 string.
    Strips ports, bracket notations, and whitespace.
    Returns normalized string IP or None if invalid.
    """
    if not ip_str or not isinstance(ip_str, str):
        return None
    val = ip_str.strip()
    if not val:
        return None

    # Handle IPv6 in brackets e.g. [2001:db8::1] or [2001:db8::1]:8080
    if val.startswith('[') and ']' in val:
        val = val.split(']')[0].lstrip('[')
    # Handle IPv4 with port e.g. 192.0.2.1:54321
    elif ':' in val and val.count(':') == 1:
        val = val.split(':')[0]

    try:
        parsed = ipaddress.ip_address(val)
        return str(parsed)
    except ValueError:
        return None

def is_ip_in_trusted_network(ip_str, trusted_list=None):
    """Check if an IP address belongs to a list of trusted proxies or subnets."""
    if not ip_str:
        return False
    try:
        ip_obj = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if trusted_list is None:
        trusted_list = DEFAULT_TRUSTED_PROXIES

    for item in trusted_list:
        item = item.strip()
        if not item:
            continue
        try:
            if '/' in item:
                net = ipaddress.ip_network(item, strict=False)
                if ip_obj in net:
                    return True
            else:
                trusted_obj = ipaddress.ip_address(item)
                if ip_obj == trusted_obj:
                    return True
        except ValueError:
            continue
    return False

def get_client_ip():
    """
    Safely extract client IP address respecting trusted reverse proxies.
    
    Security Controls:
    1. Verifies if immediate connection (remote_addr) is a trusted proxy.
    2. If remote_addr is UNTRUSTED, headers like X-Forwarded-For or CF-Connecting-IP
       are treated as potential client spoofing and strictly IGNORED.
    3. If remote_addr IS from trusted proxy infrastructure:
       - Prioritizes CF-Connecting-IP (Cloudflare edge authoritative header).
       - Checks True-Client-IP and X-Real-IP.
       - Evaluates X-Forwarded-For by parsing from right-to-left to find the genuine client IP.
    4. Validates IPv4 and IPv6 syntax.
    5. Falls back safely to request.remote_addr.
    """
    if not request:
        return "127.0.0.1"

    remote_addr = clean_and_validate_ip(request.remote_addr) or "127.0.0.1"

    # Get configured trusted proxy subnets
    trusted_proxies = None
    try:
        if current_app:
            cfg_proxies = current_app.config.get('TRUSTED_PROXIES')
            if isinstance(cfg_proxies, (list, tuple)):
                trusted_proxies = list(cfg_proxies)
            elif isinstance(cfg_proxies, str):
                trusted_proxies = [p.strip() for p in cfg_proxies.split(',') if p.strip()]
    except Exception:
        pass

    if trusted_proxies is None:
        trusted_proxies = DEFAULT_TRUSTED_PROXIES

    # Anti-spoofing check: If immediate connection is NOT from trusted proxy, DO NOT trust headers!
    if not is_ip_in_trusted_network(remote_addr, trusted_proxies):
        return remote_addr

    # Remote address is trusted proxy/tunnel: safely evaluate headers

    # 1. Cloudflare edge header (guaranteed by Cloudflare Tunnel / CDN)
    cf_ip = clean_and_validate_ip(request.headers.get('CF-Connecting-IP'))
    if cf_ip:
        return cf_ip

    # 2. True-Client-IP
    true_ip = clean_and_validate_ip(request.headers.get('True-Client-IP'))
    if true_ip:
        return true_ip

    # 3. X-Real-IP
    real_ip = clean_and_validate_ip(request.headers.get('X-Real-IP'))
    if real_ip:
        return real_ip

    # 4. X-Forwarded-For: traverse right-to-left to extract first untrusted client IP
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        parts = [clean_and_validate_ip(p) for p in xff.split(',')]
        valid_ips = [ip for ip in parts if ip is not None]
        if valid_ips:
            # Right-to-left search for client IP outside trusted proxy range
            for candidate in reversed(valid_ips):
                if not is_ip_in_trusted_network(candidate, trusted_proxies):
                    return candidate
            # If all are in private/trusted ranges, return the original leftmost client
            return valid_ips[0]

    return remote_addr

def get_public_base_url():
    """
    Retrieve the configured public HTTPS base URL for generating shareable tracking links.
    Never outputs localhost or 127.0.0.1 if a public URL is configured.
    """
    try:
        configured = current_app.config.get('PUBLIC_BASE_URL', '').rstrip('/')
        if configured:
            return configured
    except Exception:
        pass

    # Check reverse proxy headers if public URL is not explicitly configured
    forwarded_host = request.headers.get('X-Forwarded-Host', '')
    forwarded_proto = request.headers.get('X-Forwarded-Proto', 'https')
    if forwarded_host and not (forwarded_host.startswith('127.0.0.1') or forwarded_host.startswith('localhost')):
        return f"{forwarded_proto}://{forwarded_host}"

    if request.host and not (request.host.startswith('127.0.0.1') or request.host.startswith('localhost')):
        scheme = 'https' if request.is_secure else 'http'
        return f"{scheme}://{request.host}"

    return request.url_root.rstrip('/')

def add_security_headers(response):
    """Inject strict security headers into HTTP response."""
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
        "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Explicitly prohibit camera and microphone while permitting voluntary geolocation prompt on self
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(self)'
    
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response
