"""Transaction helpers for the blog CMS."""

from functools import wraps

from sqlalchemy.exc import IntegrityError, OperationalError

from app.extensions import db


def transactional(f):
    """Decorator that handles common IntegrityError/OperationalError patterns."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (IntegrityError, OperationalError) as e:
            db.session.rollback()
            raise

    return decorated_function


def commit_with_slug_retry(page, title, max_retries=3):
    """Helper for slug collision retry on commit."""
    from app.routes.admin.helpers import _generate_unique_slug

    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except IntegrityError as e:
            if attempt == max_retries - 1:
                raise
            db.session.rollback()
            page.slug = _generate_unique_slug(type(page), title)
    return False