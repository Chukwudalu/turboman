# Turboman — Production Readiness Assessment

_Assessed: 2026-05-07_

---

## Summary

**Not production-ready yet, but closer than most side projects get.** The core voice pipeline is genuinely solid. The gaps are in security, resilience, and operational tooling.

---

## What's Actually Good

- **Voice pipeline is well-built.** Deepgram → Claude → Cartesia streaming with barge-in detection, sentence-boundary flushing, and correct async handling throughout.
- **Twilio signature validation** exists on `/incoming-call` (production mode only).
- **Prompt injection detection** in `sanitize.py` — HTML stripping, pattern matching, length cap.
- **Prompt caching** correctly implemented — saves real money on every call after the first turn.
- **Asyncio safety** — Twilio SDK calls are wrapped in `run_in_executor` so they don't block the event loop.
- **Redis tenant caching** — prevents a DB hit on every incoming call.
- **Some tests exist** — unit tests for sanitize, sentence boundary, RAG; integration tests for orchestrator.
- **CI pipeline** runs on push/PR (unit tests only).
- **On-call dispatch chain** is thoughtfully designed — techs → managers → customer fallback, voice + SMS, callback handling.

---

## Blocking Issues — Fix Before Any Real Traffic

### ~~1. Twilio Webhook Endpoints Are Unauthenticated~~ ✓ Fixed

All webhook endpoints now use a shared `_verify_twilio` FastAPI dependency that validates the `X-Twilio-Signature` header on every request. The validator is instantiated once at startup (not per-request) and applied via `dependencies=[Depends(_verify_twilio)]` on all six endpoints. Only active in `production` env.

---

### ~~2. Multi-Tenant Data Isolation Gap~~ ✓ Fixed

`tenant_id` is now encoded in the JWT at login (sourced from `ADMIN_TENANT_ID` env var). A `_get_tenant_id` dependency extracts it from the token on every dashboard request. All 16 dashboard endpoints now receive `tenant_id` from the JWT — it is no longer accepted as a query param. Passing a different `tenant_id` in the URL has no effect.

---

### ~~3. SMS-Only Dispatch Has No Timeout~~ ✓ Fixed

When `notification_method == "sms"`, `_dispatch_to_contact` now schedules an `asyncio` background task that sleeps for `oncall_escalation_timeout_minutes` and calls `try_next_tech` if the dispatch is still in `"dispatching"` state. Exceptions in the task are logged rather than silently dropped. Note: does not survive server restarts (see issue 4).

---

### ~~4. Fallback SMS Doesn't Survive Server Restarts~~ ✓ Fixed

`_exhaust_dispatch` now writes to a `pending_notifications` table instead of sleeping. A background polling loop in `lifespan` checks every 30 seconds for due notifications and sends them. A server restart picks up any pending rows immediately on startup — the SMS is never lost.

---

## Significant Issues — Fix Before Launch

### ~~5. `asyncio.create_task` Exceptions Are Silently Dropped~~ ✓ Fixed

All `create_task` calls in `main.py` are now wrapped with `_guarded()`, which catches and logs any exception. Same pattern applied in `oncall_dispatch.py` for the SMS timeout task.

---

### ~~6. No Rate Limiting~~ ✓ Fixed

`slowapi` added with Redis-backed storage. Limits applied per IP:
- `POST /incoming-call` — 30/minute (triggers full AI + Deepgram + Anthropic + Cartesia)
- `POST /sms-incoming` — 60/minute
- `POST /auth/token` — 10/minute (brute force protection)

---

### ~~7. Tenant Cache Invalidation Is Flawed~~ ✓ Fixed

After the UPDATE, `update_settings` now fetches `phone` with a separate `SELECT` before deleting the cache key. PostgREST only returns updated columns so the old approach silently skipped the delete whenever `phone` wasn't in the update body.

---

### ~~8. `get_event_loop()` Deprecation~~ ✓ Fixed

Replaced in both `oncall_dispatch.py` and `notifications.py:12`.

---

### ~~9. No Phone Number Validation~~ ✓ Fixed

