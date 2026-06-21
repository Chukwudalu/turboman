import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis.asyncio as aioredis
import sentry_sdk
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import PlainTextResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from twilio.request_validator import RequestValidator
from twilio.rest import Client as TwilioRestClient

from src.admin.router import router as admin_router
from src.auth.router import router as auth_router
from src.utils.ratelimit import limiter
from src.config import settings

if settings.sentry_dsn:
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.env,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
from src.dashboard.router import router as dashboard_router
from src.db import db
from src.db.oncall import (
    acknowledge_dispatch,
    acknowledge_dispatch_for_tenant,
    cancel_dispatch_timeouts,
    get_dispatch,
    get_dispatch_context,
    get_tech_by_id,
)
from src.gateway import handle_call_websocket
from src.services.notifications import send_sms
from src.services.oncall_dispatch import try_next_tech
from src.utils.logger import logger


# ── Pending notification poller ────────────────────────────────────────────────

async def _guarded(coro) -> None:
    """Run a fire-and-forget coroutine and log any exception instead of swallowing it."""
    try:
        await coro
    except Exception as e:
        logger.error("Background task failed", error=str(e))


async def _poll_pending_notifications() -> None:
    """Every 30 s, send any fallback SMSes whose send_at time has passed."""
    while True:
        await asyncio.sleep(30)
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = await db.table("pending_notifications").select("*").eq("sent", False).lte("send_at", now).execute()
            for notif in result.data or []:
                # Claim the row immediately to prevent duplicate processing on multi-instance deploys
                claim = await db.table("pending_notifications").update({"sent": True}).eq("id", notif["id"]).eq("sent", False).execute()
                if not claim.data:
                    continue  # another instance already claimed it
                if notif.get("dispatch_id"):
                    dispatch = await get_dispatch(notif["dispatch_id"])
                    if dispatch and dispatch["status"] == "acknowledged":
                        logger.info("Dispatch acknowledged — skipping fallback SMS", dispatch_id=notif["dispatch_id"])
                        continue
                from_phone: str | None = None
                if notif.get("dispatch_id"):
                    ctx = await get_dispatch_context(notif["dispatch_id"])
                    from_phone = (ctx or {}).get("tenant_phone")
                await send_sms(notif["phone"], notif["message"], from_phone)
                logger.info("Fallback SMS sent", phone=notif["phone"])
        except Exception as e:
            logger.error("pending_notifications poll failed", error=str(e))


async def _poll_dispatch_sms_timeouts() -> None:
    """Every 30 s, escalate dispatches whose response window has expired (voice or SMS).

    Rows are written by _dispatch_to_contact and survive server restarts.
    """
    while True:
        await asyncio.sleep(30)
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = await (
                db.table("dispatch_sms_timeouts")
                .select("*")
                .eq("processed", False)
                .lte("escalate_at", now)
                .execute()
            )
            for row in result.data or []:
                try:
                    # Claim the row immediately to prevent duplicate processing on multi-instance deploys
                    claim = await db.table("dispatch_sms_timeouts").update({"processed": True}).eq("id", row["id"]).eq("processed", False).execute()
                    if not claim.data:
                        continue  # another instance already claimed it
                    dispatch = await get_dispatch(row["dispatch_id"])
                    if dispatch and dispatch["status"] == "dispatching":
                        logger.info(
                            "Dispatch timeout — tech did not respond, escalating",
                            dispatch_id=row["dispatch_id"],
                            tech_id=row["tech_id"],
                        )
                        await try_next_tech(row["dispatch_id"], row["tech_id"], declined=False)
                except Exception as e:
                    logger.error("dispatch_sms_timeout row failed", dispatch_id=row["dispatch_id"], error=str(e))
        except Exception as e:
            logger.error("dispatch_sms_timeouts poll failed", error=str(e))


# ── App lifespan — shared resources ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    poll_tasks = [
        asyncio.create_task(_poll_pending_notifications()),
        asyncio.create_task(_poll_dispatch_sms_timeouts()),
    ]
    logger.info("Turboman started", port=settings.port)
    yield
    for t in poll_tasks:
        t.cancel()
    await app.state.redis.aclose()
    logger.info("Turboman shut down")


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Admin-Secret"],
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Auth (login → JWT)
app.include_router(auth_router)

# Admin routes (tenant management, KB upload)
app.include_router(admin_router)

# Dashboard routes (calls, service requests, customers)
app.include_router(dashboard_router)


# ── Health check ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health(request: Request):
    checks: dict = {"status": "ok"}
    try:
        await request.app.state.redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        checks["status"] = "degraded"
    try:
        await db.table("tenants").select("id").limit(1).execute()
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
        checks["status"] = "degraded"
    return checks


