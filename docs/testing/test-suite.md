# Testing Suite

## Test Fixtures

### FakeSubscriber Dataclass

Located at `tests/conftest.py:56-64`:

```python
@dataclass
class FakeSubscriber:
    """Test fixture for newsletter testing without real subscribers."""
    email: str
    token: str = "test"
    confirmed: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    unsubscribed_at: datetime | None = None
```

Used for testing newsletter functionality without requiring actual subscriber records in the database.

### mock_email Fixture

Located at `tests/conftest.py:170-173`:

```python
@pytest.fixture(scope="function")
def mock_email(mock_render, mock_smtp):
    """Combined mock for email rendering and SMTP sending."""
    yield
```

**Chaining**: `mock_email` chains `mock_render` and `mock_smtp` fixtures:
- `mock_render`: Mocks `app.email.render_template` to return `"<html>Mock</html>"`
- `mock_smtp`: Mocks `app.email._connect_smtp` to return a mock SMTP server

When `mock_email` is used, both rendering and SMTP sending are mocked, allowing tests to verify email flow without actual SMTP delivery.

### clean_analytics_cache Fixture

Located at `tests/shared_fixtures.py:16-23`:

Clears the analytics cache before and after each test to prevent cross-test pollution.

### ensure_buffer_disabled Fixture

Located at `tests/shared_fixtures.py:7-13` and `tests/conftest.py:186-194`:

Ensures the page view buffer is disabled during tests by:
1. Setting `PAGE_VIEW_BUFFER_SIZE = 0`
2. Calling `shutdown_page_view_buffer()`

## Database Test Patterns

### clean_db Nested Transaction Pattern

For test data cleanup in benchmarks, use nested transactions:

```python
def clean_db(db):
    """Clean up test data using nested transaction."""
    with db.session.begin_nested():
        # Delete test records
        db.session.execute(delete(Post).where(Post.title.like("test_%")))
```

This pattern allows:
- Rollback of test data after benchmark completes
- No interference with other tests
- Proper isolation in benchmarks

### Page View Buffer in Tests

The page view buffer can cause test interference:
- Buffer is started during `create_app()` if `PAGE_VIEW_BUFFER_SIZE > 0`
- In tests: disable via `app.config.PAGE_VIEW_BUFFER_SIZE = 0`
- Call `shutdown_page_view_buffer()` before and after tests

## Test Configuration

### Celery Eager Mode

Tests run Celery tasks synchronously:

```python
from celery import current_app as celery_app
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)
```

### E2E Test Server Startup Race Condition

When starting the E2E test server, a potential race condition exists where the server may not be fully ready when tests begin. Solution:

```python
import time

# Start server
server_process = subprocess.Popen(["python", "-m", "http.server", "8000"])

# Wait for server to be ready
time.sleep(1)  # Ensures server socket is listening

# Now run tests
```

The `time.sleep(1)` ensures the server's socket is actively listening before test clients attempt connections.