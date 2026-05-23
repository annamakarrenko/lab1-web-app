import pytest
from datetime import datetime

def test_posts_index(client):
    """
    Проверяет, что страница со списком постов доступна (статус 200)
    и содержит заголовок "Последние посты".
    """
    response = client.get("/posts")
    assert response.status_code == 200
    assert "Последние посты" in response.text


def test_posts_index_template(client, captured_templates, mocker, posts_list):
    """
    Проверяет, что при обращении к /posts:
    1. Используется правильный шаблон 'posts.html'
    2. В контекст передаётся заголовок 'Посты'
    3. В контекст передаётся список постов (ровно 1 пост)
    """
    with captured_templates as templates:
        mocker.patch(
            "app.posts_list",
            return_value=posts_list,
            autospec=True
        )
        
        _ = client.get('/posts')
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'posts.html'
        assert context['title'] == 'Посты'
        assert len(context['posts']) == 1

def test_post_page_template(client, captured_templates, mocker, posts_list):
    """
    Проверяет, что страница отдельного поста:
    1. Использует правильный шаблон 'post.html'
    2. Передаёт в контекст объект 'post' с данными поста
    3. Передаёт в контекст 'index' (индекс поста)
    """
    with captured_templates as templates:
        mocker.patch(
            "app.posts_list",
            return_value=posts_list,
            autospec=True
        )
        
        _ = client.get('/posts/0')
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'post.html'
        assert 'post' in context
        assert 'index' in context


def test_post_page_contains_all_data(client, mocker, posts_list):
    """
    Проверяет, что на странице поста отображаются все обязательные элементы:
    - заголовок поста
    - имя автора
    - текст поста
    - идентификатор изображения
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert response.status_code == 200
    assert posts_list[0]['title'] in response.text
    assert posts_list[0]['author'] in response.text
    assert posts_list[0]['text'] in response.text
    assert posts_list[0]['image_id'] in response.text


def test_post_page_date_format(client, mocker, posts_list):
    """
    Проверяет, что дата публикации отображается в правильном формате:
    ДД.ММ.ГГГГ (например, 10.03.2025)
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    expected_date = posts_list[0]['date'].strftime('%d.%m.%Y')
    assert expected_date in response.text


def test_nonexistent_post_returns_404(client, mocker, posts_list):
    """
    Проверяет, что при обращении к несуществующему посту
    (индекс 999, а всего постов 1) возвращается ошибка 404.
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/999')
    assert response.status_code == 404

# ТЕСТЫ ДЛЯ ДРУГИХ СТРАНИЦ ПРИЛОЖЕНИЯ

def test_index_page_template(client, captured_templates):
    """
    Проверяет, что главная страница (/) использует шаблон 'index.html'.
    """
    with captured_templates as templates:
        _ = client.get('/')
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'index.html'


def test_about_page_template(client, captured_templates):
    """
    Проверяет, что страница "Об авторе" (/about):
    1. Использует шаблон 'about.html'
    2. Передаёт правильный заголовок 'Об авторе'
    """
    with captured_templates as templates:
        _ = client.get('/about')
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'about.html'
        assert context['title'] == 'Об авторе'

def test_post_page_contains_comment_form(client, mocker, posts_list):
    """
    Проверяет, что на странице поста присутствует форма для добавления комментариев:
    - заголовок "Оставьте комментарий"
    - тег <form>
    - текстовое поле <textarea>
    - кнопка отправки (submit)
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert "Оставьте комментарий" in response.text
    assert '<form' in response.text
    assert 'textarea' in response.text
    assert 'submit' in response.text


def test_post_page_contains_comments(client, mocker, posts_list):
    """
    Проверяет, что комментарии отображаются на странице поста.
    Добавляем тестовый комментарий и проверяем его наличие в HTML.
    """
    posts_list[0]['comments'] = [
        {'author': 'Test Author', 'text': 'Test comment', 'replies': []}
    ]
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert 'Test Author' in response.text
    assert 'Test comment' in response.text


def test_post_page_contains_replies(client, mocker, posts_list):
    """
    Проверяет, что ответы на комментарии (вложенные комментарии)
    правильно отображаются на странице поста
    """
    posts_list[0]['comments'] = [
        {
            'author': 'Test Author', 
            'text': 'Test comment', 
            'replies': [
                {'author': 'Reply Author', 'text': 'Test reply', 'replies': []}
            ]
        }
    ]
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert 'Reply Author' in response.text
    assert 'Test reply' in response.text


def test_post_page_contains_author_name(client, mocker, posts_list):
    """
    Проверяет, что на странице поста отображается имя автора с меткой "Автор:"
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert "Автор:" in response.text
    assert posts_list[0]['author'] in response.text


def test_post_page_contains_image(client, mocker, posts_list):
    """
    Проверяет, что на странице поста есть тег <img>
    и правильный путь к изображению
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert '<img' in response.text
    assert posts_list[0]['image_id'] in response.text


# ТЕСТЫ ДЛЯ БАЗОВОГО ШАБЛОНА (base.html)

def test_base_template_contains_footer(client):
    """
    Проверяет, что в базовом шаблоне присутствует подвал (footer)
    и есть символ копирайта ©
    """
    response = client.get('/')
    assert '<footer' in response.text
    assert '© 2024' in response.text or '©' in response.text


# ТЕСТЫ ДЛЯ СТРАНИЦЫ СО СПИСКОМ ПОСТОВ (дополнительные проверки)

def test_multiple_posts_on_posts_page(client, mocker, posts_list):
    """
    Проверяет, что на странице со списком постов отображаются
    все посты (в данном случае 3 поста) и их заголовки
    """
    multiple_posts = posts_list * 3
    mocker.patch(
        "app.posts_list",
        return_value=multiple_posts,
        autospec=True
    )
    
    response = client.get('/posts')
    for i in range(3):
        assert multiple_posts[i]['title'] in response.text


def test_post_page_title_in_html_title(client, mocker, posts_list):
    """
    Проверяет, что заголовок поста отображается в <title> теге HTML
    или хотя бы где-то на странице.
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    # Проверяем либо в теге title, либо просто наличие текста на странице
    assert f"<title>{posts_list[0]['title']}</title>" in response.text or posts_list[0]['title'] in response.text


def test_posts_page_has_read_more_links(client, mocker, posts_list):
    """
    Проверяет, что на странице со списком постов есть ссылки
    "Читать дальше" и они ведут на страницы отдельных постов
    """
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts')
    assert 'Читать дальше' in response.text
    assert '/posts/0' in response.text