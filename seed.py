from app import create_app
from app.demo_data import seed_demo_data

app = create_app()

with app.app_context():
    seed_demo_data(reset=True)
    print("Base de datos de demostración creada.")
