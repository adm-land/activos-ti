from app import create_app
from app.demo_data import seed_demo_data

app = create_app()

with app.app_context():
    created = seed_demo_data(reset=False)
    print("Datos de demostración cargados." if created else "La base ya tiene información.")
