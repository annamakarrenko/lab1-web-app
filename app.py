import os
import re
from datetime import datetime
from functools import lru_cache
from flask import Flask, render_template, request, make_response, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from faker import Faker

fake = Faker()

# Конфигурация
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_path = os.path.join(base_dir, 'templates')
if not os.path.exists(templates_path):
    templates_path = os.path.join(base_dir, 'app', 'templates')
static_path = os.path.join(base_dir, 'static')
if not os.path.exists(static_path):
    static_path = os.path.join(base_dir, 'app', 'static')

app = Flask(__name__, template_folder=templates_path, static_folder=static_path)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели БД 
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    last_name = db.Column(db.String(50))
    first_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role = db.relationship('Role', backref='users')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def full_name(self):
        parts = [self.last_name or '', self.first_name or '', self.middle_name or '']
        return ' '.join(p for p in parts if p).strip()

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

# Функции валидации 
def validate_login(login):
    if not login or len(login) < 5:
        return False, 'Логин должен содержать не менее 5 символов'
    if not re.match(r'^[a-zA-Z0-9]+$', login):
        return False, 'Логин должен состоять только из латинских букв и цифр'
    return True, ''

def validate_password(password):
    if not password:
        return False, 'Пароль не может быть пустым'
    if len(password) < 8:
        return False, 'Пароль должен содержать не менее 8 символов'
    if len(password) > 128:
        return False, 'Пароль должен содержать не более 128 символов'
    if not re.search(r'[A-ZА-Я]', password):
        return False, 'Пароль должен содержать хотя бы одну заглавную букву'
    if not re.search(r'[a-zа-я]', password):
        return False, 'Пароль должен содержать хотя бы одну строчную букву'
    if not re.search(r'[0-9]', password):
        return False, 'Пароль должен содержать хотя бы одну цифру'
    if ' ' in password:
        return False, 'Пароль не должен содержать пробелов'
    return True, ''

def validate_name(name, field_name):
    """Валидация имени/фамилии/отчества"""
    if not name or not name.strip():
        return False, f'Поле "{field_name}" не может быть пустым'
    return True, ''

# Инициализация БД 
def init_db():
    with app.app_context():
        db.create_all()
        # Создаём роли только если их нет
        roles = [
            Role(name='admin', description='Администратор системы'),
            Role(name='user', description='Обычный пользователь'),
            Role(name='moderator', description='Модератор')
        ]
        for role in roles:
            if not Role.query.filter_by(name=role.name).first():
                db.session.add(role)
        db.session.commit()
        
        # Создаём тестового пользователя только если его нет
        if not User.query.filter_by(login='admin').first():
            admin = User(login='admin', first_name='Администратор', last_name='Администраторов')
            admin.set_password('Admin123!')
            admin.role = Role.query.filter_by(name='admin').first()
            db.session.add(admin)
        db.session.commit()

init_db()

# Flask-Login 
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо войти в систему.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Старые маршруты (ЛР1-3) 
images_ids = ['7d4e9175-95ea-4c5f-8be5-92a6b708bb3c', '2d2ab7df-cdbc-48a8-a936-35bba702def5', '6e12f3de-d5fd-4ebb-855b-8cbc485278b7', 'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728', 'cab5b7f2-774e-4884-a200-0c0180fa777f']

def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = {'author': fake.name(), 'text': fake.text(), 'date': fake.date_time_between(start_date='-30d', end_date='now')}
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {'title': f'Заголовок поста {i+1}', 'text': fake.paragraph(nb_sentences=100), 'author': fake.name(), 'date': fake.date_time_between(start_date='-2y', end_date='now'), 'image_id': f'{images_ids[i]}.jpg', 'comments': generate_comments()}

