import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32).hex()  # Замените на статичную строку для продакшена
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///school.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ================= МОДЕЛИ =================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    class_grade = db.Column(db.String(10), nullable=True)
    child_username = db.Column(db.String(80), nullable=True)
    bd = db.Column(db.Integer)
    bm = db.Column(db.Integer)
    by = db.Column(db.Integer)

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    page_type = db.Column(db.String(20))
    heading = db.Column(db.String(200))
    is_archived = db.Column(db.Boolean, default=False)
    subheading = db.Column(db.String(200), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    allow_student_upload = db.Column(db.Boolean, default=False)
    student_comment = db.Column(db.Text, nullable=True)
    is_submitted = db.Column(db.Boolean, default=False)
    grade = db.Column(db.Integer, nullable=True)
    teacher_comment = db.Column(db.Text, nullable=True)
    files = db.relationship('FileModel', backref='content', lazy=True)

class FileModel(db.Model):
    topic_id = db.Column(db.Integer, db.ForeignKey('theory_topic.id'), nullable=True)
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(200), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    context = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=True)


class CalendarEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # 🔑 Если NULL — событие общее (видно всем в общем календаре админа)
    # Если задан — событие привязано к конкретному ученику
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    event_date = db.Column(db.Date, nullable=False)  # Дата события
    time_str = db.Column(db.String(50), nullable=True)  # "14:00-15:30"
    color = db.Column(db.String(10), default='#3788d8')  # Цвет метки
    comment = db.Column(db.Text, nullable=True)  # Текст события/комментария
    is_private = db.Column(db.Boolean, default=False)  # Видно только админу
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Связь с учеником (если есть)
    student = db.relationship('User', foreign_keys=[target_user_id], backref='calendar_events')

class StudentColor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    color = db.Column(db.String(10), default='#3788d8')  # HEX цвет
    student = db.relationship('User', backref='color_setting')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    target_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=True)
    filename = db.Column(db.String(200), nullable=True)
    filepath = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)





@login_manager.user_loader
def load_user(id):
    return db.session.get(User, int(id))

def get_target_user_or_404(user_id):
    u = db.session.get(User, user_id)
    if not u: abort(404)
    return u

# ================= АВТОРИЗАЦИЯ =================
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    child_id = None
    if current_user.role == 'parent' and current_user.child_username:
        child = User.query.filter_by(username=current_user.child_username).first()
        if child: child_id = child.id
    return render_template('dashboard.html', user=current_user, child_id=child_id)


from werkzeug.security import check_password_hash  # ✅ Убедитесь, что импортировано


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')

        # 🔍 Ищем пользователя строго по логину
        user = User.query.filter_by(username=username).first()

        if user:
            # Проверяем пароль (подставьте точное имя поля вашей модели: password или password_hash)
            stored_pw = getattr(user, 'password_hash', getattr(user, 'password', None))
            if stored_pw and check_password_hash(stored_pw, password):
                login_user(user)
                flash('✅ Вход выполнен успешно')
                return redirect(url_for('dashboard'))

        flash('❌ Неверный логин или пароль')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', '').strip()
        class_grade = request.form.get('class_grade')
        child_username = request.form.get('child_username', '').strip()
        privacy = request.form.get('privacy_consent')

        if not username or not password or not role:
            flash('❌ Заполните логин, пароль и роль')
            return redirect(url_for('register'))
        if not privacy:
            flash('❌ Необходимо дать согласие на обработку данных')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('❌ Этот логин уже занят')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)

        try:
            new_user = User(
                username=username,
                password=hashed_pw,
                role=role,
                class_grade=int(class_grade) if role == 'student' and class_grade else None,
                child_username=child_username if role == 'parent' else None,
                # 🔑 ДАТА РОЖДЕНИЯ ПОЛНОСТЬЮ УБРАНА
            )
            db.session.add(new_user)
            db.session.commit()
            flash('✅ Регистрация успешна! Теперь войдите в систему.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Ошибка при создании аккаунта: {str(e)}')
            print(f"[DEBUG] Ошибка регистрации: {e}")

    return render_template('register.html')
    # ================= СТРАНИЦЫ ПОЛЬЗОВАТЕЛЕЙ =================
