# Models

## AdminSession Model

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to User |
| session_id | String(64) | Unique session identifier |
| ip_address | String(45) | Client IP address |
| user_agent | String(256) | Client user agent |
| created_at | UTCDateTime | Session creation timestamp |
| last_activity | UTCDateTime | Last activity timestamp |

**Location:** `app/models.py:325-340`

```python
last_activity = db.Column(UTCDateTime, default=utc_now)
```

---

## PostRevision Model

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| post_id | Integer | Foreign key to Post |
| title | String(200) | Post title at revision time |
| slug | String(200) | Post slug at revision time |
| body | Text | Post body at revision time |
| summary | String(500) | Post summary at revision time |
| created_at | UTCDateTime | Revision creation timestamp |
| author_id | Integer | Foreign key to User who created revision |

**Location:** `app/models.py:236-257`

```python
author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
```

---

## Series Relationship Ordering

Posts in a series are ordered by `PostSeries.order_index` (not by date or title).

**Location:** `app/models.py:558`

```python
posts = db.relationship("Post", secondary="post_series", back_populates="series", order_by="PostSeries.order_index")
```

---

## Webhook Model

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| name | String(100) | Webhook name |
| url | String(512) | Target URL |
| secret | String | AES-256-GCM encrypted secret (decrypted on access) |
| event_type | String(32) | Event type filter |
| enabled | Boolean | Whether webhook is active |
| created_at | UTCDateTime | Creation timestamp |

**Location:** `app/models.py:484-514`

The `secret` property is decrypted on access via `app/webhook_encryption.py`. Storage uses AES-256-GCM encryption.

```python
webhook_secret_encrypted = db.Column(db.LargeBinary(256), nullable=True)

@property
def secret(self) -> Optional[str]:
    """Get decrypted webhook secret."""
    if not self.webhook_secret_encrypted:
        return None
    from app.webhook_encryption import decrypt_webhook_secret
    try:
        return decrypt_webhook_secret(self.webhook_secret_encrypted.decode("utf-8"))
    except Exception:
        return None
```

---

## WebhookEvent Model

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| webhook_id | Integer | Foreign key to Webhook |
| event_type | String(32) | Event type |
| payload | JSON | Event payload |
| target_id | Integer | Target entity ID |
| target_type | String(32) | Target entity type |
| delivered | Boolean | Whether delivery succeeded |
| delivery_status | String(32) | Delivery status: `'delivered'`, `'partial_failure'`, `'failed'` |
| delivery_attempts | Integer | Number of delivery attempts |
| created_at | UTCDateTime | Creation timestamp |

**Location:** `app/models.py:524-542`

The `delivery_status` field tracks the outcome of webhook delivery attempts:
- `'delivered'` - All webhooks succeeded
- `'partial_failure'` - Some succeeded, some failed
- `'failed'` - All failed