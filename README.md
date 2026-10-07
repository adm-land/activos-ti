# Activos TI

Sistema web para llevar el control de equipos tecnológicos dentro de una empresa. Lo hice como proyecto de portafolio para practicar desarrollo web, bases de datos y procesos que normalmente maneja un área de Sistemas.

La idea no fue hacer solamente un inventario de productos, sino trabajar con el ciclo de vida de los equipos: dónde están, quién los tiene, cuándo vence su garantía, cuándo necesitan mantenimiento y qué movimientos han tenido.

## Funciones principales

- Inicio de sesión con roles de administrador, técnico y consulta.
- Registro de laptops, desktops, monitores, impresoras, routers, switches y otros equipos.
- Etiqueta interna y número de serie único por activo.
- Estados: Disponible, Asignado, Mantenimiento y Baja.
- Ubicación física de los equipos.
- Asignación y devolución de activos a personas o áreas.
- Historial completo de responsables.
- Registro de mantenimientos preventivos y correctivos.
- Control de próximo mantenimiento.
- Alertas de garantía vencida o próxima a vencer.
- Dashboard con indicadores y distribución por tipo de activo.
- Historial de movimientos para tener trazabilidad.
- Búsqueda y filtros por tipo, estado y ubicación.
- Exportación del inventario a CSV.
- API de consulta en `/api/assets`.
- Contraseñas almacenadas con hash y protección CSRF.
- Pruebas automáticas con Pytest y GitHub Actions.

## Tecnologías

- Python
- Flask
- SQLAlchemy
- MySQL / PyMySQL
- HTML y CSS
- Flask-Login
- Flask-WTF
- Docker Compose
- Pytest
- GitHub Actions
- Gunicorn

## Ejecutarlo en local

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Instala dependencias:

```bash
pip install -r requirements.txt
```

Crea `.env` tomando como base `.env.example` y después ejecuta:

```bash
python seed.py
python run.py
```

Abre `http://127.0.0.1:5000`.

### Usuarios de demostración

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@activos.local` | `Admin123!` |
| Técnico | `tecnico@activos.local` | `Tecnico123!` |
| Consulta | `consulta@activos.local` | `Consulta123!` |

Son cuentas de prueba para mostrar los distintos permisos del sistema.

## MySQL con Docker

```bash
docker compose up -d
```

En `.env`:

```env
SECRET_KEY=cambia-esta-clave
DATABASE_URL=mysql+pymysql://assets:assets@localhost:3306/assets
```

Después ejecuta `python seed.py` y `python run.py`.

## Enfoque del proyecto

Este proyecto está pensado como una herramienta interna sencilla para un equipo de TI. Me interesó agregar trazabilidad, alertas y mantenimientos porque son funciones que vuelven el inventario más útil que una tabla de equipos.

## Mejoras futuras

Más adelante agregaría códigos QR para identificar activos físicamente, importación masiva desde CSV y reportes por área o centro de costos.

## Autor

**Alan Daniel Martínez Martínez**  
Estudiante de Ingeniería en Sistemas Computacionales — UNITEC