@app.route('/profile/<int:user_id>')
@login_required
def profile(user_id):
    u = get_target_user_or_404(user_id)
    if current_user.role not in ['admin', 'parent', 'student'] or (current_user.role != 'admin' and current_user.id != u.id and current_user.role != 'parent' and u.role != 'student'):
        if not (current_user.role == 'parent' and current_user.child_username and u.username == current_user.child_username):
            abort(403)
    child_id = None
    if u.role == 'parent' and u.child_username:
        child = User.query.filter_by(username=u.child_username).first()
        if child: child_id = child.id
    return render_template('profile.html', u=u, child_id=child_id)



# ================= 📝 АКТИВНЫЕ ДЗ (ОСНОВНАЯ ВКЛАДКА) =================
@app.route('/homework/<int:user_id>', methods=['GET', 'POST'])
@login_required
def homework(user_id):
    u = get_target_user_or_404(user_id)
    if current_user.role != 'admin':
        if current_user.id != u.id:
            if not (current_user.role == 'parent' and current_user.child_username == u.username):
                abort(403)

    if request.method == 'POST' and current_user.role == 'student' and current_user.id == u.id:
        content_id = request.form.get('content_id', type=int)
        item = db.session.get(Content, content_id)

        if item and item.page_type == 'homework' and item.target_user_id == u.id and not item.is_submitted:
            action = request.form.get('action')
            f = request.files.get('homework_file')
            if f and f.filename != '':
                orig = secure_filename(f.filename)
                uniq = f"hw_{u.id}_{item.id}_{int(datetime.now().timestamp())}_{orig}"
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], uniq))
                db.session.add(FileModel(filename=orig, filepath=uniq, uploader_id=current_user.id,
                                         target_user_id=u.id, context='homework', content_id=item.id))
            item.student_comment = request.form.get('student_comment', '').strip()
            if action == 'submit': item.is_submitted = True; flash('📤 Отправлено на проверку')
            elif action == 'upload': flash('💾 Черновик сохранён')
            db.session.commit()
            return redirect(url_for('homework', user_id=user_id, _anchor=f'hw_{content_id}'))
        else: flash('⚠️ Задание уже отправлено или не найдено')
        return redirect(url_for('homework', user_id=user_id))

    items = Content.query.filter_by(target_user_id=u.id, page_type='homework', is_archived=False).order_by(Content.created_at.desc()).all()
    return render_template('homework.html', u=u, items=items)

# ================= 📦 АРХИВ ДЗ (ВТОРАЯ ВКЛАДКА) =================
@app.route('/homework/<int:user_id>/archive')
@login_required
def homework_archive(user_id):
    u = get_target_user_or_404(user_id)
    if current_user.role != 'admin':
        if current_user.id != u.id:
            if not (current_user.role == 'parent' and current_user.child_username == u.username):
                abort(403)

    items = Content.query.filter_by(target_user_id=u.id, page_type='homework', is_archived=True).order_by(Content.created_at.desc()).all()
    return render_template('homework_archive.html', u=u, items=items)




# ================= КАЛЕНДАРЬ: УЧЕНИК/РОДИТЕЛЬ (ТОЛЬКО ПУБЛИЧНЫЕ) =================
# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def get_student_color(student_id):
    sc = StudentColor.query.filter_by(student_id=student_id).first()
    if sc: return sc.color
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#e67e22']
    return colors[student_id % len(colors)]

