# Public Routes

## Tag Pages

### GET /tag/<slug>

Display posts with a specific tag.

**Query Parameters:**
- `page` - Page number (default: 1)

**Note:** Tag pages use query parameter pagination (`?page=N`), not URL path pagination.

**Location:** `app/routes/public/browse.py:228`

```python
page = request.args.get("page", 1, type=int)
```

---

## Subscription Routes

### GET /confirm/<token>

Confirm newsletter subscription via token.

**Location:** `app/routes/public/subscribe.py:117`

**Rate Limit:** 5 per minute

**Behavior:**
- Valid token: Marks subscriber as confirmed, redirects to home
- Expired token: Removes subscriber, prompts to resubscribe
- Invalid token: Shows success message (enumeration prevention)

---

### GET /unsubscribe/<token>

Unsubscribe from the newsletter via token.

**Location:** `app/routes/public/subscribe.py:159`

**Rate Limit:** 5 per minute

**Behavior:**
- Valid token: Marks subscriber as unsubscribed
- Invalid token: Shows success message (enumeration prevention)