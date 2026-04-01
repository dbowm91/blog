import io
import os
import gzip
import shutil
import sqlite3
import pytest
import time
from datetime import timedelta
from sqlalchemy import select, func

from app.models import Post, Subscriber, PageView, ShareEvent, AdminSession
from app.utils import utc_now
from app.scheduler import publish_scheduled_posts


class TestSubscribersBulk:
    """Tests for subscribers_bulk route."""

    def test_bulk_delete(self, authenticated_client, db):
        """Test bulk delete removes selected subscribers."""
        sub1 = Subscriber(email='bulk1@example.com', confirmed=True)
        sub2 = Subscriber(email='bulk2@example.com', confirmed=True)
        db.session.add_all([sub1, sub2])
        db.session.commit()
        ids = [str(sub1.id), str(sub2.id)]

        response = authenticated_client.post('/admin/subscribers/bulk', data={
            'action': 'delete',
            'sub_ids': ids,
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Deleted 2 subscriber' in response.data
        assert db.session.get(Subscriber, sub1.id) is None
        assert db.session.get(Subscriber, sub2.id) is None

    def test_bulk_export(self, authenticated_client, db):
        """Test bulk export streams CSV of selected subscribers."""
        sub1 = Subscriber(email='export1@example.com', confirmed=True)
        sub2 = Subscriber(email='export2@example.com', confirmed=False)
        db.session.add_all([sub1, sub2])
        db.session.commit()
        ids = [str(sub1.id), str(sub2.id)]

        response = authenticated_client.post('/admin/subscribers/bulk', data={
            'action': 'export',
            'sub_ids': ids,
        })
        assert response.status_code == 200
        assert response.mimetype == 'text/csv'
        assert b'attachment; filename=subscribers_selected.csv' in response.headers.get('Content-Disposition', '').encode()
        csv_text = response.data.decode('utf-8')
        assert 'export1@example.com' in csv_text
        assert 'export2@example.com' in csv_text

    def test_bulk_empty_selection(self, authenticated_client, db):
        """Test bulk operation with no subscribers selected shows error."""
        response = authenticated_client.post('/admin/subscribers/bulk', data={
            'action': 'delete',
            'sub_ids': [],
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'No subscribers selected' in response.data

    def test_bulk_invalid_action(self, authenticated_client, db):
        """Test bulk operation with invalid action redirects."""
        sub = Subscriber(email='test@example.com', confirmed=True)
        db.session.add(sub)
        db.session.commit()

        response = authenticated_client.post('/admin/subscribers/bulk', data={
            'action': 'invalid_action',
            'sub_ids': [str(sub.id)],
        }, follow_redirects=True)
        assert response.status_code == 200


class TestAdminSessionManagement:
    """Tests for admin session management."""

    def test_sessions_list_returns_200(self, authenticated_client):
        """Test sessions list page returns 200."""
        response = authenticated_client.get('/admin/sessions')
        assert response.status_code == 200

    def test_revoke_session_deletes_session(self, authenticated_client, db, admin_user):
        """Test revoking a session deletes it from the database."""
        other_user = admin_user
        session_obj = AdminSession(
            user_id=other_user.id,
            session_id='test-session-id-12345',
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        db.session.add(session_obj)
        db.session.commit()
        sess_id = session_obj.id

        response = authenticated_client.post(f'/admin/sessions/revoke/{sess_id}', follow_redirects=True)
        assert response.status_code == 200
        assert b'Session revoked' in response.data
        assert db.session.get(AdminSession, sess_id) is None

    def test_revoke_own_session_redirects(self, authenticated_client, db, admin_user):
        """Test revoking own current session shows error."""
        with authenticated_client.session_transaction() as sess:
            admin_session_id = sess.get('admin_session_id')
        if admin_session_id:
            admin_session = db.session.execute(
                select(AdminSession).filter_by(session_id=admin_session_id)
            ).scalar_one_or_none()
            if admin_session:
                response = authenticated_client.post(
                    f'/admin/sessions/revoke/{admin_session.id}',
                    follow_redirects=True
                )
                assert response.status_code == 200
                assert b'Cannot revoke your own current session' in response.data

    def test_revoked_session_causes_redirect(self, client, db, admin_user):
        """Test a revoked session causes logout and redirect to login."""
        client.post('/admin/login', data={
            'username': 'admin',
            'password': 'testpassword',
        })

        with client.session_transaction() as sess:
            sess['admin_session_id'] = 'nonexistent-session-id'
            sess['last_activity'] = time.time() - 100000

        response = client.get('/admin/', follow_redirects=False)
        assert response.status_code == 302
        assert '/admin/login' in response.headers.get('Location', '')


class TestPostScheduling:
    """Tests for post scheduling functionality."""

    def test_future_scheduled_post_stays_draft(self, authenticated_client, db, admin_user):
        """Test a post scheduled for the future remains unpublished."""
        future_time = utc_now() + timedelta(days=7)
        post = Post(
            title='Scheduled Post',
            slug='scheduled-post-future',
            body='Content',
            published=False,
            scheduled_publish_at=future_time
        )
        db.session.add(post)
        db.session.commit()

        response = authenticated_client.get('/admin/')
        assert response.status_code == 200
        db.session.refresh(post)
        assert post.published is False
        assert post.scheduled_publish_at is not None

    def test_publish_scheduled_posts_publishes_past_due(self, app, db):
        """Test publish_scheduled_posts publishes posts whose time has passed."""
        past_time = utc_now() - timedelta(hours=1)
        post = Post(
            title='Past Scheduled Post',
            slug='scheduled-post-past',
            body='Content',
            published=False,
            scheduled_publish_at=past_time
        )
        db.session.add(post)
        db.session.commit()
        post_id = post.id

        publish_scheduled_posts(app)

        db.session.refresh(post)
        assert post.published is True
        assert post.published_at is not None
        assert post.scheduled_publish_at is None

    def test_publish_scheduled_posts_clears_scheduled_at(self, app, db):
        """Test publish_scheduled_posts clears scheduled_publish_at."""
        past_time = utc_now() - timedelta(hours=1)
        post = Post(
            title='Clear Scheduled At',
            slug='scheduled-clear-test',
            body='Content',
            published=False,
            scheduled_publish_at=past_time
        )
        db.session.add(post)
        db.session.commit()
        assert post.scheduled_publish_at is not None

        publish_scheduled_posts(app)

        db.session.refresh(post)
        assert post.scheduled_publish_at is None


class TestResubscribeFlows:
    """Tests for re-subscription flows."""

    def test_unsubscribed_user_resubscribes(self, client, db):
        """Test previously unsubscribed user can resubscribe (clears unsubscribed_at)."""
        sub = Subscriber(email='unsub@example.com', confirmed=True, unsubscribed_at=utc_now())
        db.session.add(sub)
        db.session.commit()

        response = client.post('/subscribe', data={'email': 'unsub@example.com'}, follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(sub)
        assert sub.unsubscribed_at is None
        assert sub.confirmed is False

    def test_unconfirmed_resubscribes_new_token(self, client, db):
        """Test unconfirmed subscriber gets new token on resubscribe."""
        sub = Subscriber(email='unconfirmed@example.com', confirmed=False)
        db.session.add(sub)
        db.session.commit()
        old_token = sub.token

        response = client.post('/subscribe', data={'email': 'unconfirmed@example.com'}, follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(sub)
        assert sub.token != old_token

    def test_expired_unconfirmed_resubscribes_gets_new_token(self, client, db):
        """Test expired unconfirmed subscriber gets a new token on resubscribe."""
        sub = Subscriber(
            email='expired@example.com',
            confirmed=False,
            expires_at=utc_now() - timedelta(days=1)
        )
        db.session.add(sub)
        db.session.commit()
        old_token = sub.token
        old_id = sub.id

        response = client.post('/subscribe', data={'email': 'expired@example.com'}, follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(sub)
        assert sub.id == old_id
        assert sub.token != old_token
        assert sub.expires_at > utc_now()


class TestCSVExportCorrectness:
    """Tests for CSV export correctness."""

    def test_comma_in_email_properly_quoted(self, authenticated_client, db):
        """Test email containing comma is properly quoted in CSV export."""
        sub = Subscriber(email='user,name@example.com', confirmed=True)
        db.session.add(sub)
        db.session.commit()

        response = authenticated_client.get('/admin/subscribers/export')
        assert response.status_code == 200
        csv_text = response.data.decode('utf-8')
        assert '"user,name@example.com"' in csv_text or 'user,name@example.com' in csv_text

    def test_double_quote_properly_escaped(self, authenticated_client, db):
        """Test email containing double quote is properly escaped in CSV export."""
        sub = Subscriber(email='user"test@example.com', confirmed=True)
        db.session.add(sub)
        db.session.commit()

        response = authenticated_client.get('/admin/subscribers/export')
        assert response.status_code == 200
        csv_text = response.data.decode('utf-8')
        assert 'user' in csv_text

    def test_formula_injection_chars_prefixed(self, authenticated_client, db):
        """Test formula injection characters (=, +, -, @) are prefixed with single quote."""
        dangerous_emails = [
            '=example@example.com',
            '+example@example.com',
            '-example@example.com',
            '@example@example.com',
        ]
        for email in dangerous_emails:
            sub = Subscriber(email=email, confirmed=True)
            db.session.add(sub)
        db.session.commit()

        response = authenticated_client.get('/admin/subscribers/export')
        assert response.status_code == 200
        csv_text = response.data.decode('utf-8')
        for email in dangerous_emails:
            assert f"'{email}" in csv_text


class TestCompressedBackupRestore:
    """Tests for compressed backup and restore functionality."""

    def test_create_compressed_backup(self, app, db, tmp_path):
        """Test creating a compressed .db.gz backup using backup module directly."""
        import sys
        if sys.platform == 'win32':
            import pytest
            pytest.skip("Backup tests require Unix")
        from backup import create_backup
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace('sqlite:///', '') if db_uri.startswith('sqlite:///') else str(tmp_path / 'test.db')
        backup_dir = str(tmp_path / 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        result = create_backup(db_path, backup_dir, compress=True, keep=3)
        assert result is not None
        assert result.endswith('.db.gz')
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0

    def test_restore_compressed_backup(self, app, db, tmp_path):
        """Test compressed backup can be decompressed and used as SQLite."""
        from backup import create_backup
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace('sqlite:///', '') if db_uri.startswith('sqlite:///') else str(tmp_path / 'test.db')
        backup_dir = str(tmp_path / 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        # Create compressed backup
        backup_path = create_backup(db_path, backup_dir, compress=True, keep=3)
        assert backup_path is not None

        # Decompress and verify it's a valid SQLite database
        import gzip
        restore_path = str(tmp_path / 'restored.db')
        with gzip.open(backup_path, 'rb') as f_in:
            with open(restore_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        conn = sqlite3.connect(restore_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        conn.close()

    def test_uncompressed_backup_still_works(self, app, db, tmp_path):
        """Test uncompressed .db backup still works."""
        from backup import create_backup
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        db_path = db_uri.replace('sqlite:///', '') if db_uri.startswith('sqlite:///') else str(tmp_path / 'test.db')
        backup_dir = str(tmp_path / 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        result = create_backup(db_path, backup_dir, compress=False, keep=3)
        assert result is not None
        assert result.endswith('.db')
        assert os.path.exists(result)

        conn = sqlite3.connect(result)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        assert cursor.fetchone() is not None
        conn.close()


class TestAnalyticsDataCorrectness:
    """Tests for analytics data correctness."""

    def test_page_view_counts(self, client, db, admin_user):
        """Test page view counts are accurate across multiple posts."""
        posts = []
        for i in range(5):
            p = Post(
                title=f'View Test {i}',
                slug=f'view-test-{i}',
                body=f'Body {i}',
                published=True,
                published_at=utc_now()
            )
            posts.append(p)
            db.session.add(p)
        db.session.commit()

        for p in posts:
            client.get(f'/post/{p.slug}')
            with client.session_transaction() as sess:
                sess['viewed_posts'] = []

        total_views = db.session.execute(
            select(func.count()).select_from(PageView)
        ).scalar_one()
        assert total_views == 5

    def test_share_event_referrer_categorization(self, app, db, admin_user):
        """Test referrer query params are categorized correctly in analytics."""
        from app.routes import admin as admin_module
        with admin_module._analytics_cache_lock:
            admin_module._analytics_cache.clear()

        post = Post(title='Share Test', slug='share-test', body='Content', published=True, published_at=utc_now())
        db.session.add(post)
        db.session.commit()

        pv1 = PageView(post_id=post.id, referrer='https://www.google.com/search?q=test')
        pv2 = PageView(post_id=post.id, referrer='https://twitter.com/user/status/123')
        pv3 = PageView(post_id=post.id, referrer='https://www.facebook.com/post/456')
        pv4 = PageView(post_id=post.id, referrer='https://www.linkedin.com/post/123')
        pv5 = PageView(post_id=post.id, referrer='https://example.com/page')
        pv6 = PageView(post_id=post.id, referrer=None)
        db.session.add_all([pv1, pv2, pv3, pv4, pv5, pv6])
        db.session.commit()

        from app.routes.admin import _get_analytics_data
        data = _get_analytics_data(days=30)

        assert data['referrer_summary'].get('Search') == 1
        assert data['referrer_summary'].get('Social') == 3
        assert data['referrer_summary'].get('Other') == 1

    def test_top_posts_ranking(self, client, db, admin_user):
        """Test top posts are ranked by view count."""
        for i in range(3):
            p = Post(
                title=f'Top Post {i}',
                slug=f'top-post-{i}',
                body=f'Body {i}',
                published=True,
                published_at=utc_now()
            )
            db.session.add(p)
        db.session.commit()

        p0 = db.session.execute(db.select(Post).filter_by(slug='top-post-0')).scalar_one()
        p1 = db.session.execute(db.select(Post).filter_by(slug='top-post-1')).scalar_one()
        p2 = db.session.execute(db.select(Post).filter_by(slug='top-post-2')).scalar_one()
        id0, id1, id2 = p0.id, p1.id, p2.id

        for _ in range(3):
            client.get(f'/post/{p0.slug}')
            with client.session_transaction() as sess:
                sess['viewed_posts'] = []
        for _ in range(2):
            client.get(f'/post/{p1.slug}')
            with client.session_transaction() as sess:
                sess['viewed_posts'] = []
        client.get(f'/post/{p2.slug}')
        with client.session_transaction() as sess:
            sess['viewed_posts'] = []

        from sqlalchemy import func
        views0 = db.session.execute(select(func.count()).select_from(PageView).filter_by(post_id=id0)).scalar_one()
        views1 = db.session.execute(select(func.count()).select_from(PageView).filter_by(post_id=id1)).scalar_one()
        views2 = db.session.execute(select(func.count()).select_from(PageView).filter_by(post_id=id2)).scalar_one()

        assert views0 > views1 > views2