@lru_cache
def posts_list():
    return sorted([generate_post(i) for i in range(5)], key=lambda p: p['date'], reverse=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/posts')
def posts():
    return render_template('posts.html', title='Посты', posts=posts_list())

@app.route('/posts/<int:index>', methods=['GET', 'POST'])
def post(index):
    posts = posts_list()
    if index >= len(posts):
        return render_template('404.html'), 404
    if request.method == 'POST':
        comment_text = request.form.get('comment')
        if comment_text:
            new_comment = {'author': fake.name(), 'text': comment_text, 'date': datetime.now(), 'replies': []}
            posts[index]['comments'].append(new_comment)
    return render_template('post.html', title=posts[index]['title'], post=posts[index], index=index)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/url-params')
def url_params():
    return render_template('url_params.html', title='Параметры URL', params=dict(request.args))

@app.route('/headers')
def headers():
    return render_template('headers.html', title='Заголовки запроса', headers=dict(request.headers))

@app.route('/cookies')
def cookies_page():
    return render_template('cookies.html', title='Cookie', cookies=dict(request.cookies), cookie_value=request.cookies.get('user_theme'))

@app.route('/set-cookie')
def set_cookie():
    response = make_response(redirect(url_for('cookies_page')))
    response.set_cookie('user_theme', 'dark', max_age=3600)
    return response

@app.route('/delete-cookie')
def delete_cookie():
    response = make_response(redirect(url_for('cookies_page')))
    response.delete_cookie('user_theme')
    return response

@app.route('/form-params', methods=['GET', 'POST'])
def form_params():
    form_data = dict(request.form) if request.method == 'POST' else None
    return render_template('form_params.html', title='Параметры формы', form_data=form_data)

def validate_phone(phone):
    if not phone:
        return None, 'Введите номер телефона'
    invalid_chars = re.findall(r'[^\d\+\s\(\)\-\.]', phone)
    if invalid_chars:
        return None, 'Недопустимые символы'
    digits = re.sub(r'\D', '', phone)
    if len(digits) not in [10, 11]:
        return None, 'Неверное количество цифр'
    if len(digits) == 11 and digits[0] not in ['7', '8']:
        return None, 'Неверное количество цифр'
    number = digits[1:] if len(digits) == 11 else digits
    return f"8-{number[:3]}-{number[3:6]}-{number[6:8]}-{number[8:]}", None

@app.route('/phone', methods=['GET', 'POST'])
def phone_form():
    error = None
    formatted_phone = None
    phone_input = None
    if request.method == 'POST':
        phone_input = request.form.get('phone', '')
        formatted_phone, error = validate_phone(phone_input)
    return render_template('phone.html', title='Проверка телефона', error=error, formatted_phone=formatted_phone, phone_input=phone_input)

@app.route('/visit-counter')
def visit_counter():
    count = session.get('visit_count', 0) + 1
    session['visit_count'] = count
    return render_template('visit_counter.html', title='Счётчик посещений', visit_count=count)

@app.route('/secret')
@login_required
def secret_page():
    secret_count = session.get('secret_visit_count', 0) + 1
    session['secret_visit_count'] = secret_count
    return render_template('secret.html', title='Секретная страница', visit_count=secret_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('Вы уже авторизованы!', 'info')
        return redirect(url_for('index'))
    next_url = request.args.get('next')
    if request.method == 'POST':
        login_input = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(login=login_input).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Добро пожаловать, {user.login}!', 'success')
            return redirect(next_url or url_for('index'))
        flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html', title='Вход в систему')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

# НОВЫЕ МАРШРУТЫ ЛР4 
@app.route('/users')
def user_list():
    users = User.query.all()
    return render_template('user_list.html', users=users)

@app.route('/users/<int:user_id>')
def user_view(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))
    return render_template('user_view.html', user=user)

@app.route('/users/create', methods=['GET', 'POST'])
@login_required
def user_create():
    roles = Role.query.all()
    errors = {}
    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        middle_name = request.form.get('middle_name', '').strip()
        role_id = request.form.get('role_id', type=int)

        is_valid = True
        # Валидация логина
        valid, msg = validate_login(login)
        if not valid:
            errors['login'] = msg
            is_valid = False
        elif User.query.filter_by(login=login).first():
            errors['login'] = 'Пользователь с таким логином уже существует'
            is_valid = False

        # Валидация пароля
        valid, msg = validate_password(password)
        if not valid:
            errors['password'] = msg
            is_valid = False

        # Валидация имени и фамилии
        valid, msg = validate_name(first_name, 'Имя')
        if not valid:
            errors['first_name'] = msg
            is_valid = False
        valid, msg = validate_name(last_name, 'Фамилия')
        if not valid:
            errors['last_name'] = msg
            is_valid = False

        if is_valid:
            try:
                new_user = User(login=login, first_name=first_name, last_name=last_name, middle_name=middle_name, role_id=role_id if role_id and role_id > 0 else None)
                new_user.set_password(password)
                db.session.add(new_user)
                db.session.commit()
                flash(f'Пользователь {new_user.full_name()} успешно создан', 'success')
                return redirect(url_for('user_list'))
            except Exception as e:
                flash(f'Ошибка при создании пользователя: {str(e)}', 'danger')
                db.session.rollback()
    return render_template('user_form.html', user=None, roles=roles, errors=errors)

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))
    roles = Role.query.all()
    errors = {}
    if request.method == 'POST':
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        middle_name = request.form.get('middle_name', '').strip()
        role_id = request.form.get('role_id', type=int)

        is_valid = True
        valid, msg = validate_name(first_name, 'Имя')
        if not valid:
            errors['first_name'] = msg
            is_valid = False
        valid, msg = validate_name(last_name, 'Фамилия')
        if not valid:
            errors['last_name'] = msg
            is_valid = False

        if is_valid:
            try:
                user.first_name = first_name
                user.last_name = last_name
                user.middle_name = middle_name
                user.role_id = role_id if role_id and role_id > 0 else None
                db.session.commit()
                flash(f'Данные пользователя {user.full_name()} обновлены', 'success')
                return redirect(url_for('user_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении: {str(e)}', 'danger')
                db.session.rollback()
    return render_template('user_form.html', user=user, roles=roles, errors=errors)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def user_delete(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))
    try:
        name = user.full_name()
        db.session.delete(user)
        db.session.commit()
        flash(f'Пользователь {name} успешно удалён', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
        db.session.rollback()
    return redirect(url_for('user_list'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    errors = {}
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(old_password):
            errors['old_password'] = 'Неверный старый пароль'
        elif new_password != confirm_password:
            errors['confirm_password'] = 'Пароли не совпадают'
        else:
            valid, msg = validate_password(new_password)
            if not valid:
                errors['new_password'] = msg
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Пароль успешно изменён', 'success')
                return redirect(url_for('index'))
    return render_template('change_password.html', errors=errors)

application = app
if __name__ == '__main__':
    app.run(debug=True)