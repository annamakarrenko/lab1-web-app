import os
import random
import re
from datetime import datetime
from functools import lru_cache, wraps
from flask import Flask, render_template, request, make_response, redirect, url_for, session, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from faker import Faker

fake = Faker()

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

# Инициализация БД
from database import db, User, Role, VisitLog
db.init_app(app)

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
    if not name or not name.strip():
        return False, f'Поле "{field_name}" не может быть пустым'
    return True, ''


# Декоратор проверки прав 
def check_rights(required_role=None):
    """Декоратор для проверки прав доступа"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Для доступа к этой странице необходимо войти в систему.', 'warning')
                return redirect(url_for('login', next=request.url))
            
            if required_role and not current_user.has_role(required_role):
                flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Функция логирования посещений
def log_visit(path):
    """Логирование посещения страницы"""
    try:
        log = VisitLog(
            path=path,
            user_id=current_user.id if current_user.is_authenticated else None
        )
        db.session.add(log)
        db.session.commit()
    except Exception:
        db.session.rollback()


@app.before_request
def before_request():
    """Логируем все запросы к приложению (кроме статики)"""
    if not request.path.startswith('/static') and not request.path.startswith('/visit-logs'):
        log_visit(request.path)


# Инициализация БД
with app.app_context():
    from database import init_db
    init_db(app)


# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Для доступа к этой странице необходимо войти в систему.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Регистрация Blueprint
from blueprints.visit_logs import visit_logs
app.register_blueprint(visit_logs)

#Старые маршруты 
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
        user = User.query.filter_by(username=login_input).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            return redirect(next_url or url_for('user_list'))
        flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html', title='Вход в систему')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

# МАРШРУТЫ ЛР4 
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
@check_rights('admin')
def user_create():
    roles = Role.query.all()
    errors = {}
    if request.method == 'POST':
        login = request.form.get('login', '').strip()
        password = request.form.get('password', '')
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        patronymic = request.form.get('patronymic', '').strip()
        role_id = request.form.get('role_id', type=int)

        is_valid = True
        valid, msg = validate_login(login)
        if not valid:
            errors['login'] = msg
            is_valid = False
        elif User.query.filter_by(username=login).first():
            errors['login'] = 'Пользователь с таким логином уже существует'
            is_valid = False

        valid, msg = validate_password(password)
        if not valid:
            errors['password'] = msg
            is_valid = False

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
                new_user = User(username=login, first_name=first_name, last_name=last_name, patronymic=patronymic)
                new_user.set_password(password)
                if role_id and role_id > 0:
                    role = Role.query.get(role_id)
                    if role:
                        new_user.roles.append(role)
                db.session.add(new_user)
                db.session.commit()
                flash(f'Пользователь {new_user.get_full_name()} успешно создан', 'success')
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
    
    # проверка прав: админ может редактировать любого, обычный пользователь только себя
    if not current_user.has_role('admin') and current_user.id != user.id:
        flash('У вас недостаточно прав для доступа к данной странице.', 'danger')
        return redirect(url_for('index'))
    
    roles = Role.query.all()
    errors = {}
    if request.method == 'POST':
        last_name = request.form.get('last_name', '').strip()
        first_name = request.form.get('first_name', '').strip()
        patronymic = request.form.get('patronymic', '').strip()
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
                user.patronymic = patronymic
                
                # Только админ может менять роли
                if current_user.has_role('admin'):
                    user.roles.clear()
                    if role_id and role_id > 0:
                        role = Role.query.get(role_id)
                        if role:
                            user.roles.append(role)
                
                db.session.commit()
                flash(f'Данные пользователя {user.get_full_name()} обновлены', 'success')
                return redirect(url_for('user_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении: {str(e)}', 'danger')
                db.session.rollback()
    
    return render_template('user_form.html', user=user, roles=roles, errors=errors)

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@check_rights('admin')
def user_delete(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('user_list'))
    try:
        name = user.get_full_name()
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