def prepare_calendar_data(items, year, month, is_general=False):
    import calendar
    month_names = {1:'Январь',2:'Февраль',3:'Март',4:'Апрель',5:'Май',6:'Июнь',
                   7:'Июль',8:'Август',9:'Сентябрь',10:'Октябрь',11:'Ноябрь',12:'Декабрь'}
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    calendar_weeks = calendar.monthcalendar(year, month)

    events_by_day = {}
    for e in items:
        if e.event_date.year == year and e.event_date.month == month:
            day = e.event_date.day
            if day not in events_by_day: events_by_day[day] = []
            events_by_day[day].append({
                'id': e.id, 'time': e.time_str, 'color': e.color,
                'comment': e.comment, 'is_private': e.is_private,
                'date_str': e.event_date.strftime('%Y-%m-%d'),
                'student_name': e.student.username if is_general and e.student else None,
                'student_color': get_student_color(e.target_user_id) if is_general and e.target_user_id else e.color
            })
    return {
        'month_names': month_names, 'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month, 'calendar_weeks': calendar_weeks,
        'events_by_day': events_by_day
    }


@app.route('/calendar/parent')
@login_required
def parent_calendar_redirect():
    if current_user.role != 'parent' or not current_user.child_username:
        abort(403)

    # Находим ребёнка родителя
    child = User.query.filter_by(username=current_user.child_username, role='student').first()
    if not child:
        flash('⚠️ Ребёнок не найден в системе')
        return redirect(url_for('dashboard'))

    # Перенаправляем на стандартный маршрут календаря
    return redirect(url_for('student_calendar_view', user_id=child.id))

# ================= 📅 КАЛЕНДАРЬ УЧЕНИКА (ТОЛЬКО ПРОСМОТР) =================
@app.route('/calendar/<int:user_id>')
@login_required
def student_calendar_view(user_id):
    u = db.session.get(User, user_id)
    if not u: abort(404)

    # 🔒 Проверка прав: владелец, родитель или админ
    if current_user.role != 'admin' and current_user.id != u.id:
        if not (current_user.role == 'parent' and current_user.child_username == u.username):
            abort(403)

    today = datetime.today().date()
    year = request.args.get('year', default=today.year, type=int)
    month = request.args.get('month', default=today.month, type=int)

    # ✅ Ученик видит ТОЛЬКО публичные события
    items = CalendarEntry.query.filter_by(target_user_id=u.id, is_private=False).all()
    ctx = prepare_calendar_data(items, year, month, is_general=False)
    return render_template('calendar.html', u=u, items=items, year=year, month=month,
                           today=today, is_admin=False, **ctx)
# ================= 1️⃣ ОБЩИЙ КАЛЕНДАРЬ (ПУНКТ 1, 3, 4) =================
@app.route('/admin/calendar')
@login_required
def admin_calendar_general():
    if current_user.role != 'admin': abort(403)
    today = datetime.today().date()
    year = request.args.get('year', default=today.year, type=int)
    month = request.args.get('month', default=today.month, type=int)

    all_events = CalendarEntry.query.all()
    ctx = prepare_calendar_data(all_events, year, month, is_general=True)
    return render_template('admin_calendar_general.html', year=year, month=month, today=today, all_events=all_events, **ctx)

# ================= ДОБАВЛЕНИЕ В ОБЩИЙ КАЛЕНДАРЬ =================
@app.route('/admin/calendar/add_general', methods=['POST'])
@login_required
def admin_calendar_add_general():
    if current_user.role != 'admin': abort(403)
    date_str = request.form.get('event_date')
    time_str = request.form.get('time_str', '').strip()
    color = request.form.get('color', '#95a5a6')
    comment = request.form.get('comment', '').strip()
    try: event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except: event_date = datetime.today().date()

    db.session.add(CalendarEntry(target_user_id=None, event_date=event_date, time_str=time_str, color=color, comment=comment))
    db.session.commit()
    flash('✅ Добавлено в общий календарь')
    return redirect(url_for('admin_calendar_general'))

# ================= 2️⃣ СПИСОК УЧЕНИКОВ (ПУНКТ 1) =================
@app.route('/admin/calendar/students')
@login_required
def admin_calendar_students():
    if current_user.role != 'admin': abort(403)
    students = User.query.filter_by(role='student').all()
    for s in students:
        if not StudentColor.query.filter_by(student_id=s.id).first():
            db.session.add(StudentColor(student_id=s.id, color=get_student_color(s.id)))
    db.session.commit()
    return render_template('admin_calendar_students.html', students=students)

