import pytest
from datetime import datetime

def test_posts_index(client):
    response = client.get("/posts")
    assert response.status_code == 200
    assert "Последние посты" in response.text

def test_posts_index_template(client, captured_templates, mocker, posts_list):
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
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    expected_date = posts_list[0]['date'].strftime('%d.%m.%Y')
    assert expected_date in response.text

def test_nonexistent_post_returns_404(client, mocker, posts_list):
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/999')
    assert response.status_code == 404

def test_index_page_template(client, captured_templates):
    with captured_templates as templates:
        _ = client.get('/')
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'index.html'

def test_about_page_template(client, captured_templates):
    with captured_templates as templates:
        _ = client.get('/about')
        assert len(templates) == 1
        template, context = templates[0]
        assert template.name == 'about.html'
        assert context['title'] == 'Об авторе'

def test_post_page_contains_comment_form(client, mocker, posts_list):
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
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert "Автор:" in response.text
    assert posts_list[0]['author'] in response.text

def test_post_page_contains_image(client, mocker, posts_list):
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert '<img' in response.text
    assert posts_list[0]['image_id'] in response.text

def test_base_template_contains_footer(client):
    response = client.get('/')
    assert '<footer' in response.text
    assert '© 2024' in response.text or '©' in response.text

def test_multiple_posts_on_posts_page(client, mocker, posts_list):
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
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts/0')
    assert f"<title>{posts_list[0]['title']}</title>" in response.text or posts_list[0]['title'] in response.text

def test_posts_page_has_read_more_links(client, mocker, posts_list):
    mocker.patch(
        "app.posts_list",
        return_value=posts_list,
        autospec=True
    )
    
    response = client.get('/posts')
    assert 'Читать дальше' in response.text
    assert '/posts/0' in response.text