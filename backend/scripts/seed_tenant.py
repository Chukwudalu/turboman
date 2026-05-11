#!/usr/bin/env python3
"""
Seed a new tenant to both Supabase and the Redis cache.

Usage:
  python scripts/seed_tenant.py \
      --name "Smith's HVAC" \
      --phone "+15555551234" \
      --trade hvac
"""
import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis.asyncio as aioredis

from src.config import settings
from src.db import db

_CACHE_TTL = 86_400  # 24 hours


async def seed(args: argparse.Namespace) -> None:
    payload = {
        "name": args.name,
        "trade_type": args.trade,
        "phone": args.phone,
    }

    # ── Supabase ───────────────────────────────────────────────────────────────
    result = db.table("tenants").insert(payload).execute()
    tenant = result.data[0]
    print(f"[supabase] Created tenant {tenant['id']}  name={tenant['name']}")

    # ── Redis cache ────────────────────────────────────────────────────────────
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    cache_key = f"tenant:phone:{args.phone}"
    await r.set(cache_key, json.dumps(tenant), ex=_CACHE_TTL)
    await r.aclose()
    print(f"[redis]    Cached under {cache_key}  (TTL {_CACHE_TTL}s)")

    print(f"\nDone!")
    print(f"  Tenant ID : {tenant['id']}")
    print(f"  Phone     : {args.phone}")
    print(f"\nNext steps:")
    print(f"  1. Set NEXT_PUBLIC_TENANT_ID={tenant['id']} in frontend/.env.local")
    print(f"  2. Point your Twilio number's webhook to https://<your-domain>/incoming-call")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a Turboman tenant")
    parser.add_argument("--name", required=True, help="Company display name")
    parser.add_argument("--phone", required=True, help="Twilio E.164 number e.g. +15555551234")
    parser.add_argument("--trade", default="hvac", choices=["hvac", "plumbing", "electrical"])
    asyncio.run(seed(parser.parse_args()))


if __name__ == "__main__":
    main()
