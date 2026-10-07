import csv
import io
from datetime import date, datetime
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, Response, jsonify
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from . import db
from .models import User, Asset, Assignment, MaintenanceRecord, AuditEvent

bp = Blueprint("main", __name__)

ASSET_TYPES = {"Laptop", "Desktop", "Monitor", "Impresora", "Router", "Switch", "Teléfono", "Otro"}
ASSET_STATUS = {"Disponible", "Asignado", "Mantenimiento", "Baja"}


def manager_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.can_manage:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def filtered_assets(query):
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()
    asset_type = request.args.get("type", "").strip()
    location = request.args.get("location", "").strip()

    if q:
        query = query.filter(or_(
            Asset.asset_tag.ilike(f"%{q}%"),
            Asset.brand.ilike(f"%{q}%"),
            Asset.model.ilike(f"%{q}%"),
            Asset.serial_number.ilike(f"%{q}%"),
            Asset.assigned_to.ilike(f"%{q}%"),
        ))
    if status in ASSET_STATUS:
        query = query.filter_by(status=status)
    if asset_type in ASSET_TYPES:
        query = query.filter_by(asset_type=asset_type)
    if location:
        query = query.filter(Asset.location.ilike(f"%{location}%"))
    return query


def log_event(action, detail, asset=None):
    db.session.add(AuditEvent(action=action, detail=detail, asset=asset, actor=current_user))


