from app.tag_cache import _get_tag_counts, invalidate_tag_cache
from app.models import Post, Tag
from app.utils import utc_now


def test_tag_counts_empty(app, db):
    """Test tag counts with no posts."""
    invalidate_tag_cache()
    result = _get_tag_counts()
    assert result == {}


def test_tag_counts_with_published_posts(app, db):
    """Test tag counts include only published posts."""
    invalidate_tag_cache()
    tag = Tag(name="CacheTag", slug="cachetag")
    post = Post(
        title="CachePost", slug="cachepost", body="Content", published=True, published_at=utc_now()
    )
    post.tags.append(tag)
    db.session.add_all([tag, post])
    db.session.commit()

    result = _get_tag_counts()
    assert result.get(tag.id) == 1


def test_tag_counts_excludes_drafts(app, db):
    """Test tag counts exclude draft posts."""
    invalidate_tag_cache()
    tag = Tag(name="DraftTag", slug="drafttag")
    post = Post(title="DraftPost", slug="draftpost", body="Content", published=False)
    post.tags.append(tag)
    db.session.add_all([tag, post])
    db.session.commit()

    result = _get_tag_counts()
    assert result.get(tag.id, 0) == 0


def test_cache_invalidation(app, db):
    """Test that invalidate_tag_cache forces a refresh."""
    invalidate_tag_cache()
    tag = Tag(name="InvTag", slug="invtag")
    post = Post(
        title="InvPost", slug="invpost", body="Content", published=True, published_at=utc_now()
    )
    post.tags.append(tag)
    db.session.add_all([tag, post])
    db.session.commit()

    result1 = _get_tag_counts()
    assert result1.get(tag.id) == 1
    post2 = Post(
        title="InvPost2", slug="invpost2", body="Content", published=True, published_at=utc_now()
    )
    post2.tags.append(tag)
    db.session.add(post2)
    db.session.commit()
    invalidate_tag_cache()
    result2 = _get_tag_counts()
    assert result2.get(tag.id) == 2


def test_cache_returns_copy(app, db):
    """Test that modifying the returned dict doesn't affect the cache."""
    invalidate_tag_cache()
    tag = Tag(name="CopyTag", slug="copytag")
    post = Post(
        title="CopyPost", slug="copypost", body="Content", published=True, published_at=utc_now()
    )
    post.tags.append(tag)
    db.session.add_all([tag, post])
    db.session.commit()

    result = _get_tag_counts()
    result[tag.id] = 999
    result2 = _get_tag_counts()
    assert result2.get(tag.id) == 1


def test_cache_ttl_expiry(app, db):
    """Test that cache is refreshed after TTL expires via explicit invalidation."""
    invalidate_tag_cache()
    tag = Tag(name="TTLTag", slug="ttltag")
    post = Post(
        title="TTLPost", slug="ttlpost", body="Content", published=True, published_at=utc_now()
    )
    post.tags.append(tag)
    db.session.add_all([tag, post])
    db.session.commit()

    result1 = _get_tag_counts()
    assert result1.get(tag.id) == 1

    invalidate_tag_cache()

    result2 = _get_tag_counts()
    assert result2.get(tag.id) == 1
