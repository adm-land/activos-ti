from datetime import date, timedelta
from app import create_app, db
from app.models import User, Asset, Assignment, MaintenanceRecord


def make_app(tmp_path):
    return create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'test.db'}",
        "SECRET_KEY": "test",
        "WTF_CSRF_ENABLED": False,
    })


def create_admin(app):
    with app.app_context():
        user = User(name="Admin", email="admin@test.local", role="admin")
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()


def login(client):
    return client.post("/login", data={"email": "admin@test.local", "password": "pass123"}, follow_redirects=True)


def create_asset(client):
    return client.post("/assets/new", data={
        "asset_tag": "TI-TEST-001",
        "asset_type": "Laptop",
        "brand": "Dell",
        "model": "Latitude",
        "serial_number": "SERIE-001",
        "status": "Disponible",
        "location": "Almacén TI",
        "purchase_date": date.today().isoformat(),
        "warranty_end": (date.today() + timedelta(days=45)).isoformat(),
        "next_maintenance": (date.today() + timedelta(days=20)).isoformat(),
    }, follow_redirects=True)


def test_health_and_login(tmp_path):
    app = make_app(tmp_path)
    create_admin(app)
    client = app.test_client()
    assert client.get("/health").status_code == 200
    response = login(client)
    assert response.status_code == 200
    assert b"Inventario tecnol" in response.data


def test_asset_assignment_maintenance_api_and_export(tmp_path):
    app = make_app(tmp_path)
    create_admin(app)
    client = app.test_client()
    login(client)
    response = create_asset(client)
    assert response.status_code == 200

    with app.app_context():
        asset = Asset.query.first()
        assert asset is not None
        assert asset.warranty_state == "Por vencer"
        asset_id = asset.id

    assignment = client.post(f"/assets/{asset_id}/assign", data={
        "employee_name": "Ana Pérez",
        "employee_email": "ana@empresa.local",
        "department": "Finanzas",
    }, follow_redirects=True)
    assert assignment.status_code == 200

    maintenance = client.post(f"/assets/{asset_id}/maintenance", data={
        "maintenance_type": "Preventivo",
        "description": "Limpieza y revisión general",
        "technician": "Admin",
        "cost": "150.50",
    }, follow_redirects=True)
    assert maintenance.status_code == 200

    with app.app_context():
        asset = Asset.query.first()
        assert asset.status == "Asignado"
        assert Assignment.query.count() == 1
        assert MaintenanceRecord.query.count() == 1

    api_response = client.get("/api/assets")
    assert api_response.status_code == 200
    assert api_response.get_json()[0]["asset_tag"] == "TI-TEST-001"

    export = client.get("/assets/export.csv")
    assert export.status_code == 200
    assert b"TI-TEST-001" in export.data
