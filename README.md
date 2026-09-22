# Ticket Manager — Backend
 **Django 6.1 + Django REST Framework 3.18 + PostgreSQL 18**,
---

## Architecture

```
backend/
├── domain/                     # pure business logic
│   ├── entities/               # Event, Booking, User, LogEntry (dataclasses + validation)
│   ├── repositories/           # port interfaces (EventRepository, BookingRepository, ...)
│   ├── services/               # password hashing port
│   ├── exceptions.py           # domain exception hierarchy
│   └── utils.py
├── application/
│   ├── use_cases/              # Register/Login/Create/List/Update/Delete/Book...
│   └── logging_utils.py
├── infrastructure/
│   ├── orm/                    # Django app "ticketing": models, auth backends, migrations
│   ├── repositories/           # Django implementations of the domain ports + mappers
│   └── db.py
├── presentation/
│   ├── views/                  # thin controllers (APIView per resource)
│   ├── serializers/            # request/response DTOs
│   ├── di.py                   # composition root (wires use cases to infra)
│   ├── errors.py               # domain error → HTTP mapping
│   ├── permissions.py, middleware.py, spectacular_extension.py
│   └── urls.py
├── tests/                      # domain, use cases, API, booking race
├── manage.py, requirements.txt
├── Dockerfile, docker-compose.yml, docker/postgres/Dockerfile
└── .env.example
```

## API
Base URL: `http://localhost:8000/api/v1`

### Events: `GET /api/v1/events`

Lists upcoming (non-deleted) events ordered by date, **20 per page**.

Query params (all optional, combinable):

| Param | Values | Description |
|---|---|---|
| `page` | integer ≥ 1 | Page number (default 1) |
| `code` | e.g. `EVT-2026-RO` | Exact event code |
| `name` | string | Case-insensitive substring match on the event name |
| `date_from` | `YYYY-MM-DD` | Events on/after this day (UTC, inclusive) |
| `date_to` | `YYYY-MM-DD` | Events on/before this day (UTC, inclusive) |
| `availability` | `available` \| `sold_out` | `available` = tickets remain, `sold_out` = none left |

Example: `GET /api/v1/events?page=2&name=tech&date_from=2026-01-01&date_to=2026-12-31&availability=available`

Paginated response envelope (`next`/`previous` repeat the current filters):

```json
{
  "count": 25,
  "next": "http://localhost:8000/api/v1/events?page=2",
  "previous": null,
  "results": [ { "id": "...", "name": "Tech Conference", "date": "2027-06-15T09:00:00Z", "...": "..." } ]
}
```

## Local development setup (macOS / Linux)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # optional: black + flake8
cp .env.example .env            # then edit values if needed
```

### PostgreSQL
Any PostgreSQL 18 instance works. Example with a user-owned cluster:

```bash
# (one time) create the role + database
psql -h localhost -p 5432 -U postgres -c \
  "CREATE ROLE ticket_user LOGIN PASSWORD 'ticket_password' CREATEDB;"
psql -h localhost -p 5432 -U postgres -c "CREATE DATABASE ticket_manager OWNER ticket_user;"
```

Then run migrations, seed the database, and start the server:

```bash
python manage.py migrate
python manage.py seed   # demo data: admin, users, events, bookings (idempotent)
python manage.py runserver 0.0.0.0:8000
```

Verify:

```bash
curl http://localhost:8000/api/v1/health          # {"status":"ok","database":"ok"}
```

Swagger UI: http://localhost:8000/api/v1/docs/

---

## Docker setup

```bash
cd backend
cp .env.example .env    # required by docker-compose (backend service mounts it)
docker compose up --build
```

- `db` — PostgreSQL 18 container, health-gated.
- `backend` — runs `migrate`, `seed`, then `runserver` on port **8000**, with `DB_HOST=db` and
  credentials from `.env`/compose defaults. Seeding is idempotent; disable it with
  `SEED_ENABLED=false`.

Compose variables can be overridden either in `.env` (e.g. `POSTGRES_PASSWORD=...`) or via the
`POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD` environment defaults.

---

## Seeding

`python manage.py seed` fills the database with demo data and is safe to re-run (existing
rows are left untouched):

- **1 admin** — `admin@example.com` / `Admin12345!` (reuse this to create an admin manually
  without demo data: `python manage.py create_admin --email ... --password ...`).
- **2 demo users** — `alice@example.com`, `bob@example.com` (password `Demo12345!`).
- **4 upcoming events** — valid `EVT-<year>-XX` codes, future dates, varied capacity/price.
- **A few bookings** — created only for events seeded in the same run, using the real
  booking use case (respects capacity and the 1–5 tickets rule).

All data goes through the application use cases, so domain validation, password hashing, and
audit logging apply. Configuration is via `SEED_*` env vars (see below).

---

## Environment variables (`.env`)

| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `change-me` (set a real one) | Django secret |
| `DEBUG` | `True` | Django debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hosts (`*` in Docker) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | `ticket_manager / ticket_user / ticket_password / localhost / 5432` | PostgreSQL connection |
| `JWT_ACCESS_TOKEN_MINUTES` | `60` | Access token lifetime |
| `JWT_REFRESH_TOKEN_DAYS` | `1` | Refresh token lifetime |
| `BOOK_THROTTLE_RATE` | `10/min` | Rate limit for `POST /events/{id}/book` (per user) |
| `LOGIN_THROTTLE_RATE` | `10/min` | Rate limit for `POST /login` (per client IP) |
| `REGISTER_THROTTLE_RATE` | `10/min` | Rate limit for `POST /register` (per client IP) |
| `SEED_ENABLED` | `true` | Seed demo data when `manage.py seed` runs (automatic on `docker compose up`) |
| `SEED_ADMIN_EMAIL` / `SEED_ADMIN_PASSWORD` | `admin@example.com` / `Admin12345!` | Admin account created by seeding |
| `SEED_DEMO_USERS` | `alice@example.com,bob@example.com` | Demo user accounts (comma-separated) |
| `SEED_BOOKINGS` | `true` | Create a few bookings on freshly seeded events |


## Tests

```bash
python manage.py test tests -v 2
```

- `test_domain.py` — entity validation & business rules.
- `test_use_cases.py` — use cases against in-memory fake repositories (no Django).
- `test_api.py` — full HTTP API via DRF `APIClient` (register/login/authz/CRUD/booking/health).
- `test_booking_race.py` — **PostgreSQL concurrency test** (needs a running Postgres; uses `TransactionTestCase`).
- `test_seed.py` — `seed` command: creates demo data, is idempotent, honours `SEED_ENABLED`/`SEED_BOOKINGS`.

---

## Code style & linting

The codebase is formatted with [Black](https://black.readthedocs.io/) and linted with
[flake8](https://flake8.pycqa.org/). Config lives in `pyproject.toml` (Black: 88-char line
limit, Python 3.14) and `.flake8` (flake8: same line limit, ignores `E203`/`W503`). Both
must run clean from the `backend/` directory:

```bash
pip install -r requirements-dev.txt  # once, if not already installed

black .        # format the codebase
flake8         # lint

# CI-style checks
black --check .
flake8
```

---

## Logging

- Every HTTP request writes a `Logs` row (type INFO/WARNING/ERROR by status code; stack traces captured
  for 5xx) and a Python log record — see console output and `logs/app.log`.
- Domain/application events (`event.created`, `booking.rejected`, `user.login`, ...) are emitted both to
  the log stream and persisted to the Logs table for auditability.
