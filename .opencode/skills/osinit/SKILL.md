---
name: osinit
description: "OSINIT Dashboard - FastAPI backend with 24 intelligence sources, React/TypeScript frontend with 3D globe. Triggers: build, test, deploy, run, data source, panel, SSE, sweep, synthesis, authentication, rate limiting, cache, delta, VIX, SSRF, circuit breaker, routers, Granian."
metadata:
  requires: "python>=3.12, node>=20"
  homepage: "https://github.com/sugarwookie/osinit"
---

## Project Overview

OSINIT Dashboard is a full-stack OSINT dashboard that aggregates 24 intelligence feeds (21 external APIs + 1 derived + 2 static) onto a 3D globe. The frontend is React + TypeScript + Vite with Zustand state management. The backend is FastAPI with SSE for real-time updates.

**Status as of 2026-04-30:** WAVE 1 fully completed. WAVE 2-5 have mixed completion with many deferred items due to scope/size.

**Architecture:**
- **Backend**: FastAPI + Python 3.12+, async I/O throughout, SSE for real-time updates, Granian ASGI server
- **Frontend**: React + TypeScript + Vite, Zustand state, globe.gl for 3D visualization
- **Data Flow**: 24 sources → orchestrator → synthesizer → dashboard data → SSE → frontend

## Current Status

- **Backend tests**: 1004 tests (75%+ coverage)
- **Frontend tests**: 350+ tests (0 skipped)
- **Key source coverage**: maritime 89%, nuclear 100%, satellites 97%, submarine_cables 97%
- **Documentation**: Diataxis-organized structure with tutorial/, how-to/, reference/, explanation/, runbooks/

### WAVE Status (Verified 2026-04-30)
- **WAVE 1**: COMPLETED (1.1-1.7 all fixed/implemented)
- **WAVE 2**: PARTIAL (2.1 partial, 2.3 completed; 2.2, 2.4, 2.5 deferred)
- **WAVE 3**: PARTIAL (3.3 completed; 3.1, 3.2, 3.4 deferred)
- **WAVE 4**: PARTIAL (4.2, 4.4 completed; 4.1, 4.3 deferred)
- **WAVE 5**: PARTIAL (5.3 completed; 5.1 deferred, 5.2 partial)

## Key Commands

```bash
# Backend development (uses Granian)
cd backend && source .venv/bin/activate && granian --host 0.0.0.0 --port 8000 --interface asgi app.main:app

# Backend tests (1004 passed, 75%+ coverage)
cd backend && .venv/bin/python -m pytest tests/ -x -q --cov=app

# Backend linting
cd backend && .venv/bin/python -m ruff check app/

# Frontend development
cd frontend && npm run dev

# Makefile targets (from repo root)
make test-backend
make lint
```

## Core Patterns

### Adding New API Keys
1. Add field to `Settings` in `config.py` (e.g., `adsbx_api_key: str | None = None`)
2. Add env var to `.env.example` with comment
3. Access via `settings.<key_name>` — never `os.environ.get()` directly
4. Add validation check in `validate_source_keys()`
5. Update tests to mock `app.sources.<module>.settings`

### Settings Mocking (Python)
```python
# Correct
with patch("app.sources.military_air.settings") as mock_settings:
    mock_settings.adsbx_api_key = "test_key"
    result = await source.fetch()

# Wrong
with patch.dict(os.environ, {"ADSBX_API_KEY": "test_key"}):  # Won't work
```

### SSE Authentication
The frontend reads `VITE_API_KEY` from environment and passes `X-API-Key` header:
```typescript
const apiKey = import.meta.env.VITE_API_KEY;
headers: { "X-API-Key": apiKey }
```

### Admin Endpoint Authorization
Use `require_admin_key()` FastAPI dependency for admin-only endpoints:
```python
from fastapi import Depends
from app.auth import require_admin_key

@router.post("/api/admin/reload-static-data")
async def reload_static_data(request: Request, _admin_key: str = Depends(require_admin_key)):
    # Admin-only logic here
```

The dependency returns the validated API key string, or raises HTTPException 401/403 on failure. When no auth is configured (`settings.api_keys` and `settings.admin_api_keys` both empty), it allows through.

