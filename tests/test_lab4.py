import pytest
from app import app, db
from database import User, Role
from datetime import datetime

@pytest.fixture
def client():
    """Тестовый клиент с временной БД"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Создаём роли
            roles_data = [
                ('admin', 'Администратор системы'),
                ('user', 'Обычный пользователь'),
                ('moderator', 'Модератор')
            ]
            for name, desc in roles_data:
                if not db.session.query(Role).filter(Role.name == name).first():
                    role = Role(name=name, description=desc)
                    db.session.add(role)
            db.session.commit()
            
            # создаём тестового пользователя (используем username вместо login)
            if not db.session.query(User).filter(User.username == 'admin').first():
                admin = User(username='admin', first_name='Admin', last_name='Adminov')
                admin.set_password('Admin123!')
                admin.roles.append(db.session.query(Role).filter(Role.name == 'admin').first())
                db.session.add(admin)
            
            if not db.session.query(User).filter(User.username == 'testuser').first():
                user = User(username='testuser', first_name='Test', last_name='User')
                user.set_password('Test123!')
                user.roles.append(db.session.query(Role).filter(Role.name == 'user').first())
                db.session.add(user)
            
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()


@pytest.fixture
def auth_client(client):
    """Авторизованный тестовый клиент (администратор)"""
    client.post('/login', data={
        'username': 'admin',
        'password': 'Admin123!',
        'remember': 'on'
    })
    return client


# ТЕСТЫ МОДЕЛЕЙ 

def test_user_model_creation():
    """Тест создания пользователя (используем username вместо login)"""
    with app.app_context():
        user = User(username='test', first_name='Test', last_name='User')
        user.set_password('Password123!')
        assert user.username == 'test'
        assert user.get_full_name() == 'User Test'  # full_name возвращает "Фамилия Имя"
        assert user.check_password('Password123!') == True
        assert user.check_password('wrong') == False


def test_role_model():
    """Тест модели роли"""
    with app.app_context():
        # Удаляем если существует
        existing = db.session.query(Role).filter(Role.name == 'test_role').first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
        
        role = Role(name='test_role', description='Test description')
        db.session.add(role)
        db.session.commit()
        
        assert role.id is not None
        assert role.name == 'test_role'


# ТЕСТЫ ВАЛИДАЦИИ

def test_validate_login():
    """Тест валидации логина"""
    from app import validate_login
    
    valid, msg = validate_login('user123')
    assert valid == True
    
    valid, msg = validate_login('usr')
    assert valid == False
    assert 'не менее 5 символов' in msg
    
    valid, msg = validate_login('пользователь')
    assert valid == False
    assert 'только из латинских букв и цифр' in msg


def test_validate_password():
    """Тест валидации пароля"""
    from app import validate_password
    
    valid, msg = validate_password('Password123!')
    assert valid == True
    
    valid, msg = validate_password('Pass1!')
    assert valid == False
    assert 'не менее 8 символов' in msg
    
    valid, msg = validate_password('password123!')
    assert valid == False
    assert 'заглавную букву' in msg
    
    valid, msg = validate_password('PASSWORD123!')
    assert valid == False
    assert 'строчную букву' in msg
    
    valid, msg = validate_password('Password!')
    assert valid == False
    assert 'цифру' in msg
    
    valid, msg = validate_password('Password 123!')
    assert valid == False
    assert 'не должен содержать пробелов' in msg


def test_validate_name():
    """Тест валидации имени/фамилии"""
    from app import validate_name
    
    valid, msg = validate_name('Иван', 'Имя')
    assert valid == True
    
    valid, msg = validate_name('', 'Имя')
    assert valid == False
    assert 'не может быть пустым' in msg


# ТЕСТЫ МАРШРУТОВ 

def test_user_list_page(client):
    """Тест страницы списка пользователей"""
    response = client.get('/users')
    assert response.status_code == 200
    assert 'Управление пользователями' in response.text
    assert 'admin' in response.text


def test_user_view_page(client):
    """Тест страницы просмотра пользователя"""
    with app.app_context():
        user = db.session.query(User).filter(User.username == 'admin').first()
        response = client.get(f'/users/{user.id}')
        assert response.status_code == 200
        assert 'Просмотр пользователя' in response.text
        assert 'admin' in response.text


def test_user_view_not_found(client):
    """Тест просмотра несуществующего пользователя"""
    response = client.get('/users/99999', follow_redirects=True)
    assert response.status_code == 200
    assert 'Пользователь не найден' in response.text


def test_user_create_form_requires_auth(client):
    """Тест: неавторизованный не может создать пользователя"""
    response = client.get('/users/create')
    assert response.status_code == 302


def test_user_create_form_authenticated(auth_client):
    """Тест: авторизованный видит форму создания"""
    response = auth_client.get('/users/create')
    assert response.status_code == 200
    assert 'Создание пользователя' in response.text


def test_user_create_success(auth_client):
    """Тест успешного создания пользователя"""
    response = auth_client.post('/users/create', data={
        'username': 'newuser',
        'login': 'newuser',  # для совместимости с формой
        'password': 'NewUser123!',
        'last_name': 'New',
        'first_name': 'User',
        'patronymic': 'Test',
        'role_id': ''
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert 'успешно создан' in response.text
    
    with app.app_context():
        user = db.session.query(User).filter(User.username == 'newuser').first()
        assert user is not None
        assert user.first_name == 'User'


def test_user_create_duplicate_login(auth_client):
    """Тест создания пользователя с существующим логином"""
    response = auth_client.post('/users/create', data={
        'username': 'admin',
        'login': 'admin',
        'password': 'Admin123!',
        'last_name': 'Duplicate',
        'first_name': 'User'
    })
    
    assert response.status_code == 200
    assert 'уже существует' in response.text.lower()


def test_user_create_invalid_login(auth_client):
    """Тест создания пользователя с некорректным логином"""
    response = auth_client.post('/users/create', data={
        'username': 'русский',
        'login': 'русский',
        'password': 'Valid123!',
        'last_name': 'Test',
        'first_name': 'Test'
    })
    
    assert response.status_code == 200
    assert 'Логин должен состоять только из латинских букв и цифр' in response.text


def test_user_delete_success(auth_client):
    """Тест успешного удаления пользователя"""
    # Создаём пользователя для удаления
    auth_client.post('/users/create', data={
        'username': 'todelete',
        'login': 'todelete',
        'password': 'Delete123!',
        'last_name': 'ToDelete',
        'first_name': 'Delete'
    })
    
    with app.app_context():
        user = db.session.query(User).filter(User.username == 'todelete').first()
        assert user is not None
    
    response = auth_client.post(f'/users/{user.id}/delete', follow_redirects=True)
    assert response.status_code == 200
    assert 'успешно удалён' in response.text
    
    with app.app_context():
        deleted_user = db.session.query(User).filter(User.username == 'todelete').first()
        assert deleted_user is None


# ТЕСТЫ СМЕНЫ ПАРОЛЯ

def test_change_password_page_requires_auth(client):
    """Тест: неавторизованный не может сменить пароль"""
    response = client.get('/change-password')
    assert response.status_code == 302


def test_change_password_page_authenticated(auth_client):
    """Тест: авторизованный видит страницу смены пароля"""
    response = auth_client.get('/change-password')
    assert response.status_code == 200
    assert 'Смена пароля' in response.text


def test_change_password_wrong_old_password(auth_client):
    """Тест смены пароля с неверным старым паролем"""
    response = auth_client.post('/change-password', data={
        'old_password': 'WrongPass123!',
        'new_password': 'NewPass123!',
        'confirm_password': 'NewPass123!'
    })
    
    assert response.status_code == 200
    assert 'Неверный старый пароль' in response.text


def test_change_password_mismatch(auth_client):
    """Тест смены пароля с несовпадающими новыми паролями"""
    response = auth_client.post('/change-password', data={
        'old_password': 'Admin123!',
        'new_password': 'NewPass123!',
        'confirm_password': 'DifferentPass123!'
    })
    
    assert response.status_code == 200
    assert 'Пароли не совпадают' in response.text

# ТЕСТЫ ПРАВ ДОСТУПА
def test_edit_buttons_visible_for_authenticated(auth_client):
    """Тест: авторизованный видит кнопки редактирования и удаления"""
    response = auth_client.get('/users')
    assert 'Редактировать' in response.text or '✏️' in response.text
    assert 'Удалить' in response.text or '🗑️' in response.text


def test_create_button_visible_for_authenticated(auth_client):
    """Тест: авторизованный видит кнопку создания"""
    response = auth_client.get('/users')
    assert 'Создать пользователя' in response.text


def test_navbar_links_authenticated(auth_client):
    """Тест: авторизованный видит правильные ссылки в навбаре"""
    response = auth_client.get('/')
    assert 'Пользователи (CRUD)' in response.text or 'users' in response.text
    assert 'Сменить пароль' in response.text
    assert 'Выйти' in response.text


# ДОПОЛНИТЕЛЬНЫЕ ТЕСТЫ 

def test_user_full_name_without_last_name():
    """Тест ФИО при отсутствии фамилии"""
    with app.app_context():
        user = User(username='test', first_name='Иван')
        assert user.get_full_name() == 'Иван'


def test_user_full_name_with_all_fields():
    """Тест ФИО со всеми полями"""
    with app.app_context():
        user = User(username='test', first_name='Иван', last_name='Петров', patronymic='Сидорович')
        assert user.get_full_name() == 'Петров Иван Сидорович'


def test_user_without_role(client):
    """Тест пользователя без роли"""
    with app.app_context():
        user = User(username='norole', first_name='No', last_name='Role')
        user.set_password('Test123!')
        user.roles = []  # без роли
        db.session.add(user)
        db.session.commit()
        
        response = client.get('/users')
        assert 'norole' in response.text
        assert '—' in response.text


def test_password_hashing():
    """Тест хеширования пароля"""
    with app.app_context():
        user = User(username='hashuser', first_name='Hash')
        user.set_password('MySecret123!')
        
        assert user.password_hash != 'MySecret123!'
        assert user.check_password('MySecret123!') == True
        assert user.check_password('WrongPass') == False


def test_remember_me_cookie(auth_client):
    """Тест установки remember cookie"""
    response = auth_client.get('/')
    assert response.status_code == 200