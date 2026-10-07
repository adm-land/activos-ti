from datetime import date, datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="viewer")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    events = db.relationship("AuditEvent", back_populates="actor")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def can_manage(self):
        return self.role in {"technician", "admin"}


class Asset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    asset_tag = db.Column(db.String(40), unique=True, nullable=False, index=True)
    asset_type = db.Column(db.String(50), nullable=False)
    brand = db.Column(db.String(60), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    serial_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default="Disponible")
    location = db.Column(db.String(100), nullable=False, default="Almacén TI")
    assigned_to = db.Column(db.String(100), nullable=True)
    assigned_email = db.Column(db.String(120), nullable=True)
    purchase_date = db.Column(db.Date, nullable=True)
    warranty_end = db.Column(db.Date, nullable=True)
    next_maintenance = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    maintenance_records = db.relationship("MaintenanceRecord", back_populates="asset", cascade="all, delete-orphan", order_by="MaintenanceRecord.performed_at.desc()")
    assignments = db.relationship("Assignment", back_populates="asset", cascade="all, delete-orphan", order_by="Assignment.assigned_at.desc()")
    events = db.relationship("AuditEvent", back_populates="asset", cascade="all, delete-orphan", order_by="AuditEvent.created_at.desc()")

    @property
    def warranty_state(self):
        if not self.warranty_end:
            return "Sin dato"
        days = (self.warranty_end - date.today()).days
        if days < 0:
            return "Vencida"
        if days <= 60:
            return "Por vencer"
        return "Vigente"

    @property
    def maintenance_state(self):
        if not self.next_maintenance:
            return "Sin fecha"
        days = (self.next_maintenance - date.today()).days
        if days < 0:
            return "Vencido"
        if days <= 30:
            return "Próximo"
        return "Programado"


class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_name = db.Column(db.String(100), nullable=False)
    employee_email = db.Column(db.String(120), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    returned_at = db.Column(db.DateTime, nullable=True)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=False)

    asset = db.relationship("Asset", back_populates="assignments")


class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    maintenance_type = db.Column(db.String(40), nullable=False)
    description = db.Column(db.Text, nullable=False)
    technician = db.Column(db.String(100), nullable=False)
    cost = db.Column(db.Float, nullable=False, default=0)
    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=False)

    asset = db.relationship("Asset", back_populates="maintenance_records")


class AuditEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)
    detail = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    asset = db.relationship("Asset", back_populates="events")
    actor = db.relationship("User", back_populates="events")