### SSE Message Types
`'connected'`, `'sweep_start'`, `'update'`, `'sweep_error'`, `'heartbeat'`, `'llm_stream'`, `'server_shutdown'`

### HTTP Client Caching with WeakValueDictionary and TTL
HTTP clients cached to prevent memory leaks:
```python
_shared_clients: weakref.WeakValueDictionary[str, httpx.AsyncClient] = weakref.WeakValueDictionary()
_client_timestamps: weakref.WeakValueDictionary[str, float] = weakref.WeakValueDictionary()
_CLIENT_TTL_SECONDS = 300  # 5 minutes

async def _get_client(self) -> httpx.AsyncClient:
    key = self._client_key
    now = time.monotonic()
    if key in _shared_clients and not _shared_clients[key].is_closed:
        if key in _client_timestamps and now - _client_timestamps[key] <= _CLIENT_TTL_SECONDS:
            return _shared_clients[key]
        await _shared_clients[key].aclose()  # Stale - close and recreate
    client = httpx.AsyncClient(...)
    _shared_clients[key] = client
    _client_timestamps[key] = now
    return client
```

### Centralized Constants (constants.py)
Magic numbers extracted to `backend/app/constants.py`:
```python
# Time conversions
SECONDS_PER_HOUR = 3600
DAY_SECONDS = 86400  # 24 * 3600

# Security & rate limiting
RATE_LIMIT_WINDOW_SECONDS = 3600
SECURITY_EVENT_RATE_LIMIT = 3600

# Key & session management
REVOKED_KEY_TTL_SECONDS = 2592000  # 30 days
MAX_BODY_SIZE_BYTES = 1_048_576  # 1 MB

# HTTP Client TTL
CLIENT_TTL_SECONDS = 300  # 5 minutes
HTTP_MAX_CONNECTIONS = 100
HTTP_MAX_KEEPALIVE_CONNECTIONS = 20
```

### Per-Key Locking Pattern
For fine-grained locking (cache, circuit breaker):
```python
_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
_locks_lock = asyncio.Lock()

async with _locks_lock:
    if key not in _locks:
        _locks[key] = asyncio.Lock()
lock = _locks[key]
async with lock:
    # operation
```

### Lazy Initialization for Event Loop-Dependent Objects
```python
_source_semaphore: asyncio.Semaphore | None = None

def _get_source_semaphore() -> asyncio.Semaphore:
    global _source_semaphore
    if _source_semaphore is None:
        _source_semaphore = asyncio.Semaphore(settings.max_source_concurrency)
    return _source_semaphore
```

### Async Lock Pattern (auth.py)
```python
_AUTH_FAIL_LOCK: asyncio.Lock | None = None

def _get_auth_lock() -> asyncio.Lock:
    global _AUTH_FAIL_LOCK
    if _AUTH_FAIL_LOCK is None:
        _AUTH_FAIL_LOCK = asyncio.Lock()
    return _AUTH_FAIL_LOCK
```

### Per-IP Auth Locking with WeakValueDictionary
```python
_auth_ip_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

def _get_ip_lock(client_ip: str) -> asyncio.Lock:
    global _auth_ip_locks
    lock = _auth_ip_locks.get(client_ip)
    if lock is None:
        lock = asyncio.Lock()
        _auth_ip_locks[client_ip] = lock
    return lock
```

### Coordinate Validation
Python `0.0` is falsy - use `if value is not None:` for coordinate checks:
```python
lat = body.get("Latitude")
lng = body.get("Longitude")
if lat is not None and lng is not None:
    vessels.append({"lat": lat, "lng": lng})
```

### Cache Cleanup (peek before pop)
```python
while self._heap:
    exp, key = self._heap[0]  # Peek without popping
    if exp > now:
        break
    heapq.heappop(self._heap)  # Only pop if actually expired
```

### Atomic File Writes
```python
def _atomic_write(filepath: str, content: str) -> None:
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=f"{filename}.tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)  # Atomic on POSIX
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
```