# ================= 3️⃣ РЕДАКТИРОВАНИЕ КАЛЕНДАРЯ УЧЕНИКА (ПУНКТ 2) =================
@app.route('/admin/calendar/student/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_calendar_edit_student(user_id):
    if current_user.role != 'admin': abort(403)
    u = db.session.get(User, user_id)
    if not u or u.role != 'student': abort(404)

    today = datetime.today().date()
    year = request.args.get('year', default=today.year, type=int)
    month = request.args.get('month', default=today.month, type=int)

    if request.method == 'POST':
        action = request.form.get('action')
        eid = request.form.get('event_id', '').strip()
        event_id = int(eid) if eid.isdigit() else None
        date_str = request.form.get('event_date', '')
        time_str = request.form.get('time_str', '').strip()
        color = request.form.get('color', '#3788d8')
        comment = request.form.get('comment', '').strip()
        is_private = 'is_private' in request.form

        try: event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except: event_date = today

        if action == 'delete' and event_id:
            ev = db.session.get(CalendarEntry, event_id)
            if ev and ev.target_user_id == u.id: db.session.delete(ev); db.session.commit()
        elif action == 'edit' and event_id:
            ev = db.session.get(CalendarEntry, event_id)
            if ev and ev.target_user_id == u.id:
                ev.event_date, ev.time_str, ev.color, ev.comment, ev.is_private = event_date, time_str, color, comment, is_private
                db.session.commit()
        elif action == 'add':
            db.session.add(CalendarEntry(target_user_id=u.id, event_date=event_date, time_str=time_str, color=color, comment=comment, is_private=is_private))
            db.session.commit()

        return redirect(url_for('admin_calendar_edit_student', user_id=user_id, year=year, month=month))

    items = CalendarEntry.query.filter_by(target_user_id=u.id).all()
    ctx = prepare_calendar_data(items, year, month, is_general=False)
    return render_template('admin_calendar_student_edit.html', u=u, items=items, year=year, month=month, today=today, student_color=get_student_color(u.id), **ctx)

@app.route('/feedback/<int:user_id>')
@login_required
def feedback(user_id):
    u = get_target_user_or_404(user_id)
    if current_user.role != 'admin' and not (current_user.role == 'parent' and current_user.id == u.id): abort(403)
    items = Content.query.filter_by(target_user_id=u.id, page_type='feedback').all()
    return render_template('feedback.html', u=u, items=items)

# ================= ЧАТ =================
@app.route('/my-chat', methods=['GET', 'POST'])
@login_required
def my_chat():
    if current_user.role not in ['student', 'parent']: abort(403)
    messages = ChatMessage.query.filter_by(target_user_id=current_user.id).order_by(ChatMessage.created_at).all()
    if request.method == 'POST':
        text = request.form.get('message', '').strip()
        f = request.files.get('chat_file')
        if text or (f and f.filename != ''):
            fp = fn = None
            if f and f.filename != '':
                fn = secure_filename(f.filename)
                uniq = f"chat_{current_user.id}_{int(datetime.now().timestamp())}_{fn}"
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], uniq))
                fn, fp = fn, uniq
            db.session.add(ChatMessage(sender_id=current_user.id, target_user_id=current_user.id, message=text if text else None, filename=fn, filepath=fp))
            db.session.commit()
            return redirect(url_for('my_chat'))
    return render_template('user_chat.html', messages=messages)


