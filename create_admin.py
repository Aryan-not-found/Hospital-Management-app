from app import app, db
from models import User

with app.app_context():
    email = "admin@example.com"
    existing = User.query.filter_by(email=email).first()
    if existing:
        print("Admin already exists:", existing.email)
    else:
        u = User(name="Admin User", email=email, role="admin")
        u.set_password("admin123")
        db.session.add(u)
        db.session.commit()
        print("Admin created:", email, "password=admin123") 