### Debounced Save Pattern
```python
_save_timer: asyncio.TimerHandle | None = None

def _schedule_save() -> None:
    global _save_timer
    if _save_timer is not None:
        _save_timer.cancel()
    _save_timer = asyncio.get_running_loop().call_later(
        5.0, lambda: asyncio.create_task(self._save()).add_done_callback(_log_save_error)
    )
```

### asyncio.wait with Timeout
```python
done, pending = await asyncio.wait(
    tasks,
    return_when=asyncio.ALL_COMPLETED,
    timeout=120.0  # Safety timeout
)
for t in pending:
    t.cancel()
```

### GPS Jamming Pipelining
```python
opensky_task = asyncio.create_task(run_single_source(opensky_source, correlation_id))
other_tasks = [asyncio.create_task(run_single_source(s, correlation_id)) for s in independent]

opensky_result = await opensky_task

if (opensky_result and
    opensky_result.status == SourceStatus.OK and
    opensky_result.data and
    opensky_result.data.get("states")):
    gps_jamming.set_flight_data(opensky_result.data["states"])
    gps_task = asyncio.create_task(run_single_source(gps_jamming, correlation_id))

pending = other_tasks + ([gps_task] if gps_task else [])
done, _ = await asyncio.wait(pending, return_when=asyncio.ALL_COMPLETED)
```

## Security

### Path Traversal Prevention
Always validate file paths against a base directory:
```python
from pathlib import Path

def validate_file_path(path: Path, base_dir: Path) -> Path:
    resolved = path.resolve()
    base = base_dir.resolve()
    if not resolved.is_relative_to(base):
        raise ValueError(f"Path {path} is outside base directory {base_dir}")
    return resolved
```

### XFF Spoofing Protection
```python
if settings.strict_forwarded_for and settings.allowed_proxy_ips:
    client_ip = ips[-1] if ips else (request.client.host if request.client else "unknown")
else:
    client_ip = ips[0] if ips else (request.client.host if request.client else "unknown")
```

### Log Format String Safety
```python
# Correct
logger.info("[Sweep] %s: circuit OPEN", source.name)

# Wrong - f-string interpolation
logger.info(f"[Sweep] {source.name}: circuit OPEN")
```

### LLM Prompt Injection Prevention
```python
from app.llm.base import sanitize_for_prompt, wrap_user_input

# Sanitize and wrap user input for LLM prompts
# Note: wrap_user_input() now called automatically in answer_nl_query()
safe_input = wrap_user_input(user_text)  # Includes sanitize_for_prompt() internally
```

**Defense layers (all enabled by default):**
1. `SYSTEM_PROMPT_PREFIX` - Instructs LLM to ignore embedded instructions
2. `sanitize_for_prompt()` - Normalizes unicode, removes control chars, escapes `{}`, truncates
3. `wrap_user_input()` - Wraps input in `<user_input>` XML tags
4. Injection pattern detection - Logs warnings when patterns like "ignore previous instructions" detected

### SSRF Protection Defense-in-Depth
Uses `PinnedDNSTransport` to prevent DNS rebinding attacks:
```python
from app.utils.ssrf_safe_transport import create_ssrf_safe_client

# Create SSRF-safe HTTP client with pinned DNS resolution
client = await create_ssrf_safe_client()
```

### Security Event Rate Limiting
Prevents log flooding with 1000 events/hour per type.

### HMAC Rate Limit Key
```python
def _get_rate_limit_key(request: Request) -> str:
    client_ip = get_remote_address(request)
    api_key = request.headers.get("x-api-key")
    if api_key:
        hmac_secret = settings.api_keys_raw
        if hmac_secret:
            key_hash = hmac.new(hmac_secret.encode(), api_key.encode(), 'sha256').hexdigest()[:32]
            return f"{client_ip}:{key_hash}"
    return client_ip
```

### Production Fail-Fast
Server refuses to start if `ENVIRONMENT=production` and no `API_KEYS` configured:
```python
if os.getenv("ENVIRONMENT") == "production" and not settings.api_keys:
    raise SystemExit("CRITICAL: No API_KEYS configured for production environment")
```

