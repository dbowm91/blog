# RSS Feeds

## Endpoints

- `/atom` - Atom 1.0 feed
- `/rss` - RSS 2.0 feed
- `/json` - JSON Feed 1.1

---

## Caching

Feed responses are cached for performance:

- **Cache Duration:** 5 minutes
- **ETag Support:** Conditional GET with `If-None-Match` header
- **304 Response:** When cached response is still valid, returns `304 Not Modified`

**Implementation:** `app/routes/rss.py:108-110,192-194,243-245`

```python
response.headers["Cache-Control"] = "max-age=300"
response.headers["ETag"] = f'"{hash}"'
if request.if_none_match and request.if_none_match == response.headers.get("ETag"):
    return response, 304
```