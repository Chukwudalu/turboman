import json
import re
import sys
from datetime import datetime, timezone

# Redact phone numbers before they hit logs
_PHONE_RE = re.compile(r"(\+?1?\d{10,15})|(\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b)")


def _redact(value: str) -> str:
    return _PHONE_RE.sub("[REDACTED]", value)


def _log(level: str, msg: str, **meta):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "msg": _redact(str(msg)),
        **{k: _redact(str(v)) if isinstance(v, str) else v for k, v in meta.items()},
    }
    stream = sys.stderr if level == "error" else sys.stdout
    stream.write(json.dumps(entry) + "\n")
    stream.flush()


class Logger:
    def info(self, msg: str, **meta):     _log("info",  msg, **meta)
    def warn(self, msg: str, **meta):     _log("warn",  msg, **meta)
    def warning(self, msg: str, **meta):  _log("warn",  msg, **meta)
    def error(self, msg: str, **meta):    _log("error", msg, **meta)
    def debug(self, msg: str, **meta):
        import os
        if os.getenv("ENV") != "production":
            _log("debug", msg, **meta)


logger = Logger()
