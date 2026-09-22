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

## Local development setup (macOS / Linux)
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
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

Then run migrations, seed an admin, and start the server:

```bash
python manage.py migrate
python manage.py create_admin --email admin@example.com --password 'Admin12345!'
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
- `backend` — runs `migrate` then `runserver` on port **8000**, with `DB_HOST=db` and credentials from
  `.env`/compose defaults.

Compose variables can be overridden either in `.env` (e.g. `POSTGRES_PASSWORD=...`) or via the
`POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD` environment defaults.

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


## Tests

```bash
python manage.py test tests -v 2
```

- `test_domain.py` — entity validation & business rules.
- `test_use_cases.py` — use cases against in-memory fake repositories (no Django).
- `test_api.py` — full HTTP API via DRF `APIClient` (register/login/authz/CRUD/booking/health).
- `test_booking_race.py` — **PostgreSQL concurrency test** (needs a running Postgres; uses `TransactionTestCase`).

---

## Logging

- Every HTTP request writes a `Logs` row (type INFO/WARNING/ERROR by status code; stack traces captured
  for 5xx) and a Python log record — see console output and `logs/app.log`.
- Domain/application events (`event.created`, `booking.rejected`, `user.login`, ...) are emitted both to
  the log stream and persisted to the Logs table for auditability.
