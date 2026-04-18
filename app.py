import os
import random
import re
from datetime import datetime
from functools import lru_cache
from flask import Flask, render_template, request, make_response, redirect, url_for
from faker import Faker

fake = Faker()

base_dir = os.path.dirname(os.path.abspath(__file__))

templates_path = os.path.join(base_dir, 'templates')
if not os.path.exists(templates_path):
    templates_path = os.path.join(base_dir, 'app', 'templates')

static_path = os.path.join(base_dir, 'static')
if not os.path.exists(static_path):
    static_path = os.path.join(base_dir, 'app', 'static')

app = Flask(__name__,
            template_folder=templates_path,
            static_folder=static_path)
application = app

images_ids = [
    '7d4e9175-95ea-4c5f-8be5-92a6b708bb3c',
    '2d2ab7df-cdbc-48a8-a936-35bba702def5',
    '6e12f3de-d5fd-4ebb-855b-8cbc485278b7',
    'afc2cfe7-5cac-4b80-9b9a-d5c65ef0c728',
    'cab5b7f2-774e-4884-a200-0c0180fa777f'
]

def generate_comments(replies=True):
    comments = []
    for _ in range(random.randint(1, 3)):
        comment = {
            'author': fake.name(),
            'text': fake.text(),
            'date': fake.date_time_between(start_date='-30d', end_date='now')
        }
        if replies:
            comment['replies'] = generate_comments(replies=False)
        comments.append(comment)
    return comments

def generate_post(i):
    return {
        'title': f'Заголовок поста {i+1}',
        'text': fake.paragraph(nb_sentences=100),
        'author': fake.name(),
        'date': fake.date_time_between(start_date='-2y', end_date='now'),
        'image_id': f'{images_ids[i]}.jpg',
        'comments': generate_comments()
    }

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
            new_comment = {
                'author': fake.name(),
                'text': comment_text,
                'date': datetime.now(),
                'replies': []
            }
            posts[index]['comments'].append(new_comment)
    
    return render_template('post.html', title=posts[index]['title'], post=posts[index], index=index)

@app.route('/about')
def about():
    return render_template('about.html', title='Об авторе')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# 1. Параметры URL
@app.route('/url-params')
def url_params():
    params = dict(request.args)
    return render_template('url_params.html', title='Параметры URL', params=params)

# 2. Заголовки запроса
@app.route('/headers')
def headers():
    headers_dict = dict(request.headers)
    return render_template('headers.html', title='Заголовки запроса', headers=headers_dict)

# 3. Cookie
@app.route('/cookies')
def cookies_page():
    cookies_dict = dict(request.cookies)
    cookie_value = request.cookies.get('user_theme')
    return render_template('cookies.html', title='Cookie', 
                          cookies=cookies_dict, cookie_value=cookie_value)

@app.route('/set-cookie')
def set_cookie():
    # Создаем ответ с перенаправлением на страницу cookie
    response = make_response(redirect(url_for('cookies_page')))
    # Устанавливаем cookie на 1 час
    response.set_cookie('user_theme', 'dark', max_age=3600)
    return response

@app.route('/delete-cookie')
def delete_cookie():
    # Создаем ответ с перенаправлением на страницу cookie
    response = make_response(redirect(url_for('cookies_page')))
    # Удаляем cookie
    response.delete_cookie('user_theme')
    return response

# 4. Параметры формы
@app.route('/form-params', methods=['GET', 'POST'])
def form_params():
    form_data = None
    if request.method == 'POST':
        form_data = dict(request.form)
    return render_template('form_params.html', title='Параметры формы', form_data=form_data)

# 5. Проверка номера телефона (с валидацией)
def validate_phone(phone):
    """
    Валидация и форматирование номера телефона
    Возвращает: (отформатированный_номер, сообщение_об_ошибке)
    """
    if not phone:
        return None, 'Недопустимый ввод. Введите номер телефона.'
    
    # Проверка на недопустимые символы
    # Разрешенные символы: цифры, +, пробелы, скобки, дефисы, точки
    allowed_chars_pattern = r'[^\d\+\s\(\)\-\.]'
    invalid_chars = re.findall(allowed_chars_pattern, phone)
    if invalid_chars:
        return None, 'Недопустимый ввод. В номере телефона встречаются недопустимые символы.'
    
    # Извлекаем все цифры из номера
    digits = re.sub(r'\D', '', phone)
    
    # Проверка количества цифр
    if len(digits) not in [10, 11]:
        return None, 'Недопустимый ввод. Неверное количество цифр.'
    
    # Проверка для 11-значных номеров (должны начинаться с 7 или 8)
    if len(digits) == 11:
        if digits[0] not in ['7', '8']:
            return None, 'Недопустимый ввод. Неверное количество цифр.'
        # Убираем первую цифру (7 или 8)
        number = digits[1:]
    elif len(digits) == 10:
        number = digits
    else:
        return None, 'Недопустимый ввод. Неверное количество цифр.'
    
    # Форматируем номер в вид 8-XXX-XXX-XX-XX
    formatted = f"8-{number[:3]}-{number[3:6]}-{number[6:8]}-{number[8:]}"
    return formatted, None

@app.route('/phone', methods=['GET', 'POST'])
def phone_form():
    error = None
    formatted_phone = None
    phone_input = None
    
    if request.method == 'POST':
        phone_input = request.form.get('phone', '')
        formatted_phone, error = validate_phone(phone_input)
    
    return render_template('phone.html', title='Проверка телефона',
                         error=error, formatted_phone=formatted_phone, 
                         phone_input=phone_input)

if __name__ == '__main__':
    app.run(debug=True)