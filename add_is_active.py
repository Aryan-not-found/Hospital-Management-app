from app import app
from models import db
from sqlalchemy import text

with app.app_context():
    db.session.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1"))
    db.session.commit()
    print("Column added.")