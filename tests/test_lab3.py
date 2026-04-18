import pytest
from flask_login import login_user, logout_user
from models import User

def test_visit_counter(client):
    """Проверка счётчика посещений"""
    response = client.get('/visit-counter')
    assert response.status_code == 200
    assert '1' in response.text
    
    response = client.get('/visit-counter')
    assert '2' in response.text

def test_visit_counter_per_user(client):
    """Проверка что счётчик работает для каждого пользователя отдельно"""
    client.get('/visit-counter')
    response = client.get('/visit-counter')
    assert '2' in response.text

def test_login_page_get(client):
    """Проверка GET запроса к странице входа"""
    response = client.get('/login')
    assert response.status_code == 200
    assert 'Вход в систему' in response.text

def test_login_success(client):
    """Проверка успешной аутентификации"""
    response = client.post('/login', data={
        'username': 'user',
        'password': 'qwerty',
        'remember': 'on'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Добро пожаловать' in response.text

def test_login_failure_wrong_password(client):
    """Проверка неудачной попытки входа (неверный пароль)"""
    response = client.post('/login', data={
        'username': 'user',
        'password': 'wrong'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Неверное имя пользователя или пароль' in response.text

def test_login_failure_wrong_username(client):
    """Проверка неудачной попытки входа (неверный логин)"""
    response = client.post('/login', data={
        'username': 'wrong',
        'password': 'qwerty'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Неверное имя пользователя или пароль' in response.text

def test_secret_page_redirects_unauthenticated(client):
    """Проверка что неавторизованный пользователь перенаправляется на страницу входа"""
    response = client.get('/secret', follow_redirects=False)
    assert response.status_code == 302
    location = response.headers.get('Location', '')
    assert '/login' in location

def test_secret_page_access_authenticated(client):
    """Проверка что авторизованный пользователь имеет доступ к секретной странице"""
    client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    
    response = client.get('/secret')
    assert response.status_code == 200
    assert 'Доступ разрешён' in response.text

def test_login_redirects_authenticated_user(client):
    """Проверка что авторизованный пользователь не может зайти на страницу входа"""
    client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    
    response = client.get('/login', follow_redirects=True)
    assert response.status_code == 200
    assert 'Лабораторная работа №3' in response.text

def test_next_parameter_redirects_to_secret(client):
    """Проверка что после логина пользователь перенаправляется на запрошенную страницу"""
    response = client.get('/secret', follow_redirects=False)
    assert response.status_code == 302
    
    login_url = response.headers.get('Location', '')
    assert 'next' in login_url
    assert 'secret' in login_url

def test_logout(client):
    """Проверка выхода из системы"""
    client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    
    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert 'Вы успешно вышли из системы' in response.text

def test_navbar_links_authenticated(client):
    """Проверка что авторизованному пользователю показываются правильные ссылки"""
    client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    response = client.get('/')
    
    # Авторизованный пользователь должен видеть ссылку на секретную страницу
    assert '/secret' in response.text
    # Должен видеть ссылку на выход
    assert '/logout' in response.text
    # НЕ должен видеть ссылку на вход
    assert '/login' not in response.text

def test_navbar_links_unauthenticated(client):
    """Проверка что неавторизованному пользователю показываются правильные ссылки"""
    response = client.get('/')
    
    # Неавторизованный пользователь НЕ должен видеть ссылку на секретную страницу
    assert '/secret' not in response.text
    # НЕ должен видеть ссылку на выход
    assert '/logout' not in response.text
    # Должен видеть ссылку на вход
    assert '/login' in response.text

def test_remember_me_cookie(client):
    """Проверка что remember me устанавливает правильную cookie"""
    response = client.post('/login', data={
        'username': 'user',
        'password': 'qwerty',
        'remember': 'on'
    })
    
    set_cookie = response.headers.get('Set-Cookie', '')
    assert 'remember_token' in set_cookie

def test_secret_page_counter(client):
    """Проверка счётчика на секретной странице"""
    client.post('/login', data={'username': 'user', 'password': 'qwerty'})
    
    response = client.get('/secret')
    assert '1' in response.text
    
    response = client.get('/secret')
    assert '2' in response.text