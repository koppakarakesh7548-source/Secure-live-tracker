from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, jsonify, abort
from models import db, TrackingLink, Visit
from utils.security import get_client_ip
from utils.geo import get_approximate_geolocation, validate_coordinates, reverse_geocode_coordinates
from utils.ua_parser import parse_user_agent

tracker_bp = Blueprint('tracker', __name__)

@tracker_bp.route('/track/<token>')
def track(token):
    """
    Public tracking route.
    Validates token state and displays the transparent consent page.
    NEVER collects optional visitor information before consent!
    """
    link = TrackingLink.query.filter_by(token=token).first()
    
    if not link:
        return render_template('tracker/not_found.html', token=token), 404

    if not link.active:
        return render_template('tracker/disabled.html', link=link), 410

    if link.is_expired():
        return render_template('tracker/expired.html', link=link), 410

    # Display transparent educational consent gate
    return render_template('tracker/consent.html', link=link)

@tracker_bp.route('/track/<token>/decide', methods=['POST'])
@tracker_bp.route('/api/track/<token>/consent', methods=['POST'])
def decide(token):
    """
    Processes the visitor's explicit consent choice ('allow' or 'deny').
    Redirects strictly to the administrator-configured target URL.
    
    Combines:
    - SERVER DATA: real client IP (via trusted proxy resolver), timestamp, approximate IP location
    - BROWSER DATA: browser, OS, screen width/height, language, timezone, battery % & charging
    """
    link = TrackingLink.query.filter_by(token=token).first()
    if not link:
        return jsonify({'error': 'Tracking link not found'}), 404

    if not link.active:
        return render_template('tracker/disabled.html', link=link), 410

    if link.is_expired():
        return render_template('tracker/expired.html', link=link), 410

    # Determine submission format (JSON from fetch or Form encoded)
    if request.is_json:
        data = request.get_json() or {}
    else:
        data = request.form.to_dict()

    decision = data.get('decision', '').strip().lower()

    if decision == 'allow':
        # Permitted client-side display parameters
        try:
            screen_width = int(data.get('screen_width')) if data.get('screen_width') is not None else None
        except (ValueError, TypeError):
            screen_width = None

        try:
            screen_height = int(data.get('screen_height')) if data.get('screen_height') is not None else None
        except (ValueError, TypeError):
            screen_height = None

        language = str(data.get('language', ''))[:40] if data.get('language') else None
        user_timezone = str(data.get('timezone', ''))[:80] if data.get('timezone') else None

        # Battery Status API data (Optional, collected only if supported)
        battery_percentage = None
        raw_bat_pct = data.get('battery_percentage')
        if raw_bat_pct is not None:
            try:
                bat_int = int(round(float(raw_bat_pct)))
                if 0 <= bat_int <= 100:
                    battery_percentage = bat_int
            except (ValueError, TypeError):
                battery_percentage = None

        battery_charging = None
        raw_charging = data.get('battery_charging')
        if raw_charging is not None:
            if isinstance(raw_charging, bool):
                battery_charging = raw_charging
            elif isinstance(raw_charging, str):
                if raw_charging.lower() in ('true', '1', 'yes'):
                    battery_charging = True
                elif raw_charging.lower() in ('false', '0', 'no'):
                    battery_charging = False

        # Explicit Precise Device Location (HTML5 Geolocation API, strictly voluntary)
        raw_dev_consent = data.get('device_location_consent', 'not_requested')
        if isinstance(raw_dev_consent, bool):
            device_location_consent = 'granted' if raw_dev_consent else 'denied'
        elif isinstance(raw_dev_consent, str):
            device_location_consent = raw_dev_consent.strip().lower()
        else:
            device_location_consent = 'not_requested'

        dev_lat = dev_lon = dev_acc = dev_city = dev_region = dev_country = dev_timestamp = None

        if device_location_consent == 'granted':
            raw_lat = data.get('device_latitude')
            raw_lon = data.get('device_longitude')
            raw_acc = data.get('device_accuracy_meters')

            is_valid, dev_lat, dev_lon, dev_acc = validate_coordinates(raw_lat, raw_lon, raw_acc)
            if is_valid:
                dev_city, dev_region, dev_country = reverse_geocode_coordinates(dev_lat, dev_lon)
                dev_timestamp = datetime.now(timezone.utc)
            else:
                device_location_consent = 'unavailable'
        elif device_location_consent not in ('denied', 'not_requested', 'unavailable'):
            device_location_consent = 'not_requested'

        # Server-side data: NEVER accept IP from JavaScript payload
        client_ip = get_client_ip()
        user_agent_str = request.headers.get('User-Agent', '')
        browser, os_name = parse_user_agent(user_agent_str)

        # Approximate IP-based geolocation lookup (strictly only on 'allow' decision)
        geo_result = get_approximate_geolocation(client_ip)

        visit = Visit(
            tracking_link_id=link.id,
            timestamp=datetime.now(timezone.utc),
            consent_status='granted',
            ip_address=client_ip,
            approximate_country=geo_result.country,
            approximate_region=geo_result.region,
            approximate_city=geo_result.city,
            browser=browser,
            operating_system=os_name,
            screen_width=screen_width,
            screen_height=screen_height,
            language=language,
            timezone=user_timezone or geo_result.timezone,
            battery_percentage=battery_percentage,
            battery_charging=battery_charging,
            accuracy_radius=geo_result.accuracy_radius,
            confidence_score=geo_result.confidence_score,
            geolocation_provider=geo_result.provider,
            is_mobile=geo_result.is_mobile,
            device_latitude=dev_lat,
            device_longitude=dev_lon,
            device_accuracy_meters=dev_acc,
            device_city=dev_city,
            device_region=dev_region,
            device_country=dev_country,
            device_location_consent=device_location_consent,
            device_location_timestamp=dev_timestamp
        )
        db.session.add(visit)
        db.session.commit()

    elif decision == 'deny':
        # Strictly record minimal consent decision.
        # DO NOT call external geolocation lookup!
        # DO NOT collect IP, browser, OS, screen dimensions, language, timezone, battery, or location!
        visit = Visit(
            tracking_link_id=link.id,
            timestamp=datetime.now(timezone.utc),
            consent_status='denied',
            ip_address=None,
            approximate_country=None,
            approximate_region=None,
            approximate_city=None,
            browser=None,
            operating_system=None,
            screen_width=None,
            screen_height=None,
            language=None,
            timezone=None,
            battery_percentage=None,
            battery_charging=None,
            accuracy_radius=None,
            confidence_score=None,
            geolocation_provider=None,
            is_mobile=None,
            device_latitude=None,
            device_longitude=None,
            device_accuracy_meters=None,
            device_city=None,
            device_region=None,
            device_country=None,
            device_location_consent=None,
            device_location_timestamp=None
        )
        db.session.add(visit)
        db.session.commit()
    else:
        # Default fallback for unrecognized decision: treat as denied to be safe
        visit = Visit(
            tracking_link_id=link.id,
            timestamp=datetime.now(timezone.utc),
            consent_status='denied',
            ip_address=None,
            battery_percentage=None,
            battery_charging=None,
            device_location_consent=None
        )
        db.session.add(visit)
        db.session.commit()

    # Destination URL is strictly the administrator-configured target URL
    target_url = link.target_url

    if request.is_json:
        return jsonify({
            'success': True,
            'decision': decision,
            'redirect_url': target_url
        })
    else:
        return redirect(target_url, code=302)
