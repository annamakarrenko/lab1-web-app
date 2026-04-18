import pytest
from app import app, validate_phone

def test_url_params_page(client):
    """Проверка, что страница параметров URL доступна"""
    response = client.get('/url-params?a=1&b=2')
    assert response.status_code == 200
    assert 'a' in response.text
    assert '1' in response.text
    assert 'b' in response.text
    assert '2' in response.text

def test_url_params_empty(client):
    """Проверка страницы параметров URL без параметров"""
    response = client.get('/url-params')
    assert response.status_code == 200
    assert 'Параметры не переданы' in response.text

def test_headers_page(client):
    """Проверка страницы заголовков"""
    response = client.get('/headers')
    assert response.status_code == 200
    assert 'User-Agent' in response.text
    assert 'Host' in response.text

def test_cookies_page(client):
    """Проверка страницы cookie"""
    response = client.get('/cookies')
    assert response.status_code == 200

def test_set_cookie(client):
    """Проверка установки cookie"""
    response = client.get('/set-cookie')
    assert 'user_theme' in response.headers.get('Set-Cookie', '')
    assert 'dark' in response.headers.get('Set-Cookie', '')

def test_delete_cookie(client):
    """Проверка удаления cookie"""
    response = client.get('/delete-cookie')
    # Проверяем, что cookie помечена на удаление
    assert 'user_theme' in response.headers.get('Set-Cookie', '')
    assert 'Expires=' in response.headers.get('Set-Cookie', '')

def test_form_params_get(client):
    """Проверка GET запроса к странице формы"""
    response = client.get('/form-params')
    assert response.status_code == 200
    assert 'form' in response.text

def test_form_params_post(client):
    """Проверка POST запроса к странице формы"""
    response = client.post('/form-params', data={'name': 'Test', 'email': 'test@test.com'})
    assert response.status_code == 200
    assert 'Test' in response.text
    assert 'test@test.com' in response.text

def test_phone_page_get(client):
    """Проверка GET запроса к странице телефона"""
    response = client.get('/phone')
    assert response.status_code == 200
    assert 'Проверка номера телефона' in response.text

# Тесты валидации номера телефона
def test_validate_phone_valid_11_digits_with_plus():
    """Проверка корректного 11-значного номера с +7"""
    result, error = validate_phone('+7 (123) 456-75-90')
    assert error is None
    assert result == '8-123-456-75-90'

def test_validate_phone_valid_11_digits_with_8():
    """Проверка корректного 11-значного номера с 8"""
    result, error = validate_phone('8(123)4567590')
    assert error is None
    assert result == '8-123-456-75-90'

def test_validate_phone_valid_10_digits():
    """Проверка корректного 10-значного номера"""
    result, error = validate_phone('123.456.75.90')
    assert error is None
    assert result == '8-123-456-75-90'

def test_validate_phone_invalid_chars():
    """Проверка номера с недопустимыми символами"""
    result, error = validate_phone('abc123')
    assert 'недопустимые символы' in error
    assert result is None

def test_validate_phone_wrong_digit_count():
    """Проверка номера с неверным количеством цифр"""
    result, error = validate_phone('12345')
    assert 'Неверное количество цифр' in error
    assert result is None

def test_validate_phone_with_spaces_and_dashes():
    """Проверка номера с пробелами и дефисами"""
    result, error = validate_phone('8 123 456 75 90')
    assert error is None
    assert result == '8-123-456-75-90'

def test_phone_form_valid_submission(client):
    """Проверка отправки корректного номера через форму"""
    response = client.post('/phone', data={'phone': '+7 (123) 456-75-90'})
    assert response.status_code == 200
    assert '8-123-456-75-90' in response.text

def test_phone_form_invalid_submission(client):
    """Проверка отправки некорректного номера через форму"""
    response = client.post('/phone', data={'phone': 'abc123'})
    assert response.status_code == 200
    assert 'is-invalid' in response.text
    assert 'недопустимые символы' in response.text

def test_phone_form_wrong_digits(client):
    """Проверка отправки номера с неверным количеством цифр"""
    response = client.post('/phone', data={'phone': '123'})
    assert response.status_code == 200
    assert 'Неверное количество цифр' in response.text

def test_navigation_links_in_base(client):
    """Проверка наличия ссылок на новые страницы в навигации"""
    response = client.get('/')
    assert 'URL параметры' in response.text
    assert 'Заголовки' in response.text
    assert 'Cookie' in response.text
    assert 'Параметры формы' in response.text
    assert 'Проверка телефона' in response.text