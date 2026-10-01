from datetime import datetime, timezone
from . import db

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    key = db.Column(db.String(80), primary_key=True)
    value = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default

    @classmethod
    def set(cls, key, value):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)
            setting.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return setting

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admins.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(80), nullable=False, index=True)
    target_type = db.Column(db.String(40), nullable=True)
    target_id = db.Column(db.String(80), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    admin = db.relationship('Admin', backref='audit_logs', foreign_keys=[admin_id])

    @classmethod
    def record(cls, action, admin_id=None, target_type=None, target_id=None, details=None, ip_address=None):
        try:
            entry = cls(
                action=action,
                admin_id=admin_id,
                target_type=target_type,
                target_id=str(target_id) if target_id is not None else None,
                details=details,
                ip_address=ip_address
            )
            db.session.add(entry)
            db.session.commit()
            return entry
        except Exception:
            db.session.rollback()
            return None

    def __repr__(self):
        return f'<AuditLog {self.action} by Admin {self.admin_id} at {self.timestamp}>'