### Proxy XFF Validation
`trust_forwarded_for` requires `allowed_proxy_ips` unless `UNSAFE_PROXY_BYPASS=true`:
```python
# In config.py model_validator(mode="after")
if self.trust_forwarded_for and not self.unsafe_proxy_bypass and not self.allowed_proxy_ips_raw:
    raise ValueError("trust_forwarded_for=True requires ALLOWED_PROXY_IPS...")
```

## Performance

### SSE Broadcast Batching
Prevents event loop starvation when serving many concurrent clients:
```python
# SSE_BROADCAST_BATCH_SIZE (default 100) processes clients in chunks
# Yield between batches: await asyncio.sleep(0) prevents starvation
# SSE queues have maxsize for backpressure
# QueueFull exceptions handled gracefully
```

### Blocking I/O in Async Context
```python
# TLE text processing
lines = await asyncio.to_thread(lambda: text.strip().split("\n"))

# CSV parsing
reader = await asyncio.to_thread(lambda: list(csv.DictReader(io.StringIO(text))))
```

### LLM Cache LRU with OrderedDict
```python
_semantic_cache: OrderedDict[str, tuple[str, float]] = OrderedDict()

async def _semantic_cache_get(fp: str, ttl: int) -> str | None:
    entry = _semantic_cache.get(fp)
    if entry is not None:
        _semantic_cache.move_to_end(fp)  # LRU promotion
        cached_text, cached_time = entry
        if time.time() - cached_time < ttl:
            return cached_text
        _semantic_cache.pop(fp)
    return None
```

### DNS Caching for URL Validation
TTL-based DNS cache reduces overhead:
```python
from app.config import resolve_hostname_cached

# Cache DNS resolution for 5 minutes
ip = await resolve_hostname_cached("api.example.com")
```

### Globe View Mode Cleanup
```typescript
if (viewMode === 'flat') {
    if (globeRef.current && globeRef.current._destructor) {
        globeRef.current._destructor();
    }
    globeRef.current = null;
    return <FlatMap />;
}
```

### FlatMap D3 Optimization
```typescript
const prevPointsRef = useRef(data?.globe_points);
const prevArcsRef = useRef(data?.globe_arcs);

useEffect(() => {
  if (prevPointsRef.current !== data?.globe_points ||
      prevArcsRef.current !== data?.globe_arcs) {
    prevPointsRef.current = data?.globe_points;
    prevArcsRef.current = data?.globe_arcs;
    // D3 update logic
  }
}, [data, showLayer, lowPerfMode, searchQuery, openDetail]);
```

### O(n²) Bounded Complexity
Some algorithms are intentionally O(n²) when n is bounded and small:
```python
# O(n²) inter-zone arcs - max 20 zones = 190 comparisons
# This is acceptable because:
# 1. Zone count hard-capped at 20
# 2. Each comparison is trivial (coordinates + arithmetic)
# 3. R-tree overhead > savings at this scale
for i, z1 in enumerate(active_zones):
    for z2 in active_zones[i + 1:]:  # O(n²) but bounded
        # simple arc creation
```

## Testing

### Source Data Validation
```python
# TLE checksum validation
def _validate_tle_checksum(line: str) -> bool:
    if len(line) != 69 or line[0] not in ('1', '2'):
        return False
    checksum = sum(int(c) if c.isdigit() else ord(c) - 55 for c in line[:68])
    return (checksum % 7) == int(line[68])

# CSV column validation
def _validate_csv_row(row: dict, required_cols: list[str]) -> bool:
    return all(col in row for col in required_cols)
```

### Source Response Structure Validation
```python
try:
    raw = await self.get_json(url, params=params)
except Exception as e:
    logger.warning("Source error", error=_sanitize(str(e)))
    return {"data": [], "error": _sanitize(str(e))}

if not isinstance(raw, dict) or "data" not in raw:
    logger.warning("Source: unexpected response structure")
    return {"data": [], "error": "invalid_response"}
```

