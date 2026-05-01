"""Transaction helpers for the blog CMS."""

from contextlib import contextmanager
from functools import wraps

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.extensions import db


def transactional(f):
    """Decorator that handles common IntegrityError/OperationalError patterns."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except (IntegrityError, SQLAlchemyError) as e:
            db.session.rollback()
            raise

    return decorated_function


def commit_with_rollback():
    """Commit the current transaction, rolling back on error.

    Raises:
        IntegrityError, SQLAlchemyError: Re-raised after rollback
    """
    try:
        db.session.commit()
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        raise


@contextmanager
def db_transaction():
    """Context manager for database transactions with automatic rollback.

    Usage:
        with db_transaction():
            # do database work
            # commit is automatic on success
            # rollback on IntegrityError or SQLAlchemyError
    """
    try:
        yield
        db.session.commit()
    except (IntegrityError, SQLAlchemyError):
        db.session.rollback()
        raise


def commit_with_slug_retry(page, title, max_retries=3):
    """Helper for slug collision retry on commit."""
    from app.services.slug import generate_unique_slug

    for attempt in range(max_retries):
        try:
            db.session.commit()
            return True
        except IntegrityError as e:
            if attempt == max_retries - 1:
                raise
            db.session.rollback()
            page.slug = generate_unique_slug(type(page), title)
    return False