# ================= ЕДИНЫЙ СПИСОК ЧАТОВ (ученики + родители) =================
@app.route('/admin/chats')
@app.route('/admin/chats/<role>')  # Для обратной совместимости с закладками
@login_required
def admin_chats_list(role=None):
    if current_user.role != 'admin': abort(403)

    # Если роль не указана, показываем всех
    if role and role in ['student', 'parent']:
        users = User.query.filter_by(role=role).all()
    else:
        users = User.query.filter(User.role.in_(['student', 'parent'])).all()

    chat_list = []
    for u in users:
        last_msg = ChatMessage.query.filter_by(target_user_id=u.id).order_by(ChatMessage.created_at.desc()).first()
        unread = ChatMessage.query.filter_by(target_user_id=u.id, sender_id=u.id, is_read=False).count()
        total = ChatMessage.query.filter_by(target_user_id=u.id).count()

        # Показываем только тех, у кого есть сообщения или кто существует
        if last_msg or total > 0:
            chat_list.append({
                'user': u,
                'last_msg': last_msg,
                'unread': unread,
                'total': total
            })

    # Сортируем: сначала непрочитанные, потом по времени
    chat_list.sort(key=lambda x: (x['unread'] == 0, x['last_msg'].created_at if x['last_msg'] else datetime.min),
                   reverse=True)

    return render_template('admin_chats_list.html', chat_list=chat_list, active_role=role or 'all')