### GlobeView Testing (jsdom)
```typescript
vi.mock('globe.gl', () => {
  const makeGlobe = () => {
    const instance: Record<string, unknown> = {
      // ... all chainable methods ...
      pointOfView: vi.fn(() => instance),
      _destructor: vi.fn(),
    };
    return instance;
  };
  const mockGlobe = vi.fn(() => makeGlobe());
  return { default: mockGlobe };
});
vi.stubGlobal('ResizeObserver', MockResizeObserver);
```

### Immer Proxy Revocation in Zustand Persist
When using `persistPartial()` with Immer proxies, the state is revoked after `produce()` finishes. Always deep-clone before JSON.stringify:
```typescript
// In persistPartial (store.ts) - check with !== undefined first
const stateToPersist = {
  previousValues: toPersist.previousValues !== undefined
    ? JSON.parse(JSON.stringify(toPersist.previousValues))
    : s.previousValues,
};

// In setData - clone before passing to persistPartial
persistPartial({ previousValues: JSON.parse(JSON.stringify(draft.previousValues)) });
```

## Common Issues

### `asyncio.Lock.acquire()` Always Returns `None`
Use `if lock.locked(): return` to check lock state, not `if not await lock.acquire()`.

### Circuit Breaker `_get()` Is Async
All callers must `await` it: `allow_request()`, `record_success()`, `record_failure()`, `get_state()`, `_load()`.

### `vite preview` Does Not Proxy
Use `npm run dev` for local API proxying.

### Edit Tool Pitfalls
`oldString` must match **exactly** including all lines between anchor points. Verify after edits.

### Verify Implementations Before Claiming Done
Always verify that code changes actually implement what the plan claims.

## Security Utilities

### SecureString for Memory-Zeroing
```python
from app.utils.security import SecureString, clearSensitiveDict

# Use context manager for automatic cleanup
with SecureString(api_key) as key:
    # Use key.value
    do_something(key.value)
# Memory automatically zeroed on exit

# Manually clear
key = SecureString(sensitive_token)
value = key.value
key.clear()  # Overwrites memory with zeros

# Clear sensitive values in dictionaries
safe_data = clearSensitiveDict({"api_key": "sk-xxx", "data": "public"})
# Result: {"api_key": "", "data": "public"}
```

### API Key Memory Protection
Python's memory management doesn't guarantee immediate cleanup. Use SecureString for defense-in-depth:
- API keys wrapped in SecureString are stored in ctypes arrays
- clear() overwrites memory at the C level
- Thread-safe via threading.Lock

## Data Sources (24 Total)

| Source | File | Auth |
|--------|------|------|
| OpenSky | sources/opensky.py | Optional |
| Military Aircraft | sources/military_air.py | API key |
| Satellites | sources/satellites.py | None |
| FIRMS (fires) | sources/firms.py | API key |
| Maritime | sources/maritime.py | API key |
| ACLED | sources/acled.py | Email |
| UCDP | sources/ucdp.py | API token |
| FRED | sources/fred.py | API key |
| GDELT | sources/gdelt.py | None |
| GPS Jamming | sources/gps_jamming.py | Derived |
| Earthquakes | sources/earthquakes.py | None |
| Weather | sources/weather.py | None |
| Space Weather | sources/space_weather.py | None |
| CISA KEV | sources/cisa_kev.py | None |
| Exchange Rates | sources/exchange_rates.py | None |
| EIA | sources/eia.py | API key |
| DONKI | sources/donki.py | API key |
| Safecast | sources/safecast.py | None |
| WAQI | sources/waqi.py | Token |
| Polymarket | sources/polymarket.py | None |
| Abuse.ch | sources/abuse_ch.py | None |
| Sanctions | sources/sanctions.py | None |
| Nuclear | sources/nuclear.py | Static |
| Submarine Cables | sources/submarine_cables.py | Static |

## UI Patterns

