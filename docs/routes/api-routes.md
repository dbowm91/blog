# API Routes

## Posts API

See [posts.md](posts.md)

## Subscribers API

### List Subscribers

```
GET /api/subscribers
```

Requires `X-API-Key` header.

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 50 | Items per page (max 100) |
| `confirmed` | bool | - | Filter by confirmed status |

### Response

```json
{
  "subscribers": [
    {
      "id": 1,
      "email": "user@example.com",
      "confirmed": true,
      "created_at": "2026-05-01T08:00:00Z",
      "expires_at": "2026-06-01T08:00:00Z",
      "unsubscribed_at": null
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 50
}
```

### Create Subscriber

```
POST /api/subscribers
```

Requires `X-API-Key` header.

### Request Body

```json
{
  "email": "new@example.com"
}
```

### Response

Returns the created subscriber object with `201 Created`.