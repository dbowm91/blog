"""Tests for Phase 8 features: timezone-aware datetimes, FTS search, multi-admin, backup/restore."""

import os
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.models import User, Post
from app.utils import utc_now, UTCDateTime


# --- Phase 8.1: Timezone-aware datetimes ---

class TestTimezoneAwareDatetimes:
    def test_utc_now_returns_aware(self):
        """utc_now() returns a timezone-aware datetime."""
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_utc_now_is_utc(self):
        """utc_now() returns UTC time."""
        now = utc_now()
        assert now.tzinfo == timezone.utc

    def test_utc_datetime_type_decorator_bind(self):
        """UTCDateTime strips timezone on save."""
        dt_type = UTCDateTime()
        aware = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = dt_type.process_bind_param(aware, None)
        assert result.tzinfo is None
        assert result.hour == 10

    def test_utc_datetime_type_decorator_result(self):
        """UTCDateTime adds UTC timezone on read."""
        dt_type = UTCDateTime()
        naive = datetime(2024, 1, 15, 10, 30, 0)
        result = dt_type.process_result_value(naive, None)
        assert result.tzinfo == timezone.utc

    def test_utc_datetime_none_passthrough(self):
        """UTCDateTime passes None through."""
        dt_type = UTCDateTime()
        assert dt_type.process_bind_param(None, None) is None
        assert dt_type.process_result_value(None, None) is None

    def test_utc_datetime_non_utc_input(self):
        """UTCDateTime converts non-UTC input to UTC on bind."""
        dt_type = UTCDateTime()
        est = timezone(timedelta(hours=-5))
        aware_est = datetime(2024, 1, 15, 5, 0, 0, tzinfo=est)
        result = dt_type.process_bind_param(aware_est, None)
        assert result.tzinfo is None
        assert result.hour == 10  # 5 AM EST = 10 AM UTC

    def test_post_datetime_aware_after_load(self, client, db, admin_user):
        """Post datetimes are timezone-aware after database round-trip."""
        post = Post(
            title='TZ Test', slug='tz-test', body='Test body',
            published=True, published_at=utc_now(),
        )
        db.session.add(post)
        db.session.commit()
        loaded = db.session.execute(select(Post).filter_by(slug='tz-test')).scalar_one_or_none()
        assert loaded.created_at.tzinfo == timezone.utc
        assert loaded.published_at.tzinfo == timezone.utc
        assert loaded.updated_at.tzinfo == timezone.utc

    def test_datetime_comparison_aware(self, client, db, admin_user):
        """Datetime comparisons work with aware datetimes."""
        post = Post(
            title='Compare Test', slug='compare-test', body='Test',
            published=True, published_at=utc_now() - timedelta(days=1),
        )
        db.session.add(post)
        db.session.commit()
        now = utc_now()
        assert post.published_at < now


# --- Phase 8.2: FTS search ---

class TestFTSSearch:
    def test_search_finds_post_by_title(self, client, db, sample_post):
        """Search finds a post by title content."""
        response = client.get('/search?q=Test')
        assert response.status_code == 200
        assert b'Test Post' in response.data

    def test_search_finds_post_by_body(self, client, db, sample_post):
        """Search finds a post by body content."""
        response = client.get('/search?q=Hello')
        assert response.status_code == 200
        assert b'Test Post' in response.data

    def test_search_no_results(self, client, db, sample_post):
        """Search returns 200 with no results message."""
        response = client.get('/search?q=zzzznotfound')
        assert response.status_code == 200

    def test_search_empty_query_redirects(self, client, db):
        """Empty search query redirects to index."""
        response = client.get('/search?q=')
        assert response.status_code == 302

    def test_search_excludes_drafts(self, client, db, sample_post):
        """Draft posts don't appear in search results for unique terms."""
        draft = Post(title='Draft Only Post', slug='draft-only', body='zzquniquezz body text', published=False)
        db.session.add(draft)
        db.session.commit()
        # Search for a unique term only in the body of the draft
        response = client.get('/search?q=zzquniquezz')
        # The draft post body contains "zzquniquezz" but it's unpublished.
        # The LIKE fallback filters by published=True, so the draft card shouldn't appear.
        assert b'Draft Only Post' not in response.data


# --- Phase 8.3: Multi-admin support ---