# ── Twilio signature validation dependency ─────────────────────────────────────

_twilio_validator = RequestValidator(settings.twilio_auth_token)
_twilio_client = TwilioRestClient(settings.twilio_account_sid, settings.twilio_auth_token)


async def _verify_twilio(request: Request) -> None:
    """Reject any request that doesn't carry a valid Twilio signature."""
    if settings.env != "production":
        return
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    # Railway's proxy terminates TLS, so request.url reports scheme=http even though
    # Twilio signed the https URL it actually called. Rebuild using the public base URL.
    url = settings.base_url.rstrip("/") + request.url.path
    if request.url.query:
        url += f"?{request.url.query}"
    if not _twilio_validator.validate(url, dict(form), signature):
        logger.warning("Invalid Twilio signature rejected", url=url)
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Twilio inbound call webhook ────────────────────────────────────────────────

@app.post("/incoming-call", dependencies=[Depends(_verify_twilio)])
@limiter.limit("30/minute")
async def incoming_call(request: Request):
    form = await request.form()
    caller = form.get("From", "")
    called = form.get("To", "")
    logger.info("Incoming call received", caller=caller, called=called, all_params=dict(form))

    # Resolve which tenant owns the `called` number — use Redis cache to avoid an extra DB hit
    import json as _json
    redis = request.app.state.redis
    tenant_json = await redis.get(f"tenant:phone:{called}")
    called_tenant_id: str | None = None
    if tenant_json:
        called_tenant_id = _json.loads(tenant_json).get("id")
    else:
        t_row = await db.table("tenants").select("id").eq("phone", called).single().execute()
        called_tenant_id = (t_row.data or {}).get("id") if t_row.data else None

    # If the caller is a known on-call technician for this tenant, route to the callback
    # acknowledgment flow instead of the AI agent.
    if called_tenant_id:
        tech_result = await (
            db.table("oncall_technicians")
            .select("id")
            .eq("phone", caller)
            .eq("tenant_id", called_tenant_id)
            .eq("active", True)
            .limit(1)
            .execute()
        )
        if tech_result.data:
            tech_id = tech_result.data[0]["id"]
            base = settings.base_url.rstrip("/")
            return PlainTextResponse(
                '<?xml version="1.0" encoding="UTF-8"?>'
                "<Response>"
                f'<Redirect method="POST">{base}/oncall-callback?tech_id={tech_id}</Redirect>'
                "</Response>",
                media_type="text/xml",
            )

    if settings.base_url:
        ws_url = settings.base_url.rstrip("/").replace("https://", "wss://").replace("http://", "ws://") + "/call-stream"
    else:
        host = request.headers.get("host", "localhost")
        ws_url = f"wss://{host}/call-stream"

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{ws_url}">
      <Parameter name="from" value="{caller}" />
      <Parameter name="to" value="{called}" />
    </Stream>
  </Connect>
