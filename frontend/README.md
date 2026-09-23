# Ticket Manager — Frontend

React 19 + TypeScript (strict) + Vite 8 + Tailwind CSS 4 SPA for the Ticket Manager
backend (Django/DRF, see the [root README](../README.md)).

## Quick start

The backend must be running on `localhost:8000` (see the root README). Then:

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 — /api/* is proxied to the backend
```

Production-ish local build:

```bash
npm run lint          # ESLint
npm run format:check  # Prettier (CI-style)
npm run build         # tsc -b + vite build
```

Demo accounts (seeded by `python manage.py seed`): `admin@example.com` /
`Admin12345!` (ADMIN) and `alice@example.com` / `bob@example.com` / `Demo12345!`
(USER). Registration always creates a USER account.

## Routes

| Route        | Access | Purpose                             |
| ------------ | ------ | ----------------------------------- |
| `/`          | USER   | Event catalog + booking             |
| `/login`     | public | Sign in / register                  |
| `/admin`     | ADMIN  | Event CRUD + filters                |
| `/admin/sat` | ADMIN  | SAT "Cancelados" sync (art. 69 CFF) |

Routing is `react-router-dom` v7. Unauthenticated visits to protected routes
redirect to `/login`; role mismatches (e.g. USER on `/admin`) redirect to `/`.

## Structure & conventions

```
src/
├── components/     # feature slices: booking/, events/, sat/, layout/ (+ shared ui/)
├── context/        # AuthProvider, ToastProvider (+ typed context files)
├── hooks/          # useAuth, useBooking, useEvents, useSatSync, useToast
├── pages/          # one component per route
├── services/       # thin API modules — the ONLY place that calls fetch
├── types/          # shared domain/API types
└── utils/          # cn(), format helpers, JWT decode
```

- **Layering**: components, hooks, pages and contexts never call `fetch`
  directly; they go through `services/`, which wraps every request in
  `apiClient`. Only `services/apiClient.ts` knows the `/api/v1` base URL,
  the `Authorization: Bearer` header and DRF error payloads.
- **Session**: JWT pair lives in `localStorage["ticket-manager.session"]`.
  `apiClient` keeps a module-level token with `setAuthToken()` so timing of the
  React tree never drops the header; every `401` dispatches a global
  `ticket-manager:unauthorized` event handled by `AuthProvider` (logout + redirect).
- **Toasts**: `ToastProvider` + `useToast` (stable API — safe to put `toast` in
  effect dependency arrays). Success/info toasts render with `role="status"`,
  error toasts with `role="alert"`.
- **Brand palette** (Tailwind theme tokens: `primary`, `royal`, `navy`, …):
  `#00CBAA`, `#1A1D62`, `#00A3A6`, `#1D3D8F`, `#0F1424`, `#FFFFFF`, `#F4F6F9`,
  `#667085`.
- **Responsive**: stacked event cards on small screens, tables from `sm:` up;
  no horizontal overflow on a 375 px viewport.
- **Client validation mirrors the backend**: event code `^EVT-\d{4}-[A-Z]{2}$`
  (auto-uppercased), name 5–100 chars, strictly future date, capacity ≥ 1,
  price ≥ 0.01 (≤ 2 decimals), ticket quantity integer 1–5. Booking shows the
  confirmed buyer email in the dialog. Dates are UTC ISO strings rendered in the
  browser's local timezone; `ticket_price` is a decimal string.
- **No full-page reloads**: create/edit/delete, booking and SAT start all run
  in-place with optimistic UI + API confirmation.

## E2E smoke tests

Standalone Playwright scripts (Electron via the harness + system Chrome) live
outside this repo (`tm-e2e/`): `smoke-main.mjs` (auth, CRUD, catalog, booking,
role guards, mobile) and `smoke-sat.mjs` (SAT sync lifecycle incl. the 409
concurrency branch and the completion summary card). Both must end with
`ALL … FLOWS PASSED` and zero console/page errors.
