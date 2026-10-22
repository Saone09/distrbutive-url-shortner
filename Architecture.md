# Architecture Documentation
## Distributed URL Shortener & Event Tracking System
---
## 1. High-Level Architecture
The system follows a **layered monolith** architecture in its local development form,
with a clear separation path to a distributed microservice deployment.
```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│                  Browser  ·  API Client  ·  CLI                 │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP
┌──────────────────────────────▼──────────────────────────────────┐
│                      Flask Application                          │
│                                                                 │
│   ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐  │
│   │  main.py    │  │  urls.py    │  │   analytics.py       │  │
│   │  Blueprint  │  │  Blueprint  │  │   Blueprint          │  │
│   │  HTML pages │  │  POST/GET   │  │   GET stats/charts   │  │
│   └─────────────┘  │  DELETE     │  └──────────────────────┘  │
│                    └─────────────┘                              │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │                   redirect.py Blueprint                  │  │
│   │                   GET /<short_code>                      │  │
│   └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│   ┌─────────────────────────┬────────────────────────────────┐  │
│   │   url_service.py        │   analytics_service.py         │  │
│   │   · validate_url()      │   · get_overview_stats()       │  │
│   │   · create_short_url()  │   · get_clicks_over_time()     │  │
│   │   · record_click()      │   · get_url_analytics()        │  │
│   │   · delete_url()        │   · get_url_creation_trend()   │  │
│   └─────────────────────────┴────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────────┘
                               │ SQLAlchemy ORM
┌──────────────────────────────▼──────────────────────────────────┐
│                          Data Layer                             │
│                                                                 │
│         SQLite (dev)               PostgreSQL (prod)            │
│         urls.db                    DATABASE_URL env var         │
└─────────────────────────────────────────────────────────────────┘
```
---
## 2. Design Patterns Used
### Application Factory Pattern
`create_app(config_name)` in `app/__init__.py` creates a new Flask app with the
chosen configuration. This enables:
- One app instance per test (in-memory SQLite, isolated)
- Configuration switching via environment variable
- Deferred extension initialization
### Blueprint Pattern
Routes are split into four Blueprints, each focused on a single responsibility:
|
 Blueprint 
|
 Prefix 
|
 Responsibility 
|
|
-----------
|
--------
|
---------------
|
|
 main_bp 
|
 / 
|
 HTML page rendering 
|
|
 urls_bp 
|
 /api 
|
 URL CRUD REST API 
|
|
 analytics_bp 
|
 /api 
|
 Analytics REST API 
|
|
 redirect_bp 
|
 / 
|
 Short URL redirection 
|
### Service Layer Pattern
Business logic lives in `app/services/`, not in route handlers. Routes are kept
thin — they validate HTTP input, call a service, and format the response.
Services contain all SQL queries and domain rules.
### Repository-like Model Access
`db.session.execute(db.select(URL)...)` follows SQLAlchemy 2.x patterns.
All queries go through the ORM, preventing raw SQL injection risks.
---
## 3. URL Shortening Algorithm
```
Input: "https://example.com/very-long-path"
   │
   ▼
validate_url() → check scheme, netloc, length
   │
   ▼
generate_short_code() → secrets.choice(ALPHABET) × 7 chars
   │                      ALPHABET = [A-Za-z0-9] (62 chars)
   │                      62^7 ≈ 3.5 trillion combinations
   ▼
collision check → SELECT id FROM urls WHERE short_code = ?
   │  ← Retry up to 10 times if collision found (astronomically rare)
   ▼
INSERT INTO urls (short_code, original_url, ...)
   │
   ▼
Return URL object
```
**Why `secrets.choice` over `random`?**
`secrets` uses the OS CSPRNG (Cryptographically Secure Pseudo-Random Number
Generator), making short codes unpredictable and resistant to enumeration attacks.
`random.choice` is deterministic given a known seed and must never be used for
security-relevant tokens.
---
## 4. Click Recording
Each successful redirect triggers `record_click()`:
```python
# Atomic click counter increment — avoids race conditions
db.session.execute(
    db.update(URL).where(URL.id == url.id)
    .values(click_count=URL.click_count + 1)
)
```
Using a SQL `UPDATE ... SET click_count = click_count + 1` (instead of a
Python read-modify-write) ensures correctness under concurrent requests.
### Privacy Design
Raw IP addresses are **never** stored. Instead:
```
visitor_hash = SHA256(ip_address + ":" + str(date.today()))
```
The daily salt means:
1. The same visitor on different days produces different hashes.
2. The hash cannot be reversed to recover the original IP.
3. Approximate unique-visitor counts are possible within a single day.
---
## 5. Path to Distributed Architecture
The local single-process SQLite setup can be evolved in steps:
### Step 1 — PostgreSQL (multi-process safe)
```
DATABASE_URL=postgresql://user:pass@host/db
```
SQLAlchemy connection pooling handles concurrent connections.
No code changes needed.
### Step 2 — Redis Rate Limiting
```
REDIS_URL=redis://localhost:6379/0
```
Flask-Limiter uses Redis as a shared counter store, making rate limits
consistent across multiple Flask worker processes (Gunicorn).
### Step 3 — Docker Compose
`docker-compose up` starts three services:
- `web` — Gunicorn + Flask (can be scaled with `--scale web=4`)
- `db` — PostgreSQL
- `redis` — Redis
### Step 4 — Async Event Processing (proposed)
Click events could be decoupled using a queue:
```
Redirect Handler → Celery Task Queue (Redis/RabbitMQ) → Worker → DB
```
This would make redirects faster by eliminating the synchronous DB write
on the hot path, at the cost of eventual-consistency click counts.
---
## 6. Security Measures
|
 Threat 
|
 Mitigation 
|
|
--------
|
-----------
|
|
 SQL injection 
|
 SQLAlchemy ORM parameterized queries 
|
|
 XSS 
|
 Jinja2 auto-escaping, 
`escapeHtml()`
 in JS 
|
|
 URL injection (javascript:, ftp:) 
|
`validate_url()`
 scheme whitelist 
|
|
 Brute-force short code enumeration 
|
 CSPRNG + 7-char codes (62^7 space) 
|
|
 Abuse (bulk creation) 
|
 Flask-Limiter: 30/min, 200/hour per IP 
|
|
 Secret key exposure 
|
 Environment variables; never hardcoded 
|
|
 Stack trace leakage 
|
 Custom error handlers return JSON only 
|
|
 IDOR (exposing internal IDs) 
|
 Short code is the only public identifier 
|
