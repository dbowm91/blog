import pytest
from bs4 import BeautifulSoup


class TestInjectFooterData:
    """Tests for inject_footer_data context processor."""

    def test_footer_data_not_injected_for_admin_path(self, authenticated_client):
        """Footer data should NOT be injected for /admin/* paths."""
        response = authenticated_client.get("/admin/", follow_redirects=True)
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert footer is not None
        assert "Recent Posts" not in str(footer)

    def test_footer_data_is_injected_for_public_home(self, client, sample_post):
        """Footer data should be injected for public home path /."""
        response = client.get("/")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert footer is not None
        assert "Recent Posts" in str(footer)

    def test_footer_data_is_injected_for_archive(self, client, sample_post):
        """Footer data should be injected for /archive path."""
        response = client.get("/archive")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert footer is not None
        assert "Recent Posts" in str(footer)


class TestInjectShowFooterPosts:
    """Tests for inject_show_footer_posts context processor."""

    def test_show_footer_posts_false_for_search(self, client):
        """show_footer_posts should be False for /search path."""
        response = client.get("/search?q=test")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" not in str(footer)

    def test_show_footer_posts_false_for_tag(self, client, sample_tag):
        """show_footer_posts should be False for /tag/ path."""
        response = client.get("/tag/python")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" not in str(footer)

    def test_show_footer_posts_true_for_home(self, client, sample_post):
        """show_footer_posts should be True for / path."""
        response = client.get("/")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" in str(footer)

    def test_show_footer_posts_true_for_archive(self, client, sample_post):
        """show_footer_posts should be True for /archive path."""
        response = client.get("/archive")
        assert response.status_code == 200
        soup = BeautifulSoup(response.data, "html.parser")
        footer = soup.find("footer")
        assert "Recent Posts" in str(footer)


class TestInjectConfig:
    """Tests for inject_config context processor."""

    def test_inject_config_includes_site_title(self, client):
        """inject_config should include site_title."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"<title>" in response.data

    def test_inject_config_includes_canonical_url(self, client, sample_post):
        """inject_config should include canonical_url in the page."""
        response = client.get("/post/test-post")
        assert response.status_code == 200
        assert b"canonical" in response.data.lower()

    def test_inject_config_includes_current_year(self, client):
        """inject_config should include current_year."""
        from datetime import datetime

        response = client.get("/")
        assert response.status_code == 200
        assert str(datetime.now().year).encode() in response.data