# ================= ОКНО ЧАТА (без изменений, работает с обоими ролями) =================
@app.route('/admin/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_chat_window(user_id):
    if current_user.role != 'admin': abort(403)
    user = db.session.get(User, user_id)
    if not user or user.role not in ['student', 'parent']: abort(404)

    # Помечаем сообщения как прочитанные
    ChatMessage.query.filter_by(target_user_id=user_id, sender_id=user_id, is_read=False).update(
        {ChatMessage.is_read: True})
    db.session.commit()

    messages = ChatMessage.query.filter_by(target_user_id=user_id).order_by(ChatMessage.created_at).all()

    if request.method == 'POST':
        text = request.form.get('message', '').strip()
        f = request.files.get('chat_file')
        if text or (f and f.filename != ''):
            filepath = filename = None
            if f and f.filename != '':
                fname = secure_filename(f.filename)
                unique = f"admin_chat_{user_id}_{int(datetime.now().timestamp())}_{fname}"
                full = os.path.join(app.config['UPLOAD_FOLDER'], unique)
                f.save(full)
                filename, filepath = fname, unique
            db.session.add(ChatMessage(sender_id=current_user.id, target_user_id=user_id,
                                       message=text if text else None, filename=filename, filepath=filepath))
            db.session.commit()
            return redirect(url_for('admin_chat_window', user_id=user_id))
    return render_template('admin_chat_window.html', user=user, messages=messages)

# ================= АДМИНКА =================
@app.route('/admin/panel')
@login_required
def admin_panel():
    if current_user.role != 'admin': abort(403)
    users = User.query.all()
    return render_template('admin_panel.html', users=users)


@app.route('/admin/edit/choose', methods=['POST'])
@login_required
def admin_edit_choose():
    if current_user.role != 'admin': abort(403)
    uid = request.form.get('user_id')
    pt = request.form.get('page_type')

    # 🔍 Для отладки (удалите после проверки)
    print(f"📩 POST: user_id={uid}, page_type={pt}")

    if not uid or not pt:
        flash('⚠️ Не выбран ученик или тип страницы')
        return redirect(url_for('admin_panel'))

    return redirect(url_for('admin_edit', user_id=int(uid), page_type=pt))


@app.route('/admin/edit/<int:user_id>/<page_type>', methods=['GET', 'POST'])
@login_required
def admin_edit(user_id, page_type):
    if current_user.role != 'admin': abort(403)
    u = db.session.get(User, user_id)
    if not u: abort(404)

    if request.method == 'POST':
        heading = request.form.get('heading')
        subheading = request.form.get('subheading')
        comment = request.form.get('comment')

        if page_type in ['homework', 'theory']:
            allow = (page_type == 'homework')
            nc = Content(target_user_id=u.id, page_type=page_type, heading=heading,
                         subheading=subheading, comment=comment, allow_student_upload=allow)
            db.session.add(nc)
            db.session.flush()  # 🔑 Генерируем nc.id ДО создания файлов

            files = request.files.getlist('attach_files')
            saved_count = 0
            for f in files:
                if f and f.filename != '':
                    fn = secure_filename(f.filename)
                    uniq = f"{page_type}_{u.id}_{nc.id}_{int(datetime.now().timestamp())}_{fn}"
                    f.save(os.path.join(app.config['UPLOAD_FOLDER'], uniq))
                    db.session.add(FileModel(
                        filename=fn, filepath=uniq, uploader_id=current_user.id,
                        target_user_id=u.id, context=page_type, content_id=nc.id
                    ))
                    saved_count += 1

            print(f"✅ Сохранено {saved_count} файл(ов) для Content ID: {nc.id}")

        db.session.commit()
        flash(f'✅ Успешно сохранено (+ {saved_count if "saved_count" in locals() else 0} файлов)')
        return redirect(url_for('admin_edit', user_id=user_id, page_type=page_type))

    return render_template('edit_page.html', u=u, page_type=page_type)

@app.route('/admin/homework_review')
@login_required
def admin_homework_review():
    if current_user.role != 'admin': abort(403)
    return render_template('admin_homework_review.html', students=User.query.filter_by(role='student').all())

@app.route('/admin/homework_review/<int:user_id>')
@login_required
def admin_homework_review_student(user_id):
    if current_user.role != 'admin': abort(403)
    u = db.session.get(User, user_id)
    if not u or u.role != 'student': abort(404)
    items = Content.query.filter_by(target_user_id=u.id, page_type='homework', is_archived=False).all()
    return render_template('admin_homework_student.html', u=u, items=items)

@app.route('/admin/grade/<int:content_id>', methods=['POST'])
@login_required
def submit_grade(content_id):
    if current_user.role != 'admin': abort(403)
    item = db.session.get(Content, content_id)
    if not item or item.page_type != 'homework' or not item.is_submitted: abort(404)
    g = request.form.get('grade', type=int)
    tc = request.form.get('teacher_comment', '').strip()
    if g and 1 <= g <= 5:
        item.grade, item.teacher_comment = g, tc
        db.session.commit(); flash('✅ Оценка сохранена')
    else: flash('⚠️ Оценка от 1 до 5')
    return redirect(url_for('admin_homework_review_student', user_id=item.target_user_id))


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        abort(403)
    if current_user.id == user_id:
        flash('⚠️ Нельзя удалить собственный аккаунт')
        return redirect(url_for('admin_panel'))

    user_to_delete = db.session.get(User, user_id)
    if not user_to_delete:
        flash('⚠️ Пользователь не найден')
        return redirect(url_for('admin_panel'))

    try:
        # 🔹 Удаляем ВСЕ связанные записи в правильном порядке
        # 1. Чаты
        ChatMessage.query.filter((ChatMessage.sender_id == user_id) |
                                 (ChatMessage.target_user_id == user_id)).delete()
        # 2. Календарь
        CalendarEntry.query.filter_by(target_user_id=user_id).delete()
        # 3. Файлы
        FileModel.query.filter((FileModel.uploader_id == user_id) |
                               (FileModel.target_user_id == user_id)).delete()
        # 4. Контент (ДЗ, Теория)
        Content.query.filter_by(target_user_id=user_id).delete()
        # 5. ✅ Цвет ученика (новая строка — именно она фиксит ошибку)
        StudentColor.query.filter_by(student_id=user_id).delete()

        # 6. Только теперь удаляем самого пользователя
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'✅ Аккаунт `{user_to_delete.username}` успешно удалён')

    except Exception as e:
        db.session.rollback()
        flash(f'⚠️ Ошибка при удалении: {str(e)}')
        print(f"❌ ERROR: {e}")  # Для отладки в консоли

    return redirect(url_for('admin_panel'))


# ================= АРХИВ ДЗ: СПИСОК УЧЕНИКОВ =================
@app.route('/admin/archive')
@login_required
def admin_archive_list():
    if current_user.role != 'admin': abort(403)
    students = User.query.filter_by(role='student').all()
    students_with_archive = []
    for s in students:
        count = Content.query.filter_by(target_user_id=s.id, page_type='homework', is_archived=True).count()
        if count > 0:
            students_with_archive.append({'user': s, 'count': count})
    return render_template('admin_archive_list.html', students=students_with_archive)

