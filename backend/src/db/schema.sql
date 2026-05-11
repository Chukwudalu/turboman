-- Turboman canonical schema — run this in the Supabase SQL editor.
-- Uses CREATE TABLE IF NOT EXISTS / ADD COLUMN IF NOT EXISTS so it is safe
-- to re-run against a database that already has some tables.

CREATE EXTENSION IF NOT EXISTS vector;

-- ── Tenants ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tenants (
  id                                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name                              text        NOT NULL,
  trade_type                        text,                           -- 'hvac' | 'plumbing' | 'electrical'
  phone                             text,                           -- E.164 Twilio number
  fsa_type                          text        DEFAULT '',
  cartesia_voice_id                 text        DEFAULT '',
  business_hours_start              text        DEFAULT '09:00',
  business_hours_end                text        DEFAULT '17:00',
  business_timezone                 text        DEFAULT 'America/New_York',
  oncall_escalation_timeout_minutes int         DEFAULT 10,
  oncall_notification_method        text        DEFAULT 'both',     -- 'voice' | 'sms' | 'both'
  created_at                        timestamptz DEFAULT now()
);

-- ── Customers ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS customers (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid        REFERENCES tenants(id),
  phone      text        NOT NULL,
  name       text,
  email      text,
  created_at timestamptz DEFAULT now(),
  UNIQUE(tenant_id, phone)
);

-- ── Calls ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calls (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   uuid        REFERENCES tenants(id),
  customer_id uuid        REFERENCES customers(id),
  twilio_sid  text        UNIQUE,
  status      text        DEFAULT 'active',   -- active | completed | escalated | failed
  duration_s  int,
  transcript  text,
  started_at  timestamptz DEFAULT now(),
  ended_at    timestamptz
);

-- ── Call actions (audit log) ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS call_actions (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  call_id    uuid        REFERENCES calls(id),
  type       text        NOT NULL,   -- book_job | reschedule_job | get_job_status | save_customer_info | get_quote | escalate_to_human
  payload    jsonb,
  result     jsonb,
  success    boolean,
  created_at timestamptz DEFAULT now()
);

