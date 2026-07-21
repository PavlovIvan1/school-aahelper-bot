from __future__ import annotations

import asyncio
import logging
from typing import Any

from aiogram import Bot
from aiohttp import web

import broadcast
import config
import db
from telegram_auth import validate_init_data

logger = logging.getLogger(__name__)

routes = web.RouteTableDef()


def _cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": config.CORS_ALLOWED_ORIGIN,
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers=_cors_headers())
    response = await handler(request)
    response.headers.update(_cors_headers())
    return response


def _require_admin(init_data: str) -> dict[str, Any] | None:
    payload = validate_init_data(init_data, config.BOT_TOKEN)
    if not payload or not payload.get("user"):
        return None
    user = payload["user"]
    if user.get("id") not in config.ADMIN_IDS:
        return None
    return user


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


@routes.post("/api/broadcast")
async def api_broadcast(request: web.Request) -> web.Response:
    body = await request.json()
    user = _require_admin(body.get("initData", ""))
    if not user:
        return web.json_response({"ok": False}, status=403)

    text = (body.get("text") or "").strip()
    if not text:
        return web.json_response({"ok": False, "error": "empty_text"}, status=400)
    if len(text) > 4000:
        return web.json_response({"ok": False, "error": "text_too_long"}, status=400)

    button_text = (body.get("button_text") or "").strip() or None
    button_url = (body.get("button_url") or "").strip() or None
    if bool(button_text) != bool(button_url):
        return web.json_response({"ok": False, "error": "button_needs_both_fields"}, status=400)

    user_ids = await db.get_active_user_ids()
    broadcast_id = await db.create_broadcast(
        admin_id=user["id"],
        text=text,
        button_text=button_text,
        button_url=button_url,
        total=len(user_ids),
    )

    bot: Bot = request.app["bot"]
    asyncio.create_task(broadcast.run_broadcast(bot, broadcast_id, text, button_text, button_url))
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


def create_app(bot: Bot) -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app["bot"] = bot
    app.add_routes(routes)
    return app


async def run_api_server(bot: Bot) -> None:
    app = create_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.WEBAPP_API_HOST, config.WEBAPP_API_PORT)
    await site.start()
    logger.info("Admin API server started on %s:%s", config.WEBAPP_API_HOST, config.WEBAPP_API_PORT)
    await asyncio.Event().wait()
