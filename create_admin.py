from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin = User(username='Михаил Качин', password=generate_password_hash('Ьлфывц2009'), role='admin')
        db.session.add(admin)
        db.session.commit()
        print("✅ Админ создан!")
    else:
        print("⚠️ Админ уже есть")