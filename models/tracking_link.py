from datetime import datetime, timezone
from . import db

class TrackingLink(db.Model):
    __tablename__ = 'tracking_links'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_url = db.Column(db.String(1024), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    visits = db.relationship('Visit', backref='tracking_link', lazy='dynamic', cascade='all, delete-orphan')
    creator = db.relationship('Admin', backref='tracking_links', foreign_keys=[created_by_id])

    # Alias for Section 14 naming
    @property
    def enabled(self):
        return self.active

    @enabled.setter
    def enabled(self, val):
        self.active = bool(val)

    def is_expired(self):
        if not self.expires_at:
            return False
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    def is_accessible(self):
        return self.active and not self.is_expired()

    @property
    def total_visits(self):
        return self.visits.count()

    @property
    def consent_granted_count(self):
        return self.visits.filter_by(consent_status='granted').count()

    @property
    def consent_denied_count(self):
        return self.visits.filter_by(consent_status='denied').count()

    def to_dict(self):
        return {
            'id': self.id,
            'token': self.token,
            'name': self.name,
            'description': self.description,
            'target_url': self.target_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'active': self.active,
            'enabled': self.enabled,
            'is_expired': self.is_expired(),
            'is_accessible': self.is_accessible(),
            'total_visits': self.total_visits,
            'consent_granted': self.consent_granted_count,
            'consent_denied': self.consent_denied_count
        }

    def __repr__(self):
        return f'<TrackingLink {self.token} - {self.name}>'