# ================= АРХИВ ДЗ: ПРОСМОТР КОНКРЕТНОГО УЧЕНИКА =================
@app.route('/admin/archive/<int:user_id>')
@login_required
def admin_archive_view(user_id):
    if current_user.role != 'admin': abort(403)
    u = db.session.get(User, user_id)
    if not u or u.role != 'student': abort(404)
    items = Content.query.filter_by(target_user_id=u.id, page_type='homework', is_archived=True).order_by(Content.created_at.desc()).all()
    return render_template('admin_archive_view.html', u=u, items=items)

# ================= ДЕЙСТВИЯ С ДЗ: АРХИВ / УДАЛИТЬ / ВОССТАНОВИТЬ =================
@app.route('/admin/hw_action/<int:content_id>', methods=['POST'])
@login_required
def admin_hw_action(content_id):
    if current_user.role != 'admin': abort(403)
    action = request.form.get('action')
    item = db.session.get(Content, content_id)
    if not item or item.page_type != 'homework': abort(404)

    target_user = item.target_user_id

    if action == 'archive':
        item.is_archived = True
        flash('📦 ДЗ отправлено в архив')
    elif action == 'unarchive':
        item.is_archived = False
        flash('🔄 ДЗ восстановлено из архива')
    elif action == 'delete':
        # Удаляем физические файлы
        for f in item.files:
            fp = os.path.join(app.config['UPLOAD_FOLDER'], f.filepath)
            if os.path.exists(fp):
                try: os.remove(fp)
                except: pass
            db.session.delete(f)
        db.session.delete(item)
        flash('🗑 ДЗ удалено навсегда')

    db.session.commit()
    return redirect(request.referrer or url_for('admin_homework_review_student', user_id=target_user))

# ================= ОБНОВЛЕНИЕ СТАРОГО МАРШРУТА (фильтр архивных) =================
# Найдите старый @app.route('/admin/homework_review/<int:user_id>') и замените строку запроса на:
# items = Content.query.filter_by(target_user_id=u.id, page_type='homework', is_archived=False).all()
# ================= СИСТЕМНЫЕ =================
@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(filename))


import os
from werkzeug.utils import secure_filename
from flask import render_template, request, redirect, url_for, flash, abort


# ================= 📖 ТЕОРИЯ: МОДЕЛИ =================
class TheoryBlock(db.Model):
    __tablename__ = 'theory_block'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    comment = db.Column(db.Text, nullable=True)  # 💬 Комментарий к блоку
    visible = db.Column(db.Boolean, default=True)
    topics = db.relationship('TheoryTopic', backref='block', cascade='all, delete-orphan', lazy=True)


class TheoryTopic(db.Model):
    __tablename__ = 'theory_topic'
    id = db.Column(db.Integer, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey('theory_block.id'), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(120), nullable=False)
    comment = db.Column(db.Text, nullable=True)  # 💬 Комментарий к теме
    visible = db.Column(db.Boolean, default=True)
    files = db.relationship('TheoryFile', backref='topic', cascade='all, delete-orphan', lazy=True)


class TheoryFile(db.Model):
    __tablename__ = 'theory_file'
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('theory_topic.id'), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)


THEORY_UPLOAD = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'), 'theory')
os.makedirs(THEORY_UPLOAD, exist_ok=True)


# ================= 📖 ТЕОРИЯ: МАРШРУТЫ =================
@app.route('/admin/theory')
@login_required
def admin_theory_select():
    if current_user.role != 'admin': abort(403)
    return render_template('admin_theory_select.html', students=User.query.filter_by(role='student').all())