class TestMultiAdmin:
    def test_user_has_is_admin_field(self, db, admin_user):
        """Users have is_admin attribute."""
        assert hasattr(admin_user, 'is_admin')

    def test_users_list_requires_auth(self, client, db):
        """Users page requires authentication."""
        response = client.get('/admin/users')
        assert response.status_code == 302  # redirect to login

    def test_users_list_authenticated(self, client, db, authenticated_client):
        """Users page loads for authenticated user."""
        response = authenticated_client.get('/admin/users')
        assert response.status_code == 200
        assert b'admin' in response.data

    def test_create_user(self, client, db, authenticated_client):
        """Admin can create a new user."""
        response = authenticated_client.post('/admin/users/create', data={
            'username': 'newuser',
            'password': 'Password123!',
        }, follow_redirects=True)
        assert response.status_code == 200
        user = db.session.execute(select(User).filter_by(username='newuser')).scalar_one_or_none()
        assert user is not None
        assert user.is_admin is False

    def test_create_admin_user(self, client, db, authenticated_client):
        """Admin can create a new admin user."""
        response = authenticated_client.post('/admin/users/create', data={
            'username': 'newadmin',
            'password': 'Password123!',
            'is_admin': 'on',
        }, follow_redirects=True)
        assert response.status_code == 200
        user = db.session.execute(select(User).filter_by(username='newadmin')).scalar_one_or_none()
        assert user is not None
        assert user.is_admin is True

    def test_create_user_duplicate(self, client, db, authenticated_client):
        """Cannot create user with existing username."""
        authenticated_client.post('/admin/users/create', data={
            'username': 'dupuser',
            'password': 'Password123!',
        })
        response = authenticated_client.post('/admin/users/create', data={
            'username': 'dupuser',
            'password': 'Password456!',
        }, follow_redirects=True)
        assert b'already exists' in response.data

    def test_create_user_short_password(self, client, db, authenticated_client):
        """Cannot create user with short password."""
        response = authenticated_client.post('/admin/users/create', data={
            'username': 'shortpw',
            'password': 'short',
        }, follow_redirects=True)
        assert b'8 characters' in response.data

    def test_delete_user(self, client, db, authenticated_client):
        """Admin can delete another user."""
        user2 = User(username='deleteable')
        user2.set_password('password123')
        db.session.add(user2)
        db.session.commit()
        response = authenticated_client.post(f'/admin/users/delete/{user2.id}',
                                              follow_redirects=True)
        assert response.status_code == 200
        assert db.session.execute(select(User).filter_by(username='deleteable')).scalar_one_or_none() is None

    def test_cannot_delete_self(self, client, db, authenticated_client, admin_user):
        """Cannot delete your own account."""
        response = authenticated_client.post(f'/admin/users/delete/{admin_user.id}',
                                              follow_redirects=True)
        assert b'Cannot delete your own' in response.data

    def test_cannot_delete_last_admin(self, client, db, authenticated_client, admin_user):
        """Cannot delete the last admin user."""
        from sqlalchemy import select, func
        # First, make admin_user is an admin
        admin_user.is_admin = True
        db.session.commit()
        
        # Create another admin user (user2)
        user2 = User(username='otheruser')
        user2.set_password('password123')
        user2.is_admin = True
        db.session.add(user2)
        db.session.commit()
        
        # Count admins before - should be 2
        admin_count_before = db.session.execute(select(func.count(User.id)).filter_by(is_admin=True)).scalar_one()
        assert admin_count_before == 2
        
        # Delete user2 first (should succeed)
        response = authenticated_client.post(f'/admin/users/delete/{user2.id}',
                                              follow_redirects=True)
        assert response.status_code == 200
        
        # Verify user2 is deleted
        user2_exists = db.session.execute(select(User).filter_by(id=user2.id)).scalar_one_or_none()
        assert user2_exists is None
        
        # Count admins after - should be 1
        admin_count_after = db.session.execute(select(func.count(User.id)).filter_by(is_admin=True)).scalar_one()
        assert admin_count_after == 1
        
        # Attempt to delete admin_user (the last admin) - should be blocked
        response = authenticated_client.post(f'/admin/users/delete/{admin_user.id}',
                                              follow_redirects=True)
        # The response should redirect to users_list
        assert response.status_code == 200
        # Verify admin_user still exists
        admin_still_exists = db.session.execute(select(User).filter_by(id=admin_user.id)).scalar_one_or_none()
        assert admin_still_exists is not None

    def test_change_password(self, client, db, authenticated_client, admin_user):
        """Admin can change a user's password."""
        response = authenticated_client.post(
            f'/admin/users/password/{admin_user.id}',
            data={'password': 'Newpassword123!'},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert admin_user.check_password('Newpassword123!')

    def test_change_password_short(self, client, db, authenticated_client, admin_user):
        """Cannot set a short password."""
        response = authenticated_client.post(
            f'/admin/users/password/{admin_user.id}',
            data={'password': 'short'},
            follow_redirects=True,
        )
        assert b'8 characters' in response.data


# --- Phase 8.4: Backup/restore ---

class TestBackupRestore:
    def test_backup_page_requires_auth(self, client, db):
        """Backup page requires authentication."""
        response = client.get('/admin/backup')
        assert response.status_code == 302

    def test_backup_page_loads(self, client, db, authenticated_client):
        """Backup page loads for authenticated user."""
        response = authenticated_client.get('/admin/backup')
        assert response.status_code == 200
        assert b'Backup' in response.data

    def test_create_backup(self, client, db, authenticated_client, app):
        """Creating a backup produces a backup file."""
        response = authenticated_client.post('/admin/backup/create',
                                              follow_redirects=True)
        assert response.status_code == 200
        backup_dir = os.path.join(app.instance_path, 'backups')
        assert os.path.isdir(backup_dir)
        backups = [f for f in os.listdir(backup_dir) if f.startswith('blog_')]
        assert len(backups) >= 1

    def test_create_compressed_backup(self, client, db, authenticated_client, app):
        """Creating a compressed backup produces a .gz file."""
        response = authenticated_client.post('/admin/backup/create',
                                              data={'compress': '1'},
                                              follow_redirects=True)
        assert response.status_code == 200
        backup_dir = os.path.join(app.instance_path, 'backups')
        backups = [f for f in os.listdir(backup_dir) if f.endswith('.gz')]
        assert len(backups) >= 1

    def test_download_backup(self, client, db, authenticated_client, app):
        """Can download a created backup."""
        authenticated_client.post('/admin/backup/create')
        backup_dir = os.path.join(app.instance_path, 'backups')
        backups = [f for f in os.listdir(backup_dir) if f.startswith('blog_')]
        assert len(backups) >= 1
        response = authenticated_client.get(f'/admin/backup/download/{backups[0]}')
        assert response.status_code == 200
        assert len(response.data) > 0

    def test_download_invalid_filename(self, client, db, authenticated_client):
        """Cannot download with invalid filename."""
        response = authenticated_client.get('/admin/backup/download/../../etc/passwd')
        assert response.status_code in (400, 404)

    def test_delete_backup(self, client, db, authenticated_client, app):
        """Can delete a backup."""
        # Clean up any stale backups
        backup_dir = os.path.join(app.instance_path, 'backups')
        if os.path.isdir(backup_dir):
            for f in os.listdir(backup_dir):
                os.remove(os.path.join(backup_dir, f))
        authenticated_client.post('/admin/backup/create')
        backups = [f for f in os.listdir(backup_dir) if f.startswith('blog_')]
        assert len(backups) == 1
        response = authenticated_client.post(
            f'/admin/backup/delete/{backups[0]}',
            follow_redirects=True,
        )
        assert response.status_code == 200
        remaining = [f for f in os.listdir(backup_dir) if f.startswith('blog_')]
        assert len(remaining) == 0

    def test_delete_invalid_filename(self, client, db, authenticated_client):
        """Cannot delete with invalid filename."""
        response = authenticated_client.post('/admin/backup/delete/evil.sh')
        assert response.status_code == 400

    def test_restore_no_deprecation_warning(self, client, db, authenticated_client, app):
        """Restore does not emit DeprecationWarning."""
        import warnings
        import io
        import sys

        # Create a backup first
        authenticated_client.post('/admin/backup/create')

        # Get the backup filename
        backup_dir = os.path.join(app.instance_path, 'backups')
        backups = [f for f in os.listdir(backup_dir) if f.startswith('blog_')]
        assert len(backups) >= 1
        filename = backups[0]

        # Capture warnings
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Trigger restore path - we can't actually restore (would corrupt DB)
            # but we can call the route handler to exercise the code path
            response = authenticated_client.post(f'/admin/backup/restore/{filename}')
            # Response will be a redirect (success) or error - we're checking for warnings

        sys.stderr = old_stderr

        deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_warnings) == 0, f"DeprecationWarning found: {[str(x.message) for x in deprecation_warnings]}"
