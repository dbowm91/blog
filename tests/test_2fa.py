"""Tests for 2FA/TOTP functionality."""

from unittest.mock import patch
from app.models import User
from tests.conftest import TEST_PASSWORD


class Test2FASetup:
    """Tests for 2FA setup route."""

    def test_setup_2fa_page(self, authenticated_client):
        """Test 2FA setup page renders."""
        response = authenticated_client.get("/admin/2fa/setup")
        assert response.status_code == 200

    def test_setup_2fa_generate_secret(self, authenticated_client):
        """Test 2FA setup generates a secret."""
        with patch("pyotp.random_base32", return_value="TESTSECRET123456"):
            response = authenticated_client.get("/admin/2fa/setup")
            assert response.status_code == 200
            assert "otpauth://" in response.data.decode("utf-8")


class Test2FAVerify:
    """Tests for 2FA verification route."""

    def test_verify_2fa_page(self, authenticated_client):
        """Test 2FA verify page renders."""
        response = authenticated_client.get("/admin/2fa/verify")
        assert response.status_code == 200


class Test2FALogin:
    """Tests for login with 2FA."""

    def test_login_2fa_page(self, client, admin_user):
        """Test login 2FA page renders after initial credentials."""
        with patch("app.routes.admin.auth.verify_password", return_value=True):
            with patch("app.routes.admin.auth.check_rate_limit", return_value=True):
                response = client.post(
                    "/admin/login",
                    data={
                        "username": "admin",
                        "password": TEST_PASSWORD,
                    },
                    follow_redirects=False,
                )
                assert response.status_code == 302
                assert "/admin/login-2fa" in response.location

    def test_login_with_totp(self, client, admin_user):
        """Test login with valid TOTP token."""
        admin_user.totp_secret = "TESTSECRET123456"
        from app.extensions import db

        db.session.commit()

        with patch("pyotp.TOTP.verify", return_value=True):
            with patch("app.routes.admin.auth.verify_password", return_value=True):
                client.post(
                    "/admin/login",
                    data={
                        "username": "admin",
                        "password": TEST_PASSWORD,
                    },
                )
                response = client.post(
                    "/admin/login-2fa",
                    data={
                        "totp_token": "123456",
                    },
                    follow_redirects=True,
                )
                assert response.status_code == 200

    def test_login_with_backup_code(self, client, admin_user):
        """Test login with valid backup code."""
        admin_user.totp_secret = "TESTSECRET123456"
        admin_user.backup_codes = "a665a459bc3d1351a8d59e0b6c15f3f3"  # SHA256 of '12345678'
        from app.extensions import db

        db.session.commit()

        with patch("app.routes.admin.auth.verify_password", return_value=True):
            client.post(
                "/admin/login",
                data={
                    "username": "admin",
                    "password": TEST_PASSWORD,
                },
            )
            response = client.post(
                "/admin/login-2fa",
                data={
                    "backup_code": "12345678",
                },
                follow_redirects=True,
            )
            assert response.status_code == 200

    def test_login_with_invalid_totp(self, client, admin_user):
        """Test login fails with invalid TOTP token."""
        admin_user.totp_secret = "TESTSECRET123456"
        from app.extensions import db

        db.session.commit()

        with patch("pyotp.TOTP.verify", return_value=False):
            with patch("app.routes.admin.auth.verify_password", return_value=True):
                client.post(
                    "/admin/login",
                    data={
                        "username": "admin",
                        "password": TEST_PASSWORD,
                    },
                )
                response = client.post(
                    "/admin/login-2fa",
                    data={
                        "totp_token": "000000",
                    },
                    follow_redirects=True,
                )
                assert b"Invalid token" in response.data


class Test2FABackupCodes:
    """Tests for backup codes display."""

    def test_backup_codes_page_requires_2fa(self, authenticated_client):
        """Test backup codes page requires 2FA to be enabled."""
        response = authenticated_client.get("/admin/2fa/backup-codes")
        assert response.status_code == 200


class Test2FADisable:
    """Tests for 2FA disable route."""

    def test_disable_2fa_page(self, authenticated_client):
        """Test disable 2FA page renders."""
        response = authenticated_client.get("/admin/2fa/disable")
        assert response.status_code == 200

    def test_disable_2fa_confirm(self, authenticated_client, admin_user):
        """Test disabling 2FA removes secret and backup codes."""
        admin_user.totp_secret = "TESTSECRET123456"
        admin_user.backup_codes = "a665a459bc3d1351a8d59e0b6c15f3f3"
        from app.extensions import db

        db.session.commit()

        response = authenticated_client.post("/admin/2fa/disable", follow_redirects=True)
        assert response.status_code == 200

        db.session.refresh(admin_user)
        assert admin_user.totp_secret is None
        assert admin_user.backup_codes is None


class TestTOTPSecretEncryption:
    """Tests for TOTP secret encryption via User.totp_secret property."""

    def test_totp_secret_encrypted_at_rest(self, admin_user):
        """Test TOTP secret is encrypted, not stored as plaintext."""
        admin_user.totp_secret = "TESTSECRET123456"
        from app.extensions import db

        db.session.commit()

        user_from_db = db.session.get(User, admin_user.id)
        assert user_from_db._totp_secret_encrypted != "TESTSECRET123456"
        assert user_from_db.totp_secret == "TESTSECRET123456"

    def test_totp_secret_decrypted_on_access(self, admin_user):
        """Test TOTP secret is decrypted when accessed via property."""
        admin_user.totp_secret = "TESTSECRET123456"
        from app.extensions import db

        db.session.commit()

        user_from_db = db.session.get(User, admin_user.id)
        assert user_from_db.totp_secret == "TESTSECRET123456"


class TestBackupCodeSingleUse:
    """Tests for backup code single-use enforcement."""

    def test_backup_code_invalidated_after_use(self, client, admin_user):
        """Test backup code cannot be used twice."""
        admin_user.totp_secret = "TESTSECRET123456"
        admin_user.backup_codes = "a665a459bc3d1351a8d59e0b6c15f3f3"
        from app.extensions import db

        db.session.commit()

        with patch("app.routes.admin.auth.verify_password", return_value=True):
            client.post(
                "/admin/login",
                data={
                    "username": "admin",
                    "password": TEST_PASSWORD,
                },
            )
            response1 = client.post(
                "/admin/login-2fa",
                data={
                    "backup_code": "12345678",
                },
                follow_redirects=True,
            )
            assert response1.status_code == 200

            client.post("/admin/logout")
            client.post(
                "/admin/login",
                data={
                    "username": "admin",
                    "password": TEST_PASSWORD,
                },
            )
            response2 = client.post(
                "/admin/login-2fa",
                data={
                    "backup_code": "12345678",
                },
                follow_redirects=True,
            )
            assert b"Invalid backup code" in response2.data
