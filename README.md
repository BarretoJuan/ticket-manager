# Ticket Manager
 **Django 6.1 + Django REST Framework 3.18 + PostgreSQL 18**,
---

## Architecture

```
backend/
├── domain/                     # pure business logic
│   ├── entities/               # Event, Booking, User, LogEntry, OutboundEmail, SatCancelado, SatHistory (dataclasses + validation)
│   ├── repositories/           # port interfaces (EventRepository, BookingRepository, SatRepository, ...)
│   ├── services/               # ports (password hashing, email, QR code generation, SAT data download)
│   ├── exceptions.py           # domain exception hierarchy (incl. SatSyncError / SatDownloadError / SatParseError)
│   └── utils.py
├── application/
│   ├── use_cases/              # Register/Login/Create/List/Update/Delete/Book/SatSync/SatListHistory...
│   ├── services/               # BookingNotifier (composes confirmation e-mails), SatSyncRunner (bg thread)
│   └── logging_utils.py
├── infrastructure/
│   ├── orm/                    # Django app "ticketing": models, auth backends, migrations (sat_cancelados, sat_history)
│   ├── repositories/           # Django implementations of the domain ports + mappers (incl. DjangoSatRepository)
│   ├── services/               # DjangoEmailService (SMTP), PillowQrCodeGenerator, HttpSatDataService (SAT scraper)
│   └── db.py
├── presentation/
│   ├── views/                  # thin controllers (APIView per resource, incl. SAT sync views)
│   ├── serializers/            # request/response DTOs
│   ├── di.py                   # composition root (wires use cases to infra)
│   ├── errors.py               # domain error → HTTP mapping
│   ├── permissions.py, middleware.py, spectacular_extension.py
│   └── urls.py
├── tests/                      # domain, use cases, API, booking race, SAT sync
├── manage.py, requirements.txt
├── Dockerfile, docker/postgres/Dockerfile
└── .env.example

frontend/                       # Vite 8 + React 19 + TypeScript + Tailwind CSS
├── src/                        # components/pages (App, main)
├── vite.config.ts              # /api -> backend dev proxy
├── prettier.config.js, eslint.config.js
└── Dockerfile, .dockerignore

docker-compose.yml              # single command: runs db + mailhog + backend + frontend
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

### SAT "Cancelados" sync (art. 69 CFF open data) — admin only

These endpoints manage the periodic import of SAT's published list of "Cancelados"
(tax-payers with cancelled fiscal status). The sync is **asynchronous**: the POST returns
immediately and the heavy work (scrape → stream-download → import ~185k rows) runs on a
background thread. It is fully isolated from the Events/Booking code.

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/sat/sync` | `POST` | Start a sync. `?force=true` bypasses the cooldown window (default 30 min). Returns `202` when started; `200` + `status=skipped` when the last successful sync is still inside the cooldown; `409` when another sync is already running. |
| `/api/v1/sat/sync/{history_id}` | `GET` | Poll the status of a run: `processing` / `completed` / `error`, plus stats (rows imported/omitted, processing time, file hash). |
| `/api/v1/sat/history` | `GET` | List the last processed files — **20 per page**, newest first, `count/next/previous/results` envelope. |

```bash
# start a sync (admins only)
curl -X POST http://localhost:8000/api/v1/sat/sync -H "Authorization: Bearer $TOKEN"
# => 202 {"history_id": "...", "status": "processing", "started_at": "...", "force": false}

# poll it
curl http://localhost:8000/api/v1/sat/sync/<history_id> -H "Authorization: Bearer $TOKEN"
# => {"id": "...", "status": "completed", "record_number": 185000, "omitted_number": 12, ...}
```

### Downloaded file format

The scraper finds the "Cancelados" link on the SAT page each run and downloads a single
CSV file (≈185k rows / ≈20 MB at the time of writing; encoded in UTF-8 when decodable,
otherwise latin-1) with thousands-separated, comma-quoted amounts:

