import pytest
from app.models import Post, Tag
from app.utils import utc_now


# --- RSS Tests ---

def test_rss_feed_content_structure(client, db, sample_post):
    """Test RSS feed has correct XML structure."""
    response = client.get('/rss')
    assert response.status_code == 200
    assert b'<?xml' in response.data
    assert b'<rss version="2.0"' in response.data
    assert b'<channel>' in response.data
    assert b'<item>' in response.data
    assert b'Test Post' in response.data
    assert b'test-post' in response.data


def test_rss_feed_excludes_drafts(client, db, admin_user):
    """Test RSS feed does not include draft posts."""
    draft = Post(
        title='Draft Post',
        slug='draft-post',
        body='Not ready yet.',
        published=False,
    )
    published = Post(
        title='Published Post',
        slug='published-post',
        body='Ready for the world.',
        published=True,
        published_at=utc_now(),
    )
    db.session.add_all([draft, published])
    db.session.commit()

    response = client.get('/rss')
    assert b'Published Post' in response.data
    assert b'Draft Post' not in response.data


# --- Bulk Operations Tests ---

def test_bulk_publish(authenticated_client, db, admin_user):
    """Test bulk publishing posts."""
    post1 = Post(title='Draft 1', slug='draft-1', body='Content', published=False)
    post2 = Post(title='Draft 2', slug='draft-2', body='Content', published=False)
    db.session.add_all([post1, post2])
    db.session.commit()

    response = authenticated_client.post('/admin/bulk', data={
        'action': 'publish',
        'post_ids': [str(post1.id), str(post2.id)],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Published 2 post' in response.data


def test_bulk_delete(authenticated_client, db, admin_user):
    """Test bulk deleting posts."""
    post1 = Post(title='Delete Me 1', slug='delete-1', body='Content', published=False)
    post2 = Post(title='Delete Me 2', slug='delete-2', body='Content', published=False)
    db.session.add_all([post1, post2])
    db.session.commit()
    ids = [str(post1.id), str(post2.id)]

    response = authenticated_client.post('/admin/bulk', data={
        'action': 'delete',
        'post_ids': ids,
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Deleted 2 post' in response.data


def test_bulk_no_selection(authenticated_client, db):
    """Test bulk operations with no posts selected."""
    response = authenticated_client.post('/admin/bulk', data={
        'action': 'publish',
        'post_ids': [],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'No posts selected' in response.data


def test_bulk_unpublish(authenticated_client, db, admin_user):
    """Test bulk unpublishing posts."""
    post = Post(title='Published', slug='pub', body='Content', published=True, published_at=utc_now())
    db.session.add(post)
    db.session.commit()

    response = authenticated_client.post('/admin/bulk', data={
        'action': 'unpublish',
        'post_ids': [str(post.id)],
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Unpublished 1 post' in response.data


# --- Tag Management Tests ---

def test_create_tag(authenticated_client, db):
    """Test creating a tag via the admin form."""
    response = authenticated_client.post('/admin/tags/create', data={
        'name': 'NewTag',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Tag &#39;NewTag&#39; created" in response.data


def test_rename_tag(authenticated_client, db):
    """Test renaming a tag."""
    tag = Tag(name='OldName', slug='oldname')
    db.session.add(tag)
    db.session.commit()

    response = authenticated_client.post(f'/admin/tags/rename/{tag.id}', data={
        'name': 'NewName',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Tag renamed" in response.data


def test_delete_tag(authenticated_client, db):
    """Test deleting a tag."""
    tag = Tag(name='DeleteMe', slug='deleteme')
    db.session.add(tag)
    db.session.commit()

    response = authenticated_client.post(f'/admin/tags/delete/{tag.id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"Tag &#39;DeleteMe&#39; deleted" in response.data


def test_create_tag_invalid_name(authenticated_client, db):
    """Test creating a tag with invalid characters is rejected."""
    response = authenticated_client.post('/admin/tags/create', data={
        'name': 'invalid<tag>name',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Invalid tag name' in response.data


def test_create_tag_empty_name(authenticated_client, db):
    """Test creating a tag with empty name is rejected."""
    response = authenticated_client.post('/admin/tags/create', data={
        'name': '   ',
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'cannot be empty' in response.data


def test_tags_list_page(authenticated_client, db):
    """Test tags list page loads."""
    tag = Tag(name='Python', slug='python')
    db.session.add(tag)
    db.session.commit()

    response = authenticated_client.get('/admin/tags')
    assert response.status_code == 200
    assert b'Python' in response.data


# --- Media Library Tests ---

def test_media_page_loads(authenticated_client, db):
    """Test media library page loads."""
    response = authenticated_client.get('/admin/media')
    assert response.status_code == 200


# --- Search Tests ---

def test_search_truncation(client, db, sample_post):
    """Test search query is truncated to 200 chars."""
    long_query = 'a' * 500
    response = client.get(f'/search?q={long_query}')
    assert response.status_code == 200


# --- Unsubscribe Tests ---

def test_unsubscribe_invalid_token_returns_success(client, db):
    """Test unsubscribe with invalid token returns identical success response."""
    response = client.get('/unsubscribe/nonexistent-token', follow_redirects=True)
    assert response.status_code == 200
    assert b'unsubscribed' in response.data


# --- Share Tracking Tests ---

def test_track_share_unpublished_post(client, db, admin_user):
    """Test share tracking rejects unpublished posts."""
    post = Post(title='Draft', slug='draft', body='Content', published=False)
    db.session.add(post)
    db.session.commit()

    response = client.post('/api/track-share',
        json={'post_id': post.id, 'platform': 'twitter'})
    assert response.status_code == 404


def test_track_share_published_post(client, db, sample_post):
    """Test share tracking works for published posts."""
    response = client.post('/api/track-share',
        json={'post_id': sample_post.id, 'platform': 'twitter'})
    assert response.status_code == 200


# --- Newsletter Reset Tests ---

def test_newsletter_reset(authenticated_client, db, sample_post):
    """Test resetting newsletter flag on a post."""
    sample_post.newsletter_sent_at = utc_now()
    db.session.commit()

    response = authenticated_client.post(
        f'/admin/newsletter-reset/{sample_post.id}',
        follow_redirects=True)
    assert response.status_code == 200
    assert b'newsletter flag reset' in response.data.lower()


# --- Slug Tests ---

def test_empty_slug_fallback():
    """Test empty string generates 'untitled' slug."""
    from app.utils import generate_slug
    assert generate_slug('') == 'untitled'
    assert generate_slug('   ') == 'untitled'