</Response>"""

    return PlainTextResponse(twiml, media_type="text/xml")


# ── Twilio Media Streams WebSocket ─────────────────────────────────────────────

@app.websocket("/call-stream")
async def call_stream(websocket: WebSocket):
    await handle_call_websocket(websocket, websocket.app.state.redis)


# ── On-call voice call TwiML flow ─────────────────────────────────────────────

def _xml(body: str) -> PlainTextResponse:
    return PlainTextResponse(f'<?xml version="1.0" encoding="UTF-8"?>\n<Response>{body}</Response>', media_type="application/xml")


@app.post("/oncall-call-start", dependencies=[Depends(_verify_twilio)])
async def oncall_call_start(dispatch_id: str = Query(...), tech_id: str = Query(...)):
    """TwiML: greet the tech and ask if they can attend."""
    ctx = await get_dispatch_context(dispatch_id)
    tech = await get_tech_by_id(tech_id)

    if not ctx or not tech or ctx["dispatch_status"] != "dispatching" or tech.get("tenant_id") != ctx["tenant_id"]:
        return _xml("<Say>This emergency has already been handled. Thank you.</Say><Hangup/>")

    await cancel_dispatch_timeouts(dispatch_id)

    base = settings.base_url.rstrip("/")
    name = tech["name"].split()[0]  # first name only
    company = ctx["company_name"]
    service = ctx["service_type"]
    location = f" at {ctx['address']}" if ctx["address"] else ""
    action = f"{base}/oncall-call-response?dispatch_id={dispatch_id}&amp;tech_id={tech_id}"

    is_emergency = ctx.get("is_emergency", True)
    call_type = "emergency" if is_emergency else "after-hours service"

    if tech.get("role") == "manager":
        greeting = (
            f"Hello {name}. This is an urgent escalation call from {company}. "
            f"We have been unable to reach any on-call technicians for an after-hours {call_type} request. "
            f"A customer requires {service}{location}. "
            f"If you accept, please notify the technician to contact the customer prior to attending to confirm the visit and service. "
            f"Can you coordinate a response tonight? Please say yes or no."
        )
    else:
        greeting = (
            f"Hello {name}. This is an {call_type} call from {company}. "
            f"A customer needs {service}{location}. "
            f"If you accept, please contact the customer prior to attending to confirm the visit and service. "
            f"Are you available to attend tonight? Please say yes or no."
        )

    return _xml(
        f'<Gather input="speech" action="{action}" timeout="8" speechTimeout="3" language="en-US">'
        f"<Say>{greeting}</Say>"
        f"</Gather>"
        f'<Redirect>{base}/oncall-call-response?dispatch_id={dispatch_id}&amp;tech_id={tech_id}&amp;no_input=1</Redirect>'
    )


@app.post("/oncall-callback", dependencies=[Depends(_verify_twilio)])
async def oncall_callback(tech_id: str = Query(...)):
    """
    Inbound call from a technician who missed the outbound oncall call.
    Checks whether the dispatch is still open or already handled by someone else.
    """
    tech = await get_tech_by_id(tech_id)
    if not tech:
        return _xml("<Say>We couldn't identify your account. Please contact your dispatcher directly.</Say><Hangup/>")

    name = tech["name"].split()[0]

    # Find the most recent dispatch for this tenant that is still active
    dispatch_result = await (
        db.table("oncall_dispatches")
        .select("id, status, service_requests(service_type, address, is_emergency)")
        .eq("tenant_id", tech["tenant_id"])
        .in_("status", ["dispatching", "acknowledged"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not dispatch_result.data:
        return _xml(
            f"<Say>Hi {name}, thanks for calling back. "
            "There are no active service requests right now. "
            "Have a good night.</Say><Hangup/>"
        )

    dispatch = dispatch_result.data[0]
    dispatch_id = dispatch["id"]

    await cancel_dispatch_timeouts(dispatch_id)

    if dispatch["status"] == "acknowledged":
        return _xml(
            f"<Say>Hi {name}, thanks for calling back. "
            "This job has already been accepted by another technician, so no action is needed from you. "
            "Have a good night.</Say><Hangup/>"
        )

    # Dispatch is still open — walk the tech through accepting it
    sr = dispatch.get("service_requests") or {}
    service = sr.get("service_type", "service request")
    location = f" at {sr['address']}" if sr.get("address") else ""
    is_emergency = bool(sr.get("is_emergency", True))
    call_type = "emergency" if is_emergency else "after-hours service"

    base = settings.base_url.rstrip("/")
    action = f"{base}/oncall-call-response?dispatch_id={dispatch_id}&amp;tech_id={tech_id}"

    return _xml(
        f'<Gather input="speech" action="{action}" timeout="8" speechTimeout="3" language="en-US">'
        f"<Say>Hi {name}, thanks for calling back. "
        f"We still have an open after-hours {call_type} request for {service}{location}. "
        f"If you accept, please contact the customer prior to attending to confirm the visit and service. "
        f"Are you available to attend tonight? Please say yes or no.</Say>"
        f"</Gather>"
        f'<Redirect method="POST">{base}/oncall-call-response?dispatch_id={dispatch_id}&amp;tech_id={tech_id}&amp;no_input=1</Redirect>'
    )


@app.post("/oncall-call-response", dependencies=[Depends(_verify_twilio)])
async def oncall_call_response(
    request: Request,
    dispatch_id: str = Query(...),
    tech_id: str = Query(...),
    no_input: str = Query(""),
):
    """TwiML: handle yes/no availability answer."""
    ctx = await get_dispatch_context(dispatch_id)
    tech = await get_tech_by_id(tech_id)
    if not ctx or not tech or tech.get("tenant_id") != ctx["tenant_id"]:
        return _xml("<Say>This request is no longer active. Thank you.</Say><Hangup/>")

    form = await request.form()
    speech = form.get("SpeechResult", "").lower()
    available = not no_input and any(w in speech for w in ("yes", "yeah", "sure", "yep", "okay", "ok", "affirmative", "can", "will"))

    base = settings.base_url.rstrip("/")

    if not available:
        asyncio.create_task(_guarded(try_next_tech(dispatch_id, tech_id, declined=True)))
        return _xml("<Say>Understood. We will contact the next available technician. Thank you.</Say><Hangup/>")

    action = f"{base}/oncall-call-eta?dispatch_id={dispatch_id}&amp;tech_id={tech_id}"
    return _xml(
        f'<Gather input="speech" action="{action}" timeout="10" speechTimeout="5" language="en-US">'
        "<Say>Excellent! What is your estimated time of arrival? For example, say 30 minutes or 2 hours.</Say>"
        "</Gather>"
        f'<Redirect>{base}/oncall-call-eta?dispatch_id={dispatch_id}&amp;tech_id={tech_id}&amp;no_input=1</Redirect>'
    )


@app.post("/oncall-call-eta", dependencies=[Depends(_verify_twilio)])
async def oncall_call_eta(
    request: Request,
    dispatch_id: str = Query(...),
    tech_id: str = Query(...),
    no_input: str = Query(""),
):
    """TwiML: capture ETA, acknowledge dispatch, notify customer."""
    ctx = await get_dispatch_context(dispatch_id)
    tech = await get_tech_by_id(tech_id)
    if not ctx or not tech or tech.get("tenant_id") != ctx["tenant_id"]:
        return _xml("<Say>This request is no longer active. Thank you.</Say><Hangup/>")

    form = await request.form()
    eta = form.get("SpeechResult", "").strip() if not no_input else ""

    await acknowledge_dispatch(dispatch_id, eta_text=eta or None, tech_id=tech_id)

    if ctx and ctx["customer_phone"]:
        service = ctx["service_type"]
        eta_str = f" They estimate arrival in {eta}." if eta else ""
        await send_sms(
            ctx["customer_phone"],
            f"Good news! A technician is on their way for your {service} emergency.{eta_str} They will contact you shortly. (Turboman)",
            ctx.get("tenant_phone"),
        )
        logger.info("Customer notified of oncall acknowledgment", dispatch_id=dispatch_id)

    return _xml(
        "<Say>Thank you. The customer has been notified. Please contact them directly for any further details. Stay safe out there.</Say>"
        "<Hangup/>"
    )


@app.post("/oncall-call-status", dependencies=[Depends(_verify_twilio)])
async def oncall_call_status(
    request: Request,
    dispatch_id: str = Query(...),
    tech_id: str = Query(...),
):
    """Twilio status callback — logs unanswered calls. The timeout poller handles escalation."""
    ctx = await get_dispatch_context(dispatch_id)
    tech = await get_tech_by_id(tech_id)
    if not ctx or not tech or tech.get("tenant_id") != ctx["tenant_id"]:
        return PlainTextResponse("OK")

    form = await request.form()
    call_status = form.get("CallStatus", "")

    if call_status in ("no-answer", "busy", "failed", "canceled"):
        logger.info("Oncall call unanswered — waiting for callback or timeout", status=call_status, dispatch_id=dispatch_id, tech_id=tech_id)

    return PlainTextResponse("", status_code=204)


# ── Twilio inbound SMS webhook (on-call acknowledgment) ───────────────────────

@app.post("/sms-incoming", dependencies=[Depends(_verify_twilio)])
@limiter.limit("60/minute")
async def sms_incoming(request: Request, From: str = Form("")):
    """
    Twilio sends a POST here when a text is received on our number.
    If the sender is a known on-call technician, acknowledge their tenant's
    active dispatch so the escalation chain stops.
    """
    result = await db.table("oncall_technicians").select("tenant_id").eq("phone", From).eq("active", True).limit(1).execute()
    if result.data:
        tenant_id = result.data[0]["tenant_id"]
        # Get dispatch before acknowledging so we can cancel the active call
        dispatch_result = await (
            db.table("oncall_dispatches")
            .select("id, active_call_sid")
            .eq("tenant_id", tenant_id)
            .eq("status", "dispatching")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        acknowledged = await acknowledge_dispatch_for_tenant(tenant_id)
        if acknowledged:
            logger.info("Oncall dispatch acknowledged via SMS", from_phone=From)
            # Notify the customer that a tech is on the way
            if dispatch_result.data:
                ctx = await get_dispatch_context(dispatch_result.data[0]["id"])
                if ctx and ctx.get("customer_phone"):
                    service = ctx["service_type"]
                    await send_sms(
                        ctx["customer_phone"],
                        f"Good news! A technician has accepted your {service} request and will contact you shortly. (Turboman)",
                        ctx.get("tenant_phone"),
                    )
            # Cancel the active voice call if one is ringing
            if dispatch_result.data and dispatch_result.data[0].get("active_call_sid"):
                call_sid = dispatch_result.data[0]["active_call_sid"]
                try:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: _twilio_client.calls(call_sid).update(status="completed"),
                    )
                    logger.info("Cancelled active oncall voice call after SMS accept", call_sid=call_sid)
                except Exception as e:
                    logger.warning("Could not cancel oncall voice call", call_sid=call_sid, error=str(e))

    return PlainTextResponse(
        '<?xml version="1.0"?><Response></Response>',
        media_type="application/xml",
    )


# ── Dev entrypoint ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=True)