-- ── Service requests ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS service_requests (
  id                    uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             uuid        REFERENCES tenants(id),
  customer_id           uuid        REFERENCES customers(id),
  call_id               uuid        REFERENCES calls(id),
  service_type          text        NOT NULL,
  status                text        DEFAULT 'pending',   -- pending | reschedule_requested | scheduled | in_progress | completed | cancelled
  scheduled_date        text,
  scheduled_time        text,
  address               text,
  notes                 text,
  channel               text        DEFAULT 'voice',     -- voice | sms | email | web
  is_emergency          boolean     DEFAULT false,
  is_after_hours        boolean     DEFAULT false,
  next_morning_priority boolean     DEFAULT false,
  created_at            timestamptz DEFAULT now(),
  updated_at            timestamptz DEFAULT now()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS service_requests_updated_at ON service_requests;
CREATE TRIGGER service_requests_updated_at
  BEFORE UPDATE ON service_requests
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── On-call technicians ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS oncall_technicians (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid        REFERENCES tenants(id),
  name       text        NOT NULL,
  phone      text        NOT NULL,
  email      text,
  priority   int         NOT NULL DEFAULT 1,
  role       text        NOT NULL DEFAULT 'tech',   -- 'tech' | 'manager'
  active     boolean     NOT NULL DEFAULT true,
  created_at timestamptz DEFAULT now()
);

-- ── On-call dispatches ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS oncall_dispatches (
  id                      uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id               uuid        REFERENCES tenants(id),
  service_request_id      uuid        REFERENCES service_requests(id),
  status                  text        NOT NULL DEFAULT 'dispatching',   -- dispatching | acknowledged | rejected | failed
  eta_text                text,
  acknowledged_by_tech_id uuid        REFERENCES oncall_technicians(id),
  resolved_at             timestamptz,
  created_at              timestamptz DEFAULT now()
);

-- ── Knowledge base (per-tenant RAG) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kb_chunks (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  uuid        REFERENCES tenants(id),
  content    text        NOT NULL,
  embedding  vector(1536),
  metadata   jsonb,
  created_at timestamptz DEFAULT now()
);

DROP FUNCTION IF EXISTS match_kb_chunks(vector, uuid, integer);
CREATE FUNCTION match_kb_chunks(
  query_embedding vector(1536),
  tenant          uuid,
  match_count     int DEFAULT 5
)
RETURNS TABLE (id uuid, content text, similarity float)
LANGUAGE sql STABLE AS $$
  SELECT id, content, 1 - (embedding <=> query_embedding) AS similarity
  FROM   kb_chunks
  WHERE  tenant_id = tenant
  ORDER  BY embedding <=> query_embedding
  LIMIT  match_count;
$$;

-- ── Migration: add missing columns to existing tables ─────────────────────────
-- Safe to run even if the tables/columns already exist.

ALTER TABLE service_requests ADD COLUMN IF NOT EXISTS call_id               uuid    REFERENCES calls(id);
ALTER TABLE service_requests ADD COLUMN IF NOT EXISTS is_emergency          boolean DEFAULT false;
ALTER TABLE service_requests ADD COLUMN IF NOT EXISTS is_after_hours        boolean DEFAULT false;
ALTER TABLE service_requests ADD COLUMN IF NOT EXISTS next_morning_priority boolean DEFAULT false;

ALTER TABLE customers ADD COLUMN IF NOT EXISTS email text;

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS fsa_type                          text DEFAULT '';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS cartesia_voice_id                 text DEFAULT '';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_start              text DEFAULT '09:00';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_hours_end                text DEFAULT '17:00';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS business_timezone                 text DEFAULT 'America/New_York';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS oncall_escalation_timeout_minutes int  DEFAULT 10;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS oncall_notification_method        text DEFAULT 'both';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS oncall_fallback_delay_minutes     int  DEFAULT 5;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS escalation_phone                  text DEFAULT '';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS escalation_phone_after_hours      text DEFAULT '';

-- ── Pending notifications (durable fallback SMS queue) ───────────────────────
CREATE TABLE IF NOT EXISTS pending_notifications (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  phone       text        NOT NULL,
  message     text        NOT NULL,
  send_at     timestamptz NOT NULL,
  sent        boolean     NOT NULL DEFAULT false,
  dispatch_id uuid        REFERENCES oncall_dispatches(id),
  created_at  timestamptz DEFAULT now()
);

-- ── Users (dashboard admin accounts, one or more per tenant) ──────────────────
CREATE TABLE IF NOT EXISTS users (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email         text        NOT NULL UNIQUE,
  password_hash text        NOT NULL,
  tenant_id     uuid        NOT NULL REFERENCES tenants(id),
  active        boolean     NOT NULL DEFAULT true,
  created_at    timestamptz DEFAULT now()
);

-- ── Durable SMS dispatch timeouts ────────────────────────────────────────────
-- Written when an SMS-only dispatch is sent; polled every 30 s to escalate
-- techs who haven't replied. Survives server restarts unlike asyncio.create_task.
CREATE TABLE IF NOT EXISTS dispatch_sms_timeouts (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  dispatch_id uuid        NOT NULL REFERENCES oncall_dispatches(id),
  tech_id     uuid        NOT NULL REFERENCES oncall_technicians(id),
  escalate_at timestamptz NOT NULL,
  processed   boolean     NOT NULL DEFAULT false,
  created_at  timestamptz DEFAULT now()
);

-- ── Refresh tokens (JWT revocation) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
  id         uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  token      text        NOT NULL UNIQUE,
  user_email text        NOT NULL,
  tenant_id  uuid        NOT NULL REFERENCES tenants(id),
  expires_at timestamptz NOT NULL,
  revoked    boolean     NOT NULL DEFAULT false,
  created_at timestamptz DEFAULT now()
);