@app.route('/admin/theory/<int:student_id>', methods=['GET', 'POST'])
@login_required
def admin_theory_manage(student_id):
    if current_user.role != 'admin': abort(403)
    student = db.session.get(User, student_id)
    if not student: abort(404)

    if request.method == 'POST':
        action = request.form.get('action')
        try:
            if action == 'add_block':
                db.session.add(TheoryBlock(student_id=student_id, title=request.form['title'],
                                           comment=request.form.get('comment', ''), visible=True))
            elif action == 'toggle_block':
                b = TheoryBlock.query.get(int(request.form['block_id']))
                if b: b.visible = not b.visible
            elif action == 'edit_block':
                b = TheoryBlock.query.get(int(request.form['block_id']))
                if b: b.title, b.comment = request.form['title'], request.form.get('comment', '')
            elif action == 'delete_block':
                db.session.delete(TheoryBlock.query.get(int(request.form['block_id'])))
            elif action == 'add_topic':
                bid = request.form.get('block_id')
                db.session.add(TheoryTopic(block_id=int(bid) if bid else None, student_id=student_id,
                                           title=request.form['title'], comment=request.form.get('comment', ''),
                                           visible=True))
            elif action == 'toggle_topic':
                t = TheoryTopic.query.get(int(request.form['topic_id']))
                if t: t.visible = not t.visible
            elif action == 'edit_topic':
                t = TheoryTopic.query.get(int(request.form['topic_id']))
                if t: t.title, t.comment = request.form['title'], request.form.get('comment', '')
            elif action == 'delete_topic':
                db.session.delete(TheoryTopic.query.get(int(request.form['topic_id'])))
            elif action == 'upload_file' and request.files.get('file'):
                f = request.files['file']
                t = TheoryTopic.query.get(int(request.form['topic_id']))
                if t and f.filename:
                    fn = secure_filename(f.filename)
                    uniq = f"{t.id}_{int(os.times().elapsed)}_{fn}"
                    f.save(os.path.join(THEORY_UPLOAD, uniq))
                    db.session.add(TheoryFile(topic_id=t.id, filename=fn, filepath=uniq))
            elif action == 'delete_file':
                tf = TheoryFile.query.get(int(request.form['file_id']))
                if tf:
                    fp = os.path.join(THEORY_UPLOAD, tf.filepath)
                    if os.path.exists(fp): os.remove(fp)
                    db.session.delete(tf)
            db.session.commit()
            flash('✅ Сохранено')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Ошибка: {str(e)}')
        return redirect(url_for('admin_theory_manage', student_id=student_id))

    blocks = TheoryBlock.query.filter_by(student_id=student_id).all()
    standalones = TheoryTopic.query.filter_by(student_id=student_id, block_id=None).all()
    return render_template('admin_theory.html', student=student, blocks=blocks, standalones=standalones)


@app.route('/theory/<int:student_id>')
@login_required
def student_theory_view(student_id):
    u = db.session.get(User, student_id)
    if not u: abort(404)
    if current_user.role not in ['admin', 'student', 'parent']: abort(403)
    if current_user.role != 'admin' and current_user.id != u.id:
        if not (current_user.role == 'parent' and current_user.child_username == u.username): abort(403)

    blocks = TheoryBlock.query.filter_by(student_id=u.id, visible=True).all()
    standalones = TheoryTopic.query.filter_by(student_id=u.id, block_id=None, visible=True).all()
    return render_template('student_theory.html', student=u, blocks=blocks, standalones=standalones)


@app.route('/make-admin-now')
def make_admin_now():
    from werkzeug.security import generate_password_hash
    if User.query.filter_by(username='admin').first():
        return "✅ Админ уже существует"

    # Создаём админа (автоматически подставит правильное поле пароля)
    admin = User(username='admin', role='admin')
    hashed = generate_password_hash('Admin123!')
    if hasattr(admin, 'password_hash'):
        admin.password_hash = hashed
    elif hasattr(admin, 'password'):
        admin.password = hashed

    db.session.add(admin)
    db.session.commit()
    return "✅ Админ создан! Логин: admin | Пароль: Admin123!<br>🗑️ УДАЛИТЕ этот маршрут из app.py и задеплойте заново!"


if __name__ == '__main__':
    # При первом запуске автоматически создаёт все таблицы в БД
    with app.app_context():
        db.create_all()

    # Запуск локального сервера в режиме отладки
    app.run(host='0.0.0.0', port=5000, debug=True)