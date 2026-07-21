from __future__ import annotations

import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Any

from aiogram import Bot
from aiohttp import web

import broadcast
import config
import db
from telegram_auth import validate_init_data

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()

_MAX_FILES = 10
_MAX_FILE_SIZE = 45 * 1024 * 1024  # держим запас под лимит Telegram Bot API (~50MB)
_MAX_REQUEST_SIZE = 200 * 1024 * 1024

_GIF_EXTS = {".gif"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


def _require_admin(init_data: str) -> dict[str, Any] | None:
    payload = validate_init_data(init_data, config.BOT_TOKEN)
    if not payload or not payload.get("user"):
        return None
    user = payload["user"]
    if user.get("id") not in config.ADMIN_IDS:
        return None
    return user


def _classify_file(filename: str, content_type: str) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext in _GIF_EXTS or content_type == "image/gif":
        return "animation"
    if ext in _IMAGE_EXTS or content_type.startswith("image/"):
        return "photo"
    if ext in _VIDEO_EXTS or content_type.startswith("video/"):
        return "video"
    return None


@routes.post("/api/auth")
async def api_auth(request: web.Request) -> web.Response:
    body = await request.json()
    user = _require_admin(body.get("initData", ""))
    if not user:
        return web.json_response({"ok": False}, status=403)
    return web.json_response({"ok": True, "user": user})


@routes.get("/api/stats")
async def api_stats(request: web.Request) -> web.Response:
    if not _require_admin(request.query.get("initData", "")):
        return web.json_response({"ok": False}, status=403)
    total = await db.count_users()
    return web.json_response({"ok": True, "total_users": total})


@routes.get("/api/users")
async def api_users(request: web.Request) -> web.Response:
    if not _require_admin(request.query.get("initData", "")):
        return web.json_response({"ok": False}, status=403)
    users = await db.list_users()
    return web.json_response({"ok": True, "users": users})


@routes.post("/api/broadcast")
async def api_broadcast(request: web.Request) -> web.Response:
    data = await request.post()

    user = _require_admin(str(data.get("initData", "")))
    if not user:
        return web.json_response({"ok": False}, status=403)

    text = str(data.get("text") or "").strip()
    if len(text) > 4000:
        return web.json_response({"ok": False, "error": "text_too_long"}, status=400)

    button_text = str(data.get("button_text") or "").strip() or None
    button_url = str(data.get("button_url") or "").strip() or None
    if bool(button_text) != bool(button_url):
        return web.json_response({"ok": False, "error": "button_needs_both_fields"}, status=400)

    exclude_ids: set[int] = set()
    raw_exclude = data.get("exclude_ids")
    if raw_exclude:
        try:
            exclude_ids = {int(x) for x in json.loads(str(raw_exclude))}
        except (ValueError, TypeError):
            return web.json_response({"ok": False, "error": "bad_exclude_ids"}, status=400)

    files = [f for f in data.getall("files", []) if isinstance(f, web.FileField) and f.filename]
    if len(files) > _MAX_FILES:
        return web.json_response({"ok": False, "error": "too_many_files"}, status=400)

    if not text and not files:
        return web.json_response({"ok": False, "error": "empty_broadcast"}, status=400)
    if files and len(text) > 1024:
        return web.json_response({"ok": False, "error": "caption_too_long"}, status=400)

    classified: list[tuple[str, web.FileField]] = []
    for f in files:
        kind = _classify_file(f.filename, f.content_type or "")
        if kind is None:
            return web.json_response({"ok": False, "error": f"unsupported_file:{f.filename}"}, status=400)
        classified.append((kind, f))

    if len(classified) >= 2 and any(kind == "animation" for kind, _ in classified):
        return web.json_response({"ok": False, "error": "gif_only_alone"}, status=400)

    if len(classified) == 1:
        media_kind_label = classified[0][0]
    elif len(classified) >= 2:
        media_kind_label = "album"
    else:
        media_kind_label = "none"

    user_ids = await db.get_active_user_ids(exclude_ids)
    broadcast_id = await db.create_broadcast(
        admin_id=user["id"],
        text=text,
        button_text=button_text,
        button_url=button_url,
        total=len(user_ids),
        media_kind=media_kind_label,
        excluded_count=len(exclude_ids),
    )

    upload_dir: Path | None = None
    media_items: list[tuple[str, Path]] = []
    if classified:
        upload_dir = config.DATA_DIR / "uploads" / str(broadcast_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        for i, (kind, f) in enumerate(classified):
            dest = upload_dir / f"{i}_{f.filename}"
            with open(dest, "wb") as out:
                shutil.copyfileobj(f.file, out)
            if dest.stat().st_size > _MAX_FILE_SIZE:
                shutil.rmtree(upload_dir, ignore_errors=True)
                return web.json_response({"ok": False, "error": f"file_too_large:{f.filename}"}, status=400)
            media_items.append((kind, dest))

    bot: Bot = request.app["bot"]
    asyncio.create_task(
        broadcast.run_broadcast(
            bot,
            broadcast_id,
            user_ids,
            text,
            button_text,
            button_url,
            media_items=media_items,
            upload_dir=upload_dir,
        )
    )
    return web.json_response({"ok": True, "broadcast_id": broadcast_id})


@routes.get("/api/broadcast/{broadcast_id}")
async def api_broadcast_status(request: web.Request) -> web.Response:
    if not _require_admin(request.query.get("initData", "")):
        return web.json_response({"ok": False}, status=403)
    try:
        broadcast_id = int(request.match_info["broadcast_id"])
    except ValueError:
        return web.json_response({"ok": False}, status=400)
    row = await db.get_broadcast(broadcast_id)
    if not row:
        return web.json_response({"ok": False}, status=404)
    return web.json_response({"ok": True, "broadcast": row})


@routes.get("/api/broadcasts")
async def api_broadcasts(request: web.Request) -> web.Response:
    if not _require_admin(request.query.get("initData", "")):
        return web.json_response({"ok": False}, status=403)
    rows = await db.list_broadcasts()
    return web.json_response({"ok": True, "broadcasts": rows})


@routes.get("/")
async def index(request: web.Request) -> web.Response:
    return web.FileResponse(config.ADMIN_WEBAPP_DIR / "index.html")


def create_app(bot: Bot) -> web.Application:
    app = web.Application(client_max_size=_MAX_REQUEST_SIZE)
    app["bot"] = bot
    app.add_routes(routes)
    app.router.add_static("/", config.ADMIN_WEBAPP_DIR)
    return app


async def run_api_server(bot: Bot) -> None:
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.WEBAPP_API_HOST, config.WEBAPP_API_PORT)
    await site.start()
    logger.info("Admin API server started on %s:%s", config.WEBAPP_API_HOST, config.WEBAPP_API_PORT)
    await asyncio.Event().wait()