### Right-Click Context Menu
For context menus on canvas elements like the globe:
```typescript
const [contextMenu, setContextMenu] = useState<{x: number; y: number; lat: number; lng: number; point?: unknown; type?: string} | null>(null);

useEffect(() => {
  const handleContextMenu = (e: MouseEvent) => {
    e.preventDefault();
    const lat = calculateLatFromY(e.clientY);
    const lng = calculateLngFromX(e.clientX);
    const point = data?.globe_points?.find(p =>
      p.lat && p.lng &&
      Math.abs(p.lat - lat) < 2 &&
      Math.abs(p.lng - lng) < 2
    );
    setContextMenu({ x: e.clientX, y: e.clientY, lat, lng, point, pointType: point?.type });
  };
  container.addEventListener('contextmenu', handleContextMenu);
  return () => container.removeEventListener('contextmenu', handleContextMenu);
}, []);

useEffect(() => {
  if (!contextMenu) return;
  const handleClick = () => setContextMenu(null);
  window.addEventListener('click', handleClick);
  return () => window.removeEventListener('click', handleClick);
}, [contextMenu]);

// Render context menu
{contextMenu && <ContextMenu x={contextMenu.x} y={contextMenu.y} items={getMenuItems(contextMenu)} onClose={() => setContextMenu(null)} />}
```

### Draggable Overlay
For draggable elements like legends that persist position:
```typescript
const [position, setPosition] = useState<{bottom: number; left: number}>({bottom: 16, left: 220});
const [isDragging, setIsDragging] = useState(false);
const dragStartRef = useRef<{x: number; y: number; bottom: number; left: number} | null>(null);

const handleMouseDown = (e: React.MouseEvent) => {
  e.preventDefault();
  setIsDragging(true);
  dragStartRef.current = { x: e.clientX, y: e.clientY, ...position };
};

useEffect(() => {
  if (!isDragging || !dragStartRef.current) return;
  const handleMouseMove = (e: MouseEvent) => {
    const dx = e.clientX - dragStartRef.current.x;
    const dy = dragStartRef.current.y - e.clientY;
    setPosition({
      bottom: Math.max(0, dragStartRef.current.bottom + dy),
      left: Math.max(0, dragStartRef.current.left + dx),
    });
  };
  const handleMouseUp = () => {
    setIsDragging(false);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(position));
  };
  if (isDragging) {
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
  }
  return () => {
    window.removeEventListener('mousemove', handleMouseMove);
    window.removeEventListener('mouseup', handleMouseUp);
  };
}, [isDragging, position]);
```

### Bulk Selection
For selecting multiple items with checkboxes:
```typescript
const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

const toggleSelection = (key: string) => {
  setSelectedItems(prev => {
    const next = new Set(prev);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    return next;
  });
};

const selectAll = () => {
  setSelectedItems(new Set(items.map(i => i.key)));
};

const selectNone = () => {
  setSelectedItems(new Set());
};
```

### TypeScript Temporal Dead Zone Fix
When using `useCallback` hooks that reference each other, define them in order of dependency (callees before callers):
```typescript
// Define these first since handleKeyDown depends on them
const handleSubmit = useCallback(() => { ... }, [...]);
const selectSuggestion = useCallback((suggestion) => { ... }, [...]);

// Define this last since it calls the above
const handleKeyDown = useCallback((e) => {
  // Can safely call handleSubmit() and selectSuggestion() here
}, [..., handleSubmit, selectSuggestion]);
```

### Globe Tooltip Copy Button
For adding copy buttons to globe tooltips:
```typescript
// In globe.gl pointLabel callback
.pointLabel(
  (d: GlobePoint) => {
    const head = DOMPurify.sanitize(d.pop_head ?? '', { RETURN_TRUSTED_TYPE: false });
    const text = DOMPurify.sanitize(d.pop_text ?? '', { RETURN_TRUSTED_TYPE: false });
    const meta = DOMPurify.sanitize(d.pop_meta ?? '', { RETURN_TRUSTED_TYPE: false });
    const copyText = `${head}\n${text}\n${meta}`;
    return `<div class="globe-tooltip"><b>${head}</b><br/>${text}<br/><span class="meta">${meta}</span><button class="tooltip-copy-btn" data-copy="${encodeURIComponent(copyText)}" title="Copy info">⧉</button></div>`;
  },
)

// In useEffect for click handling
useEffect(() => {
  const container = containerRef.current;
  if (!container) return;

  const handleClick = async (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (!target.classList.contains('tooltip-copy-btn')) return;

    e.preventDefault();
    e.stopPropagation();

    const copyData = target.getAttribute('data-copy');
    if (!copyData) return;

    try {
      const text = decodeURIComponent(copyData);
      await navigator.clipboard.writeText(text);
      target.textContent = '✓';
      target.classList.add('copied');
      setTimeout(() => {
        target.textContent = '⧉';
        target.classList.remove('copied');
      }, 1500);
    } catch {
      // Clipboard API failed
    }
  };

  container.addEventListener('click', handleClick);
  return () => container.removeEventListener('click', handleClick);
}, []);
```