```csv
RFC,RAZON SOCIAL,TIPO PERSONA,SUPUESTO,FECHA DE CANCELACION,MONTO ,FECHA DE PUBLICACION,ENTIDAD FEDERATIVA
AAA010101AAA,"EMPRESA UNO SA DE CV",M,CANCELADOS,28/05/2019,"1,390,273",20/08/2019,BAJA CALIFORNIA SUR
```

| CSV column | Format |
|---|---|
| `RFC` | 12/13-char tax-payer ID (`AAA010101AAA`, `XAXX010101000`…) |
| `RAZON SOCIAL` | entity/business name — may contain multiple spaces |
| `TIPO PERSONA` | `M` (empresa/legal) or `F` (persona física) |
| `SUPUESTO` | legal supposition under art. 69 CFF (e.g. `CANCELADOS POR INCOSTEABILIDAD`) |
| `FECHA DE CANCELACION` | cancellation date, `dd/mm/yyyy` |
| `MONTO` | amount of the cancelled operations, integer or decimal with `,` thousands separators (the header itself has a trailing space) |
| `FECHA DE PUBLICACION` | publication date, `dd/mm/yyyy` |
| `ENTIDAD FEDERATIVA` | state (e.g. `CIUDAD DE MEXICO`) |

### Mapping to the database

Each valid row becomes one `sat_cancelados` record:

| CSV column | `sat_cancelados` field | Type |
|---|---|---|
| `RFC` | `rfc` | `varchar(50)`, uppercased, indexed (not unique) |
| `RAZON SOCIAL` | `razon_social` | `text` |
| `TIPO PERSONA` | `tipo_persona` | `varchar(255)`, nullable |
| `SUPUESTO` | `supuesto` | `text` |
| `FECHA DE CANCELACION` | `fecha_de_cancelacion` | `date` |
| `MONTO` | `monto` | `numeric(20,2)` |
| `FECHA DE PUBLICACION` | `fecha_de_publicacion` | `date` |
| `ENTIDAD FEDERATIVA` | `entidad_federativa` | `varchar(255)`, nullable |
| — (computed) | `row_hash` | `varchar(64)`, sha256 of the canonicalized row, unique — drives de-duplication |
| — (bookkeeping) | `id`, `created_at`, `updated_at` | identity + timestamps |

Every run is recorded in `sat_history`: `id`, `started_at`, `completed_at`, which admin
triggered it (`user_id`), `status` (`processing`/`completed`/`error`), `file_hash` (sha256
of the whole file, used to short-circuit re-runs), `processing_time`, `record_number`
(rows inserted) and `omitted_number` (rows skipped — invalid or already stored).

Design notes:

- **Cooldown + dedupe**: after a successful download, new runs are skipped for
  `SAT_SYNC_COOLDOWN_MINUTES` (default 30) unless `?force=true`. A file already imported
  (identical sha256) short-circuits to a `completed` run with `record_number: 0` — nothing
  is re-imported. Rows are additionally de-duplicated by their full content hash: a row
  identical to one already stored is skipped and counted in `omitted_number`.
- **Download safety**: the CSV is streamed to a temp file (never fully in RAM) while its
  sha256 is computed, capped by `SAT_MAX_FILE_BYTES`; the download link is scraped from the
  SAT page each run (it may change over time). Fields/dates/amounts that don't parse are
  counted in `omitted_number` instead of failing the run; a structurally unrecognized file
  records an `error` run instead of crashing.
- **Concurrency**: a PostgreSQL advisory xact lock plus a `processing` history row guarantee
  a single concurrent run — safe across threads and multiple WSGI workers.
- **Data**: rows are stored into `sat_cancelados` de-duplicated by row content hash — the
  same RFC can appear in several *distinct* rows (a tax-payer can be cancelled more than
  once), and all of them are kept; only byte-identical rows are collapsed. Every run is
  recorded in `sat_history` with which admin triggered it.

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

