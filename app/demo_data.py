from datetime import date, datetime, timedelta
from . import db
from .models import User, Asset, Assignment, MaintenanceRecord, AuditEvent


def seed_demo_data(reset=False):
    if reset:
        db.drop_all()
        db.create_all()
    elif User.query.first():
        return False

    admin = User(name="Alan Martínez", email="admin@activos.local", role="admin")
    admin.set_password("Admin123!")
    tech = User(name="Sofía Torres", email="tecnico@activos.local", role="technician")
    tech.set_password("Tecnico123!")
    viewer = User(name="Carlos Mendoza", email="consulta@activos.local", role="viewer")
    viewer.set_password("Consulta123!")
    db.session.add_all([admin, tech, viewer])
    db.session.flush()

    today = date.today()
    assets = [
        Asset(asset_tag="TI-LAP-001", asset_type="Laptop", brand="Dell", model="Latitude 5440", serial_number="DL5440-A001", status="Asignado", location="Administración", assigned_to="Mariana López", assigned_email="mariana@empresa.local", purchase_date=today-timedelta(days=420), warranty_end=today+timedelta(days=45), next_maintenance=today+timedelta(days=20)),
        Asset(asset_tag="TI-LAP-002", asset_type="Laptop", brand="Lenovo", model="ThinkPad E14", serial_number="LNE14-B002", status="Disponible", location="Almacén TI", purchase_date=today-timedelta(days=240), warranty_end=today+timedelta(days=490), next_maintenance=today+timedelta(days=70)),
        Asset(asset_tag="TI-SW-001", asset_type="Switch", brand="Cisco", model="CBS250-24T", serial_number="CSW250-C001", status="Asignado", location="Site principal", assigned_to="Infraestructura TI", assigned_email="infra@empresa.local", purchase_date=today-timedelta(days=800), warranty_end=today-timedelta(days=35), next_maintenance=today-timedelta(days=5)),
        Asset(asset_tag="TI-MON-001", asset_type="Monitor", brand="HP", model="E24 G5", serial_number="HPE24-D001", status="Disponible", location="Almacén TI", purchase_date=today-timedelta(days=130), warranty_end=today+timedelta(days=590), next_maintenance=None),
        Asset(asset_tag="TI-IMP-001", asset_type="Impresora", brand="Brother", model="MFC-L3770CDW", serial_number="BR3770-E001", status="Mantenimiento", location="Recepción", purchase_date=today-timedelta(days=980), warranty_end=today-timedelta(days=250), next_maintenance=today+timedelta(days=2)),
        Asset(asset_tag="TI-RTR-001", asset_type="Router", brand="Cisco", model="C1111-8P", serial_number="CR1111-F001", status="Asignado", location="Site principal", assigned_to="Infraestructura TI", assigned_email="infra@empresa.local", purchase_date=today-timedelta(days=600), warranty_end=today+timedelta(days=130), next_maintenance=today+timedelta(days=35)),
    ]
    db.session.add_all(assets)
    db.session.flush()

    assignment = Assignment(employee_name="Mariana López", employee_email="mariana@empresa.local", department="Administración", asset=assets[0], assigned_at=datetime.utcnow()-timedelta(days=120))
    network_assignment = Assignment(employee_name="Infraestructura TI", employee_email="infra@empresa.local", department="Sistemas", asset=assets[2], assigned_at=datetime.utcnow()-timedelta(days=300))
    maint = MaintenanceRecord(maintenance_type="Preventivo", description="Limpieza interna, revisión de temperaturas y actualización de firmware.", technician="Sofía Torres", cost=0, asset=assets[2], performed_at=datetime.utcnow()-timedelta(days=95))
    db.session.add_all([assignment, network_assignment, maint])

    for asset in assets:
        db.session.add(AuditEvent(action="Alta", detail=f"Activo {asset.asset_tag} registrado", asset=asset, actor=admin, created_at=asset.created_at))
    db.session.add(AuditEvent(action="Mantenimiento", detail="Preventivo: limpieza y revisión de firmware", asset=assets[2], actor=tech, created_at=maint.performed_at))
    db.session.commit()
    return True
