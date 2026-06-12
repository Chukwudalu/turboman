from __future__ import annotations

import asyncio

from supabase import create_client, Client
from src.config import settings

_sync_client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)


class _Proxy:
    """
    Wraps a postgrest-py query builder so .execute() runs in a thread pool
    instead of blocking the event loop.  All chaining methods (.select, .eq,
    .update, …) are forwarded transparently; intermediate results are
    re-wrapped so the chain keeps working.
    """

    __slots__ = ("_b",)

    def __init__(self, builder) -> None:
        self._b = builder

    def __getattr__(self, name: str):
        attr = getattr(self._b, name)
        if not callable(attr):
            return attr

        def _method(*args, **kwargs):
            result = attr(*args, **kwargs)
            if result is not None and hasattr(result, "execute"):
                return _Proxy(result)
            return result

        return _method

    async def execute(self):
        builder = self._b
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, builder.execute)


class _AsyncDB:
    """Thin async façade over the sync supabase client."""

    def table(self, name: str) -> _Proxy:
        return _Proxy(_sync_client.table(name))

    def rpc(self, name: str, params: dict) -> _Proxy:
        return _Proxy(_sync_client.rpc(name, params))


db = _AsyncDB()
