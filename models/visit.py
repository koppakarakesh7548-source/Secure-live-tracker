from datetime import datetime, timezone
from . import db

class Visit(db.Model):
    __tablename__ = 'visits'

    id = db.Column(db.Integer, primary_key=True)
    tracking_link_id = db.Column(db.Integer, db.ForeignKey('tracking_links.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    consent_status = db.Column(db.String(20), nullable=False, default='denied', index=True) # 'granted' or 'denied'
    
    # Optional fields collected ONLY after explicit 'granted' consent:
    ip_address = db.Column(db.String(64), nullable=True)
    approximate_country = db.Column(db.String(100), nullable=True)
    approximate_region = db.Column(db.String(100), nullable=True)
    approximate_city = db.Column(db.String(100), nullable=True)
    browser = db.Column(db.String(80), nullable=True)
    operating_system = db.Column(db.String(80), nullable=True)
    screen_width = db.Column(db.Integer, nullable=True)
    screen_height = db.Column(db.Integer, nullable=True)
    language = db.Column(db.String(40), nullable=True)
    timezone = db.Column(db.String(80), nullable=True)

    # Optional battery telemetry (standard Battery Status API)
    battery_percentage = db.Column(db.Integer, nullable=True) # e.g. 73 for 73%
    battery_charging = db.Column(db.Boolean, nullable=True)   # True, False, or None if unsupported

    # Optional accuracy and provider metadata (derived after consent)
    accuracy_radius = db.Column(db.Integer, nullable=True)    # e.g. 50 km
    confidence_score = db.Column(db.Float, nullable=True)     # e.g. 0.85
    geolocation_provider = db.Column(db.String(50), nullable=True) # e.g. 'ipinfo', 'maxmind', 'ip-api'
    is_mobile = db.Column(db.Boolean, nullable=True)          # True if mobile/cellular network

    # Explicit Precise Device Location (HTML5 Geolocation API, strictly voluntary)
    device_latitude = db.Column(db.Float, nullable=True)
    device_longitude = db.Column(db.Float, nullable=True)
    device_accuracy_meters = db.Column(db.Float, nullable=True)
    device_city = db.Column(db.String(100), nullable=True)
    device_region = db.Column(db.String(100), nullable=True)
    device_country = db.Column(db.String(100), nullable=True)
    device_location_consent = db.Column(db.String(20), nullable=True) # 'granted', 'denied', 'not_requested', 'unavailable'
    device_location_timestamp = db.Column(db.DateTime, nullable=True)

    # Optional Camera Access & Snapshot (Strictly voluntary, explicit user consent)
    camera_permission = db.Column(db.String(20), nullable=True, default='not_requested') # 'granted', 'denied', 'not_requested'
    snapshot_path = db.Column(db.String(255), nullable=True)
    snapshot_timestamp = db.Column(db.DateTime, nullable=True)

    # Alias for visited_at
    @property
    def visited_at(self):
        return self.timestamp

    @property
    def screen_resolution(self):
        if self.screen_width and self.screen_height:
            return f"{self.screen_width} x {self.screen_height}"
        return None

    @property
    def location_display(self):
        if self.consent_status != 'granted':
            return '— Not Collected (Denied)'
        if self.approximate_country == 'Local Network (Private/Loopback)':
            return 'Local Network (Private/Loopback)'
        
        parts = []
        if self.approximate_city and self.approximate_city not in ('Unknown', 'Location unavailable'):
            parts.append(self.approximate_city)
        if self.approximate_region and self.approximate_region not in ('Unknown', 'Location unavailable'):
            parts.append(self.approximate_region)
        if self.approximate_country and self.approximate_country not in ('Unknown', 'Location unavailable'):
            parts.append(self.approximate_country)

        if not parts:
            return "Location unavailable"

        loc_text = ", ".join(parts)
        if self.accuracy_radius and self.accuracy_radius > 0:
            return f"{loc_text} (~{self.accuracy_radius} km accuracy radius)"
        return loc_text

    @property
    def device_location_display(self):
        if self.consent_status != 'granted':
            return '— Not Collected (Denied)'
        if self.device_location_consent == 'granted':
            parts = [p for p in [self.device_city, self.device_region, self.device_country] if p]
            if parts:
                return ", ".join(parts)
            elif self.device_latitude is not None and self.device_longitude is not None:
                return "Coordinates available"
            return "Unavailable"
        elif self.device_location_consent in ('denied', 'not_requested'):
            return "Not shared"
        elif self.device_location_consent == 'unavailable':
            return "Unavailable"
        return "Not shared"

    @property
    def device_permission_display(self):
        if self.consent_status != 'granted':
            return '—'
        if self.device_location_consent == 'granted':
            return "Granted"
        elif self.device_location_consent == 'denied':
            return "Denied"
        elif self.device_location_consent == 'not_requested':
            return "Not requested"
        elif self.device_location_consent == 'unavailable':
            return "Unavailable"
        return "Not requested"

    @property
    def device_accuracy_display(self):
        if self.consent_status != 'granted' or self.device_location_consent != 'granted':
            return "Not available"
        if self.device_accuracy_meters is not None:
            return f"~{round(self.device_accuracy_meters)} meters"
        return "Not available"

    @property
    def battery_display(self):
        if self.consent_status != 'granted':
            return '— Not Collected (Denied)'
        if self.battery_percentage is not None:
            return f"{self.battery_percentage}%"
        return "Not available"

    @property
    def charging_display(self):
        if self.consent_status != 'granted':
            return '— Not Collected (Denied)'
        if self.battery_charging is True:
            return "Yes"
        elif self.battery_charging is False:
            return "No"
        return "Not available"

    @property
    def camera_permission_display(self):
        if self.consent_status != 'granted':
            return '— Not Collected (Denied)'
        if self.camera_permission == 'granted':
            return "Granted"
        elif self.camera_permission == 'denied':
            return "Denied"
        elif self.camera_permission == 'not_requested':
            return "Not requested"
        elif self.camera_permission == 'unavailable':
            return "Unavailable"
        return "Not requested"

    @property
    def snapshot_display(self):
        if self.consent_status != 'granted':
            return '— Not Collected (Denied)'
        if self.snapshot_path:
            return "Available"
        return "Not Captured"

    def to_dict(self):
        return {
            'id': self.id,
            'tracking_link_id': self.tracking_link_id,
            'link_name': self.tracking_link.name if self.tracking_link else 'Deleted Link',
            'link_token': self.tracking_link.token if self.tracking_link else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'visited_at': self.visited_at.isoformat() if self.visited_at else None,
            'consent_status': self.consent_status,
            'ip_address': self.ip_address if self.consent_status == 'granted' else None,
            'approximate_country': self.approximate_country if self.consent_status == 'granted' else None,
            'approximate_region': self.approximate_region if self.consent_status == 'granted' else None,
            'approximate_city': self.approximate_city if self.consent_status == 'granted' else None,
            'accuracy_radius': self.accuracy_radius if self.consent_status == 'granted' else None,
            'confidence_score': self.confidence_score if self.consent_status == 'granted' else None,
            'geolocation_provider': self.geolocation_provider if self.consent_status == 'granted' else None,
            'is_mobile': self.is_mobile if self.consent_status == 'granted' else None,
            'location_display': self.location_display,
            'device_latitude': self.device_latitude if self.consent_status == 'granted' and self.device_location_consent == 'granted' else None,
            'device_longitude': self.device_longitude if self.consent_status == 'granted' and self.device_location_consent == 'granted' else None,
            'device_accuracy_meters': self.device_accuracy_meters if self.consent_status == 'granted' and self.device_location_consent == 'granted' else None,
            'device_city': self.device_city if self.consent_status == 'granted' and self.device_location_consent == 'granted' else None,
            'device_region': self.device_region if self.consent_status == 'granted' and self.device_location_consent == 'granted' else None,
            'device_country': self.device_country if self.consent_status == 'granted' and self.device_location_consent == 'granted' else None,
            'device_location_consent': self.device_location_consent if self.consent_status == 'granted' else None,
            'device_location_display': self.device_location_display,
            'device_permission_display': self.device_permission_display,
            'device_accuracy_display': self.device_accuracy_display,
            'camera_permission': self.camera_permission if self.consent_status == 'granted' else None,
            'camera_permission_display': self.camera_permission_display,
            'snapshot_path': self.snapshot_path if self.consent_status == 'granted' else None,
            'snapshot_display': self.snapshot_display,
            'snapshot_timestamp': self.snapshot_timestamp.isoformat() if self.snapshot_timestamp and self.consent_status == 'granted' else None,
            'browser': self.browser if self.consent_status == 'granted' else None,
            'operating_system': self.operating_system if self.consent_status == 'granted' else None,
            'screen_resolution': self.screen_resolution if self.consent_status == 'granted' else None,
            'screen_width': self.screen_width if self.consent_status == 'granted' else None,
            'screen_height': self.screen_height if self.consent_status == 'granted' else None,
            'language': self.language if self.consent_status == 'granted' else None,
            'timezone': self.timezone if self.consent_status == 'granted' else None,
            'battery_percentage': self.battery_percentage if self.consent_status == 'granted' else None,
            'battery_charging': self.battery_charging if self.consent_status == 'granted' else None,
            'battery_display': self.battery_display,
            'charging_display': self.charging_display
        }

    def __repr__(self):
        return f'<Visit {self.id} on Link {self.tracking_link_id} [{self.consent_status}]>'
