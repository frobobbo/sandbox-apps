from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class BookStackConfig:
    base_url: str
    token_id: str
    token_secret: str
    default_book_id: str | None = None
    default_chapter_id: str | None = None

    @classmethod
    def from_env(cls) -> "BookStackConfig | None":
        base_url = os.getenv("BOOKSTACK_BASE_URL", "").rstrip("/")
        token_id = os.getenv("BOOKSTACK_TOKEN_ID", "")
        token_secret = os.getenv("BOOKSTACK_TOKEN_SECRET", "")
        if not (base_url and token_id and token_secret):
            return None
        return cls(
            base_url=base_url,
            token_id=token_id,
            token_secret=token_secret,
            default_book_id=os.getenv("BOOKSTACK_BOOK_ID") or None,
            default_chapter_id=os.getenv("BOOKSTACK_CHAPTER_ID") or None,
        )


def is_configured() -> bool:
    return BookStackConfig.from_env() is not None


def publish_page(
    *,
    title: str,
    markdown: str,
    book_id: str | None = None,
    chapter_id: str | None = None,
    config: BookStackConfig | None = None,
) -> dict[str, object]:
    """Publish a markdown page to BookStack using env-backed API credentials.

    This function never logs or returns token values. Callers can catch RuntimeError
    and display the sanitized error message to the local user.
    """
    cfg = config or BookStackConfig.from_env()
    if cfg is None:
        raise RuntimeError("BookStack is not configured. Set BOOKSTACK_BASE_URL, BOOKSTACK_TOKEN_ID, and BOOKSTACK_TOKEN_SECRET.")

    target_book_id = book_id or cfg.default_book_id
    target_chapter_id = chapter_id or cfg.default_chapter_id
    if not target_book_id and not target_chapter_id:
        raise RuntimeError("BookStack publishing needs BOOKSTACK_BOOK_ID or BOOKSTACK_CHAPTER_ID, or a value submitted from the form.")

    payload: dict[str, object] = {
        "name": title,
        "markdown": markdown,
    }
    if target_chapter_id:
        payload["chapter_id"] = int(target_chapter_id)
    elif target_book_id:
        payload["book_id"] = int(target_book_id)

    request = urllib.request.Request(
        f"{cfg.base_url}/api/pages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Token {cfg.token_id}:{cfg.token_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310: user-configured internal BookStack URL
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {"status": response.status}
    except urllib.error.HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"BookStack API returned HTTP {exc.code}: {_sanitize(message)}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"BookStack API request failed: {_sanitize(str(exc.reason))}") from exc


def _sanitize(message: str) -> str:
    cfg = BookStackConfig.from_env()
    if cfg is None:
        return message
    sanitized = message.replace(cfg.token_id, "[BOOKSTACK_TOKEN_ID]")
    sanitized = sanitized.replace(cfg.token_secret, "[BOOKSTACK_TOKEN_SECRET]")
    return sanitized
