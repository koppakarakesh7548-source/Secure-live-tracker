from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(session_options={'expire_on_commit': False})

from .admin import Admin
from .tracking_link import TrackingLink
from .visit import Visit
from .setting import SystemSetting, AuditLog

__all__ = ['db', 'Admin', 'TrackingLink', 'Visit', 'SystemSetting', 'AuditLog']
