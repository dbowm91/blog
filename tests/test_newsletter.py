import pytest
from unittest.mock import patch, MagicMock
from app.models import Post, Subscriber
from app.utils import utc_now
from datetime import timedelta


def test_scheduler_filters_unsent_posts(app, db):
    """Test scheduler only picks up posts without newsletter_sent_at."""
    unsent = Post(title='Unsent', slug='unsent', body='Content',
                  published=True, published_at=utc_now())
    sent = Post(title='Sent', slug='sent', body='Content',
                published=True, published_at=utc_now(),
                newsletter_sent_at=utc_now())
    sub = Subscriber(email='sub@example.com', confirmed=True)
    db.session.add_all([unsent, sent, sub])
    db.session.commit()

    # Manually replicate the scheduler query
    posts = (
        Post.query.filter(
            Post.published == True,
            Post.published_at != None,
            Post.newsletter_sent_at == None,
        ).all()
    )
    slugs = [p.slug for p in posts]
    assert 'unsent' in slugs
    assert 'sent' not in slugs


def test_scheduler_confirmed_subscriber_filter(app, db):
    """Test scheduler query only includes confirmed, non-unsubscribed subscribers."""
    confirmed = Subscriber(email='confirmed@example.com', confirmed=True)
    unconfirmed = Subscriber(email='unconfirmed@example.com', confirmed=False)
    unsubscribed = Subscriber(email='unsub@example.com', confirmed=True,
                              unsubscribed_at=utc_now())
    db.session.add_all([confirmed, unconfirmed, unsubscribed])
    db.session.commit()

    subs = Subscriber.query.filter_by(confirmed=True).filter(
        Subscriber.unsubscribed_at.is_(None)
    ).all()
    emails = [s.email for s in subs]
    assert emails == ['confirmed@example.com']


def test_newsletter_test_endpoint(authenticated_client, db, sample_post):
    """Test POST /admin/newsletter-test works."""
    response = authenticated_client.post('/admin/newsletter-test', follow_redirects=True)
    assert response.status_code == 200


def test_newsletter_reset_endpoint(authenticated_client, db, sample_post):
    """Test POST /admin/newsletter-reset/<id> clears flag."""
    sample_post.newsletter_sent_at = utc_now()
    db.session.commit()

    response = authenticated_client.post(
        f'/admin/newsletter-reset/{sample_post.id}',
        follow_redirects=True)
    assert response.status_code == 200
    assert b'newsletter flag reset' in response.data.lower()


def test_newsletter_returns_false_on_smtp_failure(app, db):
    """Test send_newsletter returns False on SMTP connection failure."""
    from app.email import send_newsletter

    post = Post(title='Post', slug='post-fail', body='Content',
                published=True, published_at=utc_now())
    sub = Subscriber(email='test@example.com', confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    with patch('app.email.render_template', return_value='<html>Mock</html>'):
        with patch('app.email._connect_smtp', return_value=None):
            result = send_newsletter([post], [sub])

    assert result is False


def test_newsletter_returns_true_on_success(app, db):
    """Test send_newsletter returns True when all emails sent successfully."""
    from app.email import send_newsletter

    post = Post(title='Post', slug='post-ok', body='Content',
                published=True, published_at=utc_now())
    sub = Subscriber(email='test@example.com', confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    mock_server = MagicMock()
    with patch('app.email.render_template', return_value='<html>Mock</html>'):
        with patch('app.email._connect_smtp', return_value=mock_server):
            result = send_newsletter([post], [sub])

    assert result is True


def test_newsletter_returns_true_for_empty(app, db):
    """Test send_newsletter returns True (no-op) when no posts or subscribers."""
    from app.email import send_newsletter

    assert send_newsletter([], []) is True
    assert send_newsletter([1], []) is True
    assert send_newsletter([], [1]) is True
