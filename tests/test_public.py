import pytest


def test_index(client, db, sample_post):
    """Test homepage returns 200."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Test Post' in response.data


def test_post_page(client, db, sample_post):
    """Test individual post page."""
    response = client.get('/post/test-post')
    assert response.status_code == 200
    assert b'Test Post' in response.data


def test_post_not_found(client, db):
    """Test 404 for non-existent post."""
    response = client.get('/post/non-existent')
    assert response.status_code == 404


def test_tag_page(client, db, sample_post, sample_tag):
    """Test tag page."""
    sample_post.tags.append(sample_tag)
    db.session.commit()
    response = client.get('/tag/python')
    assert response.status_code == 200


def test_search(client, db, sample_post):
    """Test search functionality."""
    response = client.get('/search?q=test')
    assert response.status_code == 200
    assert b'Test Post' in response.data


def test_search_empty_query(client, db):
    """Test search with empty query redirects."""
    response = client.get('/search?q=')
    assert response.status_code == 302


def test_search_no_results(client, db, sample_post):
    """Test search with no results."""
    response = client.get('/search?q=nonexistent')
    assert response.status_code == 200
    assert b'No posts match your search' in response.data


def test_robots_txt(client):
    """Test robots.txt returns text."""
    response = client.get('/robots.txt')
    assert response.status_code == 200
    assert b'Sitemap:' in response.data


def test_sitemap_xml(client, db, sample_post):
    """Test sitemap.xml returns valid XML."""
    response = client.get('/sitemap.xml')
    assert response.status_code == 200
    assert b'<?xml' in response.data
    assert b'test-post' in response.data


def test_rss_feed(client, db, sample_post):
    """Test RSS feed."""
    response = client.get('/rss')
    assert response.status_code == 200
    assert b'<?xml' in response.data
    assert b'Test Post' in response.data


def test_favicon(client):
    """Test favicon redirects to SVG."""
    response = client.get('/favicon.ico')
    assert response.status_code == 301


def test_subscribe_valid_email(client, db):
    """Test subscribing with a valid email."""
    response = client.post('/subscribe', data={'email': 'test@example.com'}, follow_redirects=True)
    assert response.status_code == 200


def test_subscribe_invalid_email(client, db):
    """Test subscribing with an invalid email."""
    response = client.post('/subscribe', data={'email': 'invalid'}, follow_redirects=True)
    assert b'valid email' in response.data


def test_subscribe_duplicate(client, db):
    """Test subscribing with an already-subscribed email."""
    from app.models import Subscriber
    sub = Subscriber(email='test@example.com')
    db.session.add(sub)
    db.session.commit()
    response = client.post('/subscribe', data={'email': 'test@example.com'}, follow_redirects=True)
    assert response.status_code == 200


def test_confirm_subscription(client, db):
    """Test confirming a subscription."""
    from app.models import Subscriber
    sub = Subscriber(email='test@example.com')
    db.session.add(sub)
    db.session.commit()
    response = client.get(f'/confirm/{sub.token}', follow_redirects=True)
    assert response.status_code == 200


def test_unsubscribe(client, db):
    """Test unsubscribing."""
    from app.models import Subscriber
    sub = Subscriber(email='test@example.com', confirmed=True)
    db.session.add(sub)
    db.session.commit()
    response = client.get(f'/unsubscribe/{sub.token}', follow_redirects=True)
    assert response.status_code == 200


def test_short_url_redirect(client, db, sample_post):
    """Test short URL redirects to post."""
    from app.base62 import encode
    code = encode(sample_post.id)
    response = client.get(f'/s/{code}')
    assert response.status_code == 302
    assert f'/post/{sample_post.slug}' in response.headers['Location']


def test_short_url_records_share_event(client, db, sample_post):
    """Test short URL records a share event."""
    from app.base62 import encode
    from app.models import ShareEvent
    code = encode(sample_post.id)
    client.get(f'/s/{code}')
    event = ShareEvent.query.filter_by(post_id=sample_post.id, platform='link').first()
    assert event is not None


def test_short_url_invalid_code(client):
    """Test short URL with invalid code redirects home."""
    response = client.get('/s/invalid')
    assert response.status_code == 302