`E164Phone = Annotated[str, Field(pattern=r"^\+[1-9]\d{6,14}$")]` defined in `src/utils/validators.py`. Applied to `TenantCreate.phone`, `OncallTechCreate.phone`, `OncallTechUpdate.phone`, and both escalation phone fields in `TenantSettingsUpdate`. Pydantic returns a 422 with a clear error before any Twilio call is made.

---

## Operational Gaps — Needed Before Sustained Production Use

### ~~10. No Error Monitoring~~ ✓ Fixed

`sentry-sdk[fastapi]` added to requirements. `sentry_sdk.init()` runs at startup in `main.py` (before the app object is created so the FastAPI integration hooks in automatically). Only initialises when `SENTRY_DSN` is set — no-op in local dev without one. `traces_sample_rate=0.05` captures 5% of requests for performance monitoring without significant overhead. Environment tag is set from `settings.env` so issues are bucketed by production / staging / development.

---

### ~~11. No Pagination on Dashboard Data~~ ✓ Fixed

All four list endpoints (`/calls`, `/service-requests`, `/customers`, `/kb`) now return `{data, next_cursor}`. Frontend switched from `useSWR` to `useSWRInfinite` on all list pages with a "Load more" button. Date filtering still works across all loaded pages.

---

### ~~12. Auth Is Single-User, No Revocation~~ ✓ Fixed

Credentials moved to a `users` table (done in previous session). Access JWTs shortened to 15 minutes. Login now returns an opaque refresh token stored in a `refresh_tokens` table. `POST /auth/refresh` issues a new access JWT; `POST /auth/logout` marks the refresh token as revoked. The frontend auto-refreshes before expiry via the NextAuth `jwt` callback and force-signs-out on `RefreshAccessTokenError`. Stolen tokens expire in ≤15 min and can't be refreshed if revoked.

---

### ~~13. CI Only Runs Unit Tests~~ ✓ Fixed

24 new integration tests added across two files:

- `tests/integration/test_webhooks.py` — covers all 7 Twilio webhook endpoints (`/incoming-call`, `/oncall-call-start`, `/oncall-call-response`, `/oncall-call-eta`, `/oncall-call-status`, `/sms-incoming`, and the callback flow). Uses `httpx.AsyncClient` with mocked Redis/background tasks so no real services are needed.
- `tests/integration/test_oncall_dispatch.py` — covers `trigger_oncall_dispatch` and `try_next_tech` across all branching paths (no contacts, tech→manager escalation, exhausted→fallback, already-resolved no-ops).

Also fixed two pre-existing failures in `test_orchestrator.py` that broke silently under Python 3.13 (async iterator protocol and awaited `on_chunk` callbacks). Total suite: **49 tests, all passing**.

---

## Minor Issues

- ~~`logger.warn()` is deprecated — use `logger.warning()`~~ ✓ Fixed — `Logger` now supports both; production code already used `warning()` in several places that would have crashed at runtime.
- ~~When no tenant is found for a phone number in the gateway, the call silently hangs~~ ✓ Fixed — plays "We're unable to connect your call at this time" then closes cleanly.
- Dashboard has no loading skeletons — just "Loading…" text everywhere

---

## Status Table

| Area | Status |
|---|---|
| Voice pipeline correctness | Ready |
| On-call dispatch logic | Ready |
| Twilio webhook auth | **Not ready** |
| Multi-tenant data isolation | **Not ready for SaaS** |
| Error monitoring | Ready (Sentry) |
| Rate limiting | **Not ready** |
| Resilient background jobs | **Not ready** |
| Auth (admin) | Acceptable for single-tenant |
| Test coverage | Integration tests added (49 tests) |
| Pagination | Missing |

---

## Recommended Launch Threshold

### Must have before first customer

- [x] Twilio signature validation on all webhook endpoints
- [ ] Sentry error monitoring
- [ ] Rate limiting on webhook endpoints
- [ ] SMS dispatch timeout (background job)
- [ ] One full week of test calls with real phones

### Can ship after launch

- [ ] Cursor-based pagination
- [ ] Full JWT revocation
- [ ] Multi-user dashboard auth
- [ ] Persistent fallback delay (survive restarts)
- [ ] Billing system