## Verified Codebase Facts (2026-04-30)

These facts were verified against the actual codebase. Future agents can trust these without re-verifying.

### Frontend Architecture (2026-04-30)
- **GlobeView.tsx**: 365 lines (utility functions extracted to `globeConstants.ts`, `globeUtils.ts`) - selectors NOT consolidated yet
- **ThreatPanel.tsx**: 238 lines (4 tabs extracted to separate files: SignalsTab, CompareTab, EventsTab, CountriesTab)
- **useSSE.ts**: 110 lines (split into useSSEConnection.ts, useSSEOfflineDetector.ts)
- **useSSE.ts** includes visibility-aware reconnection (reconnects if lastUpdate > 30s when tab becomes visible)
- **Type guards**: `isEarthquakeEvent`, `isUcdpEvent`, `isWeatherAlert` added in `types/index.ts`
- **NuclearDataLoader**: `asyncio.Lock` added for thread-safe cache access

### Modular Router Structure
- `main.py` reduced from ~1140 lines to ~604 lines
- All routes organized into `backend/app/routers/` by domain:
  - `routers/health.py`: `/api/health`, `/metrics`
  - `routers/data.py`: `/api/data`, `/api/sources/health`
  - `routers/llm.py`: `/llm/query`, `/llm/stream`
  - `routers/sse.py`: `/events`
  - `routers/sweep.py`: `/api/sweep`
  - `routers/admin.py`: `/api/admin/*`
  - `routers/history.py`: `/api/history`, `/api/history/{ts}`
- Shared state in `state.py`, shared limiter in `limiter.py`

### Synthesizer Architecture
- **19 module files** in `backend/app/synthesizer/` (excluding `__init__.py`, `base.py`, `main.py`)
- **23 total synthesizer calls**: 6 run in parallel via ThreadPoolExecutor, 17 run sequentially
- `synthesize()` is **synchronous** (NOT asyncio.gather)
- Thread pool default: 6 workers (configurable via `SYNTH_THREAD_WORKERS` env var)
- **Safe synthesis:** `_safe_synthesize()` helper reduces try/except boilerplate
- **Error collection:** `synthesizer_errors` tracks failures and returns them in DashboardData

### SSE Infrastructure
- Real-time updates via Server-Sent Events
- SSE broadcast batching with `SSE_BROADCAST_BATCH_SIZE` (default 100)
- Yield between batches (`await asyncio.sleep(0)`) prevents event loop starvation
- Backpressure via queue `maxsize`
- Periodic cleanup and broadcast logic properly use `async with state.sse_clients_lock:`
- **Visibility-aware reconnection:** `useSSE.ts` reconnects if `lastUpdate > 30s` when tab becomes visible

### Store enableMapSet
- `_seenSignalKeys: Set<string>` and `_signalExpirationTimes: Map<string, number>` are used inside `produce()` in store.ts
- `enableMapSet()` is properly called in production code at store.ts line 3-6

### Delta Computation Async Handling
- `DeltaEngine.compute()` is an **async method** in `backend/app/delta.py`
- Called correctly at main.py line 930: `dashboard.delta = await state.delta_engine.compute(dashboard)`

### Source Standardization (Completed WAVE 1.1)
- BaseSource has `_fallback()` method returning `{"stale": True}`
- `waqi.py` and `donki.py` return `{"error": "api_key_missing", "stale": True, ...}` instead of raising ValueError
- Tests updated to expect fallback dict instead of exception

### WAVE 1 Implementation Details

#### Signal Key Persistence (WAVE 1.6)
- `_seenSignalKeys` persisted to 'osinit-signal-keys' localStorage key
- `loadPersistedState()` function reads localStorage once at store initialization
- Last 50 signal keys preserved across page refreshes