## Docker setup — run the whole project

```bash
cp backend/.env.example backend/.env   # required by docker-compose (backend service mounts it)
docker compose up --build
```

- `db` — PostgreSQL 18 container, health-gated.
- `mailhog` — SMTP sink for booking confirmation e-mails (web UI at **http://localhost:8025**,
  SMTP on `mailhog:1025` inside the compose network, host port `1025`).
- `backend` — runs `migrate`, `seed`, then `runserver` on port **8000**, with `DB_HOST=db` and
  credentials from `.env`/compose defaults. Seeding is idempotent; disable it with
  `SEED_ENABLED=false`. Confirmation e-mails are sent through MailHog (override
  `EMAIL_HOST`/`EMAIL_PORT` in `.env` to route them to a real provider).
- `frontend` — Vite dev server with HMR on port **5173** (source-tree mount, as if you ran
  `npm run dev` locally). Browser calls to `/api/*` on `http://localhost:5173` are proxied to
  the backend service by the Vite dev server, so the API base URL is just `/api/v1` (no CORS
  involved). The proxy target comes from `VITE_BACKEND_PROXY` (defaults to
  `http://localhost:8000` for standalone `npm run dev` outside Docker).

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

## Email notifications

A successful booking triggers a **confirmation e-mail** to the buyer with:

- event name, code and date (UTC),
- the buyer's e-mail address and the number of tickets,
- a thank-you message,
- a **QR code** (PNG image) encoding the booking identifier (`str(booking.id)`).

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
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` | Django mail backend (set `locmem`/`console` for tests/debug) |
| `EMAIL_HOST` | *(empty)* | SMTP server; empty + SMTP backend ⇒ e-mails disabled |
| `EMAIL_PORT` | `25` | SMTP port (Docker overrides to `1025` for MailHog) |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | *(empty)* | SMTP credentials when the server requires auth |
| `EMAIL_USE_TLS` | `false` | Start TLS for the SMTP connection |
| `DEFAULT_FROM_EMAIL` | `no-reply@ticket-manager.local` | Sender address for confirmation e-mails |
| `SAT_SYNC_COOLDOWN_MINUTES` | `30` | Minutes after a successful sync during which new runs are skipped (bypass with `?force=true`) |
| `SAT_PAGE_URL` | `https://www.sat.gob.mx/minisitio/DatosAbiertos/contribuyentes_publicados.html` | SAT page scraped for the "Cancelados" link |
| `SAT_LINK_TEXT` | `Cancelados` | Anchor text used to find the download link on the SAT page |
| `SAT_HTTP_TIMEOUT_SECONDS` | `60` | Timeout for the SAT page/CSV HTTP calls |
| `SAT_MAX_FILE_BYTES` | `536870912` (512 MB) | Safety cap on the downloaded CSV size |
| `SAT_SYNC_BATCH_SIZE` | `5000` | Rows per import batch (memory stays flat)


## Tests

```bash
python manage.py test tests -v 2
```

- `test_domain.py` — entity validation & business rules.
- `test_use_cases.py` — use cases against in-memory fake repositories (no Django).
- `test_api.py` — full HTTP API via DRF `APIClient` (register/login/authz/CRUD/booking/health).
- `test_booking_race.py` — **PostgreSQL concurrency test** (needs a running Postgres; uses `TransactionTestCase`).
- `test_seed.py` — `seed` command: creates demo data, is idempotent, honours `SEED_ENABLED`/`SEED_BOOKINGS`.
- `test_sat_sync.py` — SAT use-case tests with fakes (cooldown, concurrency, CSV parsing, hash dedupe, error handling; no DB).
- `test_sat_api.py` — SAT endpoints against PostgreSQL with the downloader mocked (202 → status poll, cooldown/force, `409`, paginated history list).

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
