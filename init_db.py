import os
from app import app
from models import db

os.makedirs("instance", exist_ok=True)

with app.app_context():
    db.create_all()
    print("Database tables created in instance/hospital.db")