from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any
from urllib.parse import parse_qsl


def validate_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> dict[str, Any] | None:
    """Verify Telegram WebApp initData per the official signing scheme."""
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        return None

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    auth_date = pairs.get("auth_date")
    if auth_date and time.time() - int(auth_date) > max_age_seconds:
        return None

    user = None
    if "user" in pairs:
        try:
            user = json.loads(pairs["user"])
        except json.JSONDecodeError:
            user = None

    return {"user": user, "auth_date": auth_date}
