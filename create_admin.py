from app import app, db, User

with app.app_context():
    # Ищем пользователя с логином 'admin'
    admin = User.query.filter_by(username='admin').first()

    if admin:
        # Если найден — просто делаем его админом
        admin.role = 'admin'
        admin.password = 'admin123'  # ← при необходимости смените пароль
        db.session.commit()
        print("✅ Пользователь 'admin' обновлён!")
        print("🔑 Логин: admin")
        print("🔑 Пароль: admin123")
    else:
        # Если не найден — создаём нового
        new_admin = User(
            username='admin',
            password='admin123',
            role='admin',
            bd=1, bm=1, by=1990,
            class_grade=None,
            child_username=None
        )
        db.session.add(new_admin)
        db.session.commit()
        print("✅ Админ создан с нуля!")