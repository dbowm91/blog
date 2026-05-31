from unittest.mock import patch, MagicMock
from sqlalchemy import select
from app.models import Post, Subscriber
from app.utils import utc_now
import pytest

pytestmark = pytest.mark.slow


def test_scheduler_filters_unsent_posts(app, db):
    """Test scheduler only picks up posts without newsletter_sent_at."""
    unsent = Post(
        title="Unsent", slug="unsent", body="Content", published=True, published_at=utc_now()
    )
    sent = Post(
        title="Sent",
        slug="sent",
        body="Content",
        published=True,
        published_at=utc_now(),
        newsletter_sent_at=utc_now(),
    )
    sub = Subscriber(email="sub@example.com", confirmed=True)
    db.session.add_all([unsent, sent, sub])
    db.session.commit()

    # Manually replicate the scheduler query
    posts = (
        db.session.execute(
            select(Post).filter(
                Post.published,
                Post.published_at is not None,
                Post.newsletter_sent_at is None,
            )
        )
        .scalars()
        .all()
    )
    slugs = [p.slug for p in posts]
    assert "unsent" in slugs
    assert "sent" not in slugs


def test_scheduler_confirmed_subscriber_filter(app, db):
    """Test scheduler query only includes confirmed, non-unsubscribed subscribers."""
    confirmed = Subscriber(email="confirmed@example.com", confirmed=True)
    unconfirmed = Subscriber(email="unconfirmed@example.com", confirmed=False)
    unsubscribed = Subscriber(email="unsub@example.com", confirmed=True, unsubscribed_at=utc_now())
    db.session.add_all([confirmed, unconfirmed, unsubscribed])
    db.session.commit()

    subs = (
        db.session.execute(
            select(Subscriber)
            .filter_by(confirmed=True)
            .filter(Subscriber.unsubscribed_at.is_(None))
        )
        .scalars()
        .all()
    )
    emails = [s.email for s in subs]
    assert emails == ["confirmed@example.com"]


def test_newsletter_test_endpoint(authenticated_client, db, sample_post):
    """Test POST /admin/newsletter-test works."""
    response = authenticated_client.post("/admin/newsletter-test", follow_redirects=True)
    assert response.status_code == 200


def test_newsletter_reset_endpoint(authenticated_client, db, sample_post):
    """Test POST /admin/newsletter-reset/<id> clears flag."""
    sample_post.newsletter_sent_at = utc_now()
    db.session.commit()

    response = authenticated_client.post(
        f"/admin/newsletter-reset/{sample_post.id}", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"newsletter flag reset" in response.data.lower()


def test_newsletter_returns_false_on_smtp_failure(app, db):
    """Test send_newsletter returns False on SMTP connection failure."""
    from app.email import send_newsletter

    post = Post(
        title="Post", slug="post-fail", body="Content", published=True, published_at=utc_now()
    )
    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    with patch("app.email.render_template", return_value="<html>Mock</html>"):
        with patch("app.email._connect_smtp", return_value=None):
            result = send_newsletter([post], [sub])

    assert result is False


def test_newsletter_returns_true_on_success(app, db):
    """Test send_newsletter returns True when all emails sent successfully."""
    from app.email import send_newsletter

    post = Post(
        title="Post", slug="post-ok", body="Content", published=True, published_at=utc_now()
    )
    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    mock_server = MagicMock()
    with patch("app.email.render_template", return_value="<html>Mock</html>"):
        with patch("app.email._connect_smtp", return_value=mock_server):
            result = send_newsletter([post], [sub])

    assert result is True


def test_newsletter_returns_true_for_empty(app, db):
    """Test send_newsletter returns True (no-op) when no posts or subscribers."""
    from app.email import send_newsletter

    assert send_newsletter([], []) is True
    assert send_newsletter([1], []) is True
    assert send_newsletter([], [1]) is True


def test_newsletter_attempts_skip_after_max(app, db):
    """Test posts with >= max retry attempts are skipped."""
    max_attempts = 5
    exhausted = Post(
        title="Exhausted",
        slug="exhausted",
        body="Content",
        published=True,
        published_at=utc_now(),
        newsletter_attempts=max_attempts,
    )
    fresh = Post(
        title="Fresh",
        slug="fresh",
        body="Content",
        published=True,
        published_at=utc_now(),
        newsletter_attempts=0,
    )
    db.session.add_all([exhausted, fresh])
    db.session.commit()

    posts = (
        db.session.execute(
            select(Post).filter(
                Post.published,
                Post.published_at is not None,
                Post.newsletter_sent_at is None,
                Post.newsletter_attempts < max_attempts,
            )
        )
        .scalars()
        .all()
    )
    slugs = [p.slug for p in posts]
    assert "fresh" in slugs
    assert "exhausted" not in slugs


def test_newsletter_reset_clears_attempts(authenticated_client, db, sample_post):
    """Test newsletter reset also clears attempt count."""
    sample_post.newsletter_sent_at = utc_now()
    sample_post.newsletter_attempts = 3
    db.session.commit()

    authenticated_client.post(f"/admin/newsletter-reset/{sample_post.id}", follow_redirects=True)

    from app.models import Post

    post = db.session.get(Post, sample_post.id)
    assert post.newsletter_attempts == 0
    assert post.newsletter_sent_at is None


def test_newsletter_returns_true_after_reconnect(app, db):
    """Test send_newsletter returns True after successful SMTP reconnection."""
    import smtplib
    from app.email import send_newsletter

    post = Post(
        title="Post", slug="post-reconnect", body="Content", published=True, published_at=utc_now()
    )
    sub = Subscriber(email="test@example.com", confirmed=True)
    db.session.add_all([post, sub])
    db.session.commit()

    mock_server = MagicMock()
    # First call raises disconnect, second succeeds
    mock_server.sendmail.side_effect = [
        smtplib.SMTPServerDisconnected(),
        None,  # retry sendmail succeeds
    ]
    with patch("app.email.render_template", return_value="<html>Mock</html>"):
        with patch("app.email._connect_smtp") as mock_connect:
            mock_connect.return_value = mock_server
            result = send_newsletter([post], [sub])

    assert result is True