@bp.route("/health")
def health():
    return jsonify({"status": "ok"})


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("main.dashboard"))
        flash("Correo o contraseña incorrectos.", "danger")
    return render_template("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@bp.route("/dashboard")
@login_required
def dashboard():
    assets = Asset.query.all()
    type_counts = {}
    location_counts = {}
    for asset in assets:
        type_counts[asset.asset_type] = type_counts.get(asset.asset_type, 0) + 1
        location_counts[asset.location] = location_counts.get(asset.location, 0) + 1

    metrics = {
        "total": len(assets),
        "available": sum(1 for a in assets if a.status == "Disponible"),
        "assigned": sum(1 for a in assets if a.status == "Asignado"),
        "maintenance": sum(1 for a in assets if a.status == "Mantenimiento"),
        "retired": sum(1 for a in assets if a.status == "Baja"),
        "warranty_alerts": sum(1 for a in assets if a.warranty_state in {"Por vencer", "Vencida"}),
        "maintenance_alerts": sum(1 for a in assets if a.maintenance_state in {"Próximo", "Vencido"}),
    }

    max_type = max(type_counts.values(), default=1) or 1
    categories = [
        {"name": name, "count": count, "percent": round((count / max_type) * 100)}
        for name, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    ]
    alerts = sorted(
        [a for a in assets if a.warranty_state in {"Por vencer", "Vencida"} or a.maintenance_state in {"Próximo", "Vencido"}],
        key=lambda a: a.next_maintenance or a.warranty_end or date.max,
    )[:6]
    recent_events = AuditEvent.query.order_by(AuditEvent.created_at.desc()).limit(7).all()
    return render_template("dashboard.html", metrics=metrics, categories=categories, alerts=alerts, recent_events=recent_events)


@bp.route("/assets")
@login_required
def assets():
    items = filtered_assets(Asset.query).order_by(Asset.updated_at.desc()).all()
    return render_template("assets.html", assets=items, asset_types=sorted(ASSET_TYPES), statuses=sorted(ASSET_STATUS))


@bp.route("/assets/new", methods=["GET", "POST"])
@manager_required
def new_asset():
    if request.method == "POST":
        data = {key: request.form.get(key, "").strip() for key in ["asset_tag", "asset_type", "brand", "model", "serial_number", "status", "location", "notes"]}
        required = [data["asset_tag"], data["asset_type"], data["brand"], data["model"], data["serial_number"], data["location"]]
        if not all(required):
            flash("Completa los campos obligatorios.", "danger")
            return render_template("asset_form.html", asset_types=sorted(ASSET_TYPES), statuses=sorted(ASSET_STATUS), asset=None)
        if data["asset_type"] not in ASSET_TYPES or data["status"] not in ASSET_STATUS:
            abort(400)
        if Asset.query.filter(or_(Asset.asset_tag == data["asset_tag"], Asset.serial_number == data["serial_number"])).first():
            flash("La etiqueta o el número de serie ya están registrados.", "danger")
            return render_template("asset_form.html", asset_types=sorted(ASSET_TYPES), statuses=sorted(ASSET_STATUS), asset=None)

        asset = Asset(
            asset_tag=data["asset_tag"], asset_type=data["asset_type"], brand=data["brand"], model=data["model"],
            serial_number=data["serial_number"], status=data["status"], location=data["location"], notes=data["notes"],
            purchase_date=parse_date(request.form.get("purchase_date")),
            warranty_end=parse_date(request.form.get("warranty_end")),
            next_maintenance=parse_date(request.form.get("next_maintenance")),
        )
        db.session.add(asset)
        db.session.flush()
        log_event("Alta", f"Activo {asset.asset_tag} registrado", asset)
        db.session.commit()
        flash("Activo registrado.", "success")
        return redirect(url_for("main.asset_detail", asset_id=asset.id))
    return render_template("asset_form.html", asset_types=sorted(ASSET_TYPES), statuses=sorted(ASSET_STATUS), asset=None)


@bp.route("/assets/<int:asset_id>")
@login_required
def asset_detail(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    return render_template("asset_detail.html", asset=asset, statuses=sorted(ASSET_STATUS))


@bp.route("/assets/<int:asset_id>/edit", methods=["GET", "POST"])
@manager_required
def edit_asset(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    if request.method == "POST":
        old_status = asset.status
        asset.asset_type = request.form.get("asset_type", asset.asset_type)
        asset.brand = request.form.get("brand", "").strip()
        asset.model = request.form.get("model", "").strip()
        asset.status = request.form.get("status", asset.status)
        asset.location = request.form.get("location", "").strip()
        asset.notes = request.form.get("notes", "").strip()
        asset.purchase_date = parse_date(request.form.get("purchase_date"))
        asset.warranty_end = parse_date(request.form.get("warranty_end"))
        asset.next_maintenance = parse_date(request.form.get("next_maintenance"))
        if asset.asset_type not in ASSET_TYPES or asset.status not in ASSET_STATUS:
            abort(400)
        detail = "Datos del activo actualizados"
        if old_status != asset.status:
            detail += f" · Estado: {old_status} → {asset.status}"
        log_event("Actualización", detail, asset)
        db.session.commit()
        flash("Activo actualizado.", "success")
        return redirect(url_for("main.asset_detail", asset_id=asset.id))
    return render_template("asset_form.html", asset_types=sorted(ASSET_TYPES), statuses=sorted(ASSET_STATUS), asset=asset)


@bp.route("/assets/<int:asset_id>/assign", methods=["POST"])
@manager_required
def assign_asset(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    employee_name = request.form.get("employee_name", "").strip()
    employee_email = request.form.get("employee_email", "").strip()
    department = request.form.get("department", "").strip()
    if not employee_name:
        flash("Indica la persona responsable.", "danger")
        return redirect(url_for("main.asset_detail", asset_id=asset.id))

    active = next((a for a in asset.assignments if a.returned_at is None), None)
    if active:
        active.returned_at = datetime.utcnow()

    assignment = Assignment(employee_name=employee_name, employee_email=employee_email, department=department, asset=asset)
    asset.assigned_to = employee_name
    asset.assigned_email = employee_email
    asset.status = "Asignado"
    db.session.add(assignment)
    log_event("Asignación", f"Asignado a {employee_name}" + (f" · {department}" if department else ""), asset)
    db.session.commit()
    flash("Asignación registrada.", "success")
    return redirect(url_for("main.asset_detail", asset_id=asset.id))


@bp.route("/assets/<int:asset_id>/return", methods=["POST"])
@manager_required
def return_asset(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    active = next((a for a in asset.assignments if a.returned_at is None), None)
    if active:
        active.returned_at = datetime.utcnow()
        log_event("Devolución", f"Devuelto por {active.employee_name}", asset)
    asset.assigned_to = None
    asset.assigned_email = None
    if asset.status != "Baja":
        asset.status = "Disponible"
    db.session.commit()
    flash("Devolución registrada.", "success")
    return redirect(url_for("main.asset_detail", asset_id=asset.id))


@bp.route("/assets/<int:asset_id>/maintenance", methods=["POST"])
@manager_required
def add_maintenance(asset_id):
    asset = db.get_or_404(Asset, asset_id)
    maintenance_type = request.form.get("maintenance_type", "Preventivo").strip()
    description = request.form.get("description", "").strip()
    technician = request.form.get("technician", "").strip()
    try:
        cost = float(request.form.get("cost", "0") or 0)
    except ValueError:
        cost = 0
    if not description or not technician:
        flash("Agrega descripción y técnico responsable.", "danger")
        return redirect(url_for("main.asset_detail", asset_id=asset.id))

    record = MaintenanceRecord(maintenance_type=maintenance_type, description=description, technician=technician, cost=max(cost, 0), asset=asset)
    next_date = parse_date(request.form.get("next_maintenance"))
    if next_date:
        asset.next_maintenance = next_date
    db.session.add(record)
    log_event("Mantenimiento", f"{maintenance_type}: {description[:120]}", asset)
    db.session.commit()
    flash("Mantenimiento registrado.", "success")
    return redirect(url_for("main.asset_detail", asset_id=asset.id))


@bp.route("/assets/export.csv")
@login_required
def export_assets():
    items = filtered_assets(Asset.query).order_by(Asset.asset_tag).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Etiqueta", "Tipo", "Marca", "Modelo", "Serie", "Estado", "Ubicación", "Responsable", "Garantía", "Próximo mantenimiento"])
    for asset in items:
        writer.writerow([
            asset.asset_tag, asset.asset_type, asset.brand, asset.model, asset.serial_number, asset.status,
            asset.location, asset.assigned_to or "", asset.warranty_end.isoformat() if asset.warranty_end else "",
            asset.next_maintenance.isoformat() if asset.next_maintenance else "",
        ])
    return Response(output.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=activos_ti.csv"})


@bp.route("/api/assets")
@login_required
def api_assets():
    items = filtered_assets(Asset.query).order_by(Asset.asset_tag).all()
    return jsonify([
        {
            "id": a.id,
            "asset_tag": a.asset_tag,
            "type": a.asset_type,
            "brand": a.brand,
            "model": a.model,
            "serial_number": a.serial_number,
            "status": a.status,
            "location": a.location,
            "assigned_to": a.assigned_to,
            "warranty_state": a.warranty_state,
            "maintenance_state": a.maintenance_state,
        }
        for a in items
    ])


@bp.route("/admin/users")
@admin_required
def users():
    return render_template("users.html", users=User.query.order_by(User.name).all())
