## Specs 

[How to run](README.md)

Further is spec.md

## 1. Middleware

### a. CORS + TrustedHostMiddleware

Add two Starlette built-ins directly in `main.py` before any routers are mounted.
- `CORSMiddleware` — controls which origins can make cross-origin requests. For local
  dev we allow all origins, but the allowed list is driven by env vars so it can be
  locked down in production without touching code.
- `TrustedHostMiddleware` — rejects requests whose `Host` header doesn't match a
  whitelist. Protects against HTTP Host header injection attacks.


### b. Custom Request Logging → Elasticsearch

Write a custom Starlette `BaseHTTPMiddleware` subclass that wraps every request.

Each log document contains:
- `timestamp` — ISO 8601 UTC
- `log_type` — INFO / DEBUG / ERROR
- `service` — hardcoded `"game-backlog-api"`
- `endpoint` — the matched route path e.g. `/api/games/{id}`
- `message` — `<IP>:<Port> - <Method> - <URL> - <Status Code> - <Processing Time ms>`
- `ip` — client IP
- `port` — client port
- `method` — GET / POST etc.
- `url` — full request URL
- `status_code` — response status
- `processing_time_ms` — float, time from request received to response sent

**Log level rules:**
- `ERROR` — status >= 500
- `DEBUG` — status >= 400 and < 500
- `INFO` — everything else (2xx, 3xx)

**Elasticsearch:**
- Index name: `game-backlog-logs`
- One document per request
- Ships asynchronously using `elasticsearch-py[async]` so it never blocks the response
- If ES is down the log is dropped silently — never let observability break the app


### c. Rate Limiting

Write a custom middleware using Redis directly. This gives full control
over the logic 

**Implementation:**
- Redis key pattern: `ratelimit:{ip}:minute`, `ratelimit:{ip}:hour`, `ratelimit:{ip}:write:hour`
- Uses Redis `INCR` + `EXPIRE` — atomic, fast, no race conditions
- Returns `429 Too Many Requests` with a `Retry-After` header indicating when the
  window resets
- IP extracted from `X-Forwarded-For` header if behind a proxy, falls back to
  `request.client.host`


### d. Profiling Middleware

Write a middleware that uses `pyinstrument` to profile each request's call stack and
measure latency.

**What it tracks:**
- Full call stack profile for each request
- Slow endpoint detection — any request over a configurable threshold (default 500ms)
  logs a WARNING with the full pyinstrument text output

**When it runs:**
Profiling is never on by default in any environment. It activates via:
- `PROFILING_ENABLED=true` in env 

**Why not always on:**
pyinstrument adds ~1-5ms overhead per request. At scale that compounds. The golden
rule: the profiler must never be the reason your app is slow in production.

**When the profiler itself is the bottleneck:**
- Switch from `pyinstrument` (statistical, 1ms sample interval) to no profiling
- Use `PROFILING_SAMPLE_RATE` env var to reduce sampling frequency
- Profile only a % of requests (e.g. 1 in 100) using random sampling
- Move to external APM (Datadog, Sentry Performance) which instruments at the
  infrastructure level with near-zero app overhead

**Common slow endpoint causes in this app:**
- N+1 queries — fetching backlog list then hitting DB once per game for platform info.
  Fix: use `joinedload()` or `selectinload()` in SQLAlchemy
- Missing DB indexes — filtering by `user_id` or `game_id` without an index.
  Fix: already handled in model definitions with `index=True`
- Synchronous calls inside async handlers — e.g. blocking bcrypt in the request path.
  Fix: run in `asyncio.get_event_loop().run_in_executor()` for CPU-bound work
- MinIO calls in the request path — image URL generation should be pre-computed,
  not fetched on every request

## 2. Background Tasks (Celery)

### a. Email Tasks

**Plan:**
Use Celery with Redis as the broker. Two tasks:
- `send_confirmation_email(user_id)` — triggered on register, sends a verification
  link with a signed token
- `send_password_reset_email(user_id)` — triggered on password reset request, sends
  a time-limited reset link

Both tasks are fire-and-forget from the API's perspective — the endpoint returns
immediately, Celery handles delivery in the background.

Email sending uses `smtplib` with a local Mailhog SMTP container for dev so no real
emails are sent during development.

### b. Image Compression Pipeline

**Plan:**
Screenshot upload endpoint (`POST /api/backlog/{entry_id}/screenshots`) accepts a
multipart file, saves it temporarily, fires a Celery task, returns 202 Accepted
immediately.

Celery task `process_screenshot(entry_id, tmp_path)`:
1. Open image with Pillow
2. Log original size: `"Before: 4.2MB"`
3. Compress — resize to max 1920px wide, convert to JPEG at quality=85
4. Log compressed size: `"After: 380KB (91% reduction)"`
5. Store compressed file in MinIO
6. Save the MinIO URL to the `Screenshot.file_url` column in Postgres
7. Delete the temp file


## Middleware Order in `main.py`

Order matters — middleware runs as a stack, outermost first:

```
1. TrustedHostMiddleware    — reject bad Host headers immediately
2. CORSMiddleware           — handle preflight, add headers
3. RateLimiterMiddleware    — reject abusive IPs before any work is done
4. LoggingMiddleware        — log everything that gets through
5. ProfilingMiddleware      — profile only if enabled
   ↓
   FastAPI routers
```
