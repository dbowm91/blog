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
    """Test favicon returns 204."""
    response = client.get('/favicon.ico')
    assert response.status_code == 204
