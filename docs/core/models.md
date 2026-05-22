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