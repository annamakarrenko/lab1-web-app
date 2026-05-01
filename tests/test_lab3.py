import pytest

def test_visit_counter(client):
    """Проверка счётчика посещений"""
    response = client.get('/visit-counter')
    assert response.status_code == 200
    assert '1' in response.text
    
    response = client.get('/visit-counter')
    assert '2' in response.text

def test_login_page_get(client):
    """Проверка GET запроса к странице входа"""
    response = client.get('/login')
    assert response.status_code == 200
    assert 'Вход в систему' in response.text

def test_login_success(client):
    """Проверка успешной аутентификации с паролем qwerty"""
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
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert 'Неверное имя пользователя или пароль' in response.text

def test_login_failure_wrong_username(client):
    """Проверка неудачной попытки входа (неверный логин)"""
    response = client.post('/login', data={
        'username': 'wronguser',
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
    
    assert 'Секретная' in response.text
    assert 'Выйти' in response.text
    assert 'Войти' not in response.text

def test_navbar_links_unauthenticated(client):
    """Проверка что неавторизованному пользователю видна ссылка на секретную страницу, но Войти вместо Выйти"""
    response = client.get('/')
    
    # Ссылка на секретную страницу ВИДНА всем
    assert 'Секретная' in response.text
    # Неавторизованный НЕ должен видеть кнопку "Выйти"
    assert 'Выйти' not in response.text
    # Должен видеть кнопку "Войти"
    assert 'Войти' in response.text