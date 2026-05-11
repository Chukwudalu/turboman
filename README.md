# Turboman 🔧

AI voice agent for trades companies (HVAC, plumbing, electrical).
Answers inbound calls, books jobs, reschedules, checks status — integrated with HousecallPro and Jobber.

## Stack

| Layer | Tool |
|---|---|
| Web framework | FastAPI + uvicorn |
| WebSockets | Built-in FastAPI / websockets |
| LLM | Claude Haiku (Anthropic) |
| STT | Deepgram nova-3 streaming |
| TTS | Cartesia sonic-english streaming |
| Database | Supabase (Postgres + pgvector) |
| Session cache | Upstash Redis |
| Telephony | Twilio Media Streams |
| Hosting | Railway |

## Quick start

```bash
# 1. Clone and set up venv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
cp .env.example .env
# Fill in your API keys

# 4. Set up Supabase
# Paste src/db/schema.sql into your Supabase SQL editor and run it

# 5. Run
python main.py
```

## Local dev with ngrok

```bash
# Terminal 1
python main.py

# Terminal 2
ngrok http 3000

# Then set your Twilio number's voice webhook to:
# https://<ngrok-url>/incoming-call
```

## Tests

```bash
pytest tests/unit -v
```

## Project structure

```
main.py               FastAPI app + WebSocket endpoint
src/
  gateway/            WebSocket call handler, streaming pipeline, barge-in
  orchestrator/       LLM turns, tool routing, system prompts
  actions/            book_job, reschedule, get_status, get_quote, escalate
  services/           Deepgram, Cartesia, HousecallPro, notifications
  channels/           Channel adapter (voice today, SMS/email later)
  db/                 Supabase client, schema, query helpers
  utils/              Logger (PII-safe), sanitizer, sentence boundary
  config/             Pydantic settings + validation
tests/
  unit/               Pure function tests — no network needed
  integration/        Pipeline tests with mocked services
  e2e/                Full call flow tests
```