#### Sweep Timeout Configuration (WAVE 1.7)
- `sweep_timeout: float = 120.0` in config.py (env: `SWEEP_TIMEOUT`)
- `orchestrator.py` uses `settings.sweep_timeout` instead of hardcoded 120.0

#### Admin Key Debug Bypass (WAVE 1.3)
- `debug_admin_bypass: bool = False` in Settings (env: `DEBUG_ADMIN_BYPASS`)
- `is_admin_key()` returns `settings.debug_admin_bypass` when no auth configured

#### Visibility-Aware SSE (WAVE 2.3)
- `useSSE.ts` has visibilitychange listener that triggers reconnect if lastUpdate > 30s

### WAVE 3 Implementation Details

#### /api/sources/health (WAVE 3.3)
- `CircuitBreaker.get_detailed_states()` returns state, consecutive_failures, opened_at per source
- `/api/sources/health` in data.py returns detailed states from circuit breaker

### WAVE 4 Implementation Details

#### Error Categorization (WAVE 4.2)
- `_ERROR_CATEGORIES` in orchestrator.py includes: dns_failure, ssl_error, connection_refused
- Patterns match lowercase error messages for flexible categorization

#### Equality Checking (WAVE 4.4)
- `pointsEqual()` in globeUtils.ts uses hybrid approach: reference check (`===`) first, then sample comparison, then full loop
- This provides O(1) fast-path for same reference, O(n/2) for sample check, then O(n) full check

### WAVE 5 Implementation Details

#### Redis TLS Hardening (WAVE 5.3)
- `_get_redis_client()` supports:
  - `REDIS_SSL_MIN_VERSION` (e.g., "2" for TLSv1.2)
  - `REDIS_SSL_CHECK_HOSTNAME` (true/false)
  - `REDIS_CLIENT_CERT` and `REDIS_CLIENT_KEY` for mTLS

## Visual Regression Testing

Playwright-based screenshot comparison with pixelmatch:
- **Location**: `frontend/tests/e2e/visualRegression.spec.ts`
- **Comparison**: pixelmatch with 0.1% threshold, max 100 diff pixels
- **Directories**: `visualRegression/baseline/`, `visualRegression/screenshots/`, `visualRegression/diff/`
- **Scripts**: 
  - `npm run test:visual` - Run visual regression tests
  - `npm run test:visual:update` - Update baselines (UPDATE_BASELINE=true)
  - `npm run test:visual:open` - Run with Playwright UI

## Test Coverage

- **Backend**: 1004 tests, 75.23% coverage
- **Key source coverage**: maritime 89%, nuclear 100%, satellites 97%, submarine_cables 97%
- **Frontend**: 350+ tests (0 skipped), 14 e2e test files

## Deferred Items

These items are documented but require significant work:
- **SEC8**: Frontend API key exposure - requires BFF proxy setup (documentation in `docs/runbooks/SEC8_BFF_PROXY.md`)
- **ARC7**: Split schemas.py into domain files (1104 lines, deferred for future refactoring)
- **2.2 Zustand Storage Abstraction**: StateStorage interface and storage.ts utility
- **2.4 TypeScript Errors**: 50+ errors in build
- **2.5 Mobile-First Design**: Missing 1024px breakpoint and useIsTablet hook
- **3.1 Lifespan Extraction**: app/services/ with LoggingService, StateService, HttpService, BackgroundService
- **3.2 Schema Decoupling**: models/base.py with SourceStatus, Severity, SignalCategory
- **3.4 OpenTelemetry**: app/tracing.py with OTLP instrumentation
- **4.1 GlobeView Selector**: useShallow consolidation (19→1 selector)
- **4.3 Orchestrator Concurrency**: asyncio.as_completed for independent tasks
- **5.1 Keyboard Shortcut System**: useKeyboard.ts hook, remove duplicate normalizeKey in App.tsx and ShortcutSettings.tsx
- **5.2 Search Autocomplete**: SearchBar.tsx needs to use SearchAutocomplete.tsx component