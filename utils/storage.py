"""
تخزين بسيط مبني على JSON لكل إعدادات السيرفرات (تايم / رتب / باند)
وكمان عدّادات الاستخدام اليومي لكل شخص.
"""

import json
import os
import asyncio
from datetime import date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "guilds.json")

_lock = asyncio.Lock()


def _ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def _read() -> dict:
    _ensure_files()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _write(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _default_guild() -> dict:
    return {
        "time": {
            "giver_role_id": None,
            "daily_limit": None,
            "admin_role_id": None,
            "log_channel_id": None,
            "usage": {},   # {user_id: {"date": "YYYY-MM-DD", "count": N}}
            "active": {},  # {target_user_id: giver_user_id}  -> مين عطى مين تايم حالياً
        },
        "role": {
            "allowed_role_id": None,
            "log_channel_id": None,
        },
        "ban": {
            "allowed_role_id": None,
            "daily_limit": None,
            "unlimited_role_id": None,
            "log_channel_id": None,
            "usage": {},
        },
    }


class Storage:
    @staticmethod
    async def get_guild(guild_id: int) -> dict:
        async with _lock:
            data = _read()
            gid = str(guild_id)
            merged = _default_guild()
            existing = data.get(gid, {})
            for section in merged:
                merged[section].update(existing.get(section, {}))
            return merged

    @staticmethod
    async def update_guild(guild_id: int, section: str, updates: dict):
        async with _lock:
            data = _read()
            gid = str(guild_id)
            if gid not in data:
                data[gid] = _default_guild()
            data[gid].setdefault(section, {})
            data[gid][section].update(updates)
            _write(data)

    # ---------- الحدود اليومية ----------

    @staticmethod
    async def get_usage(guild_id: int, section: str, user_id: int) -> int:
        today = date.today().isoformat()
        async with _lock:
            data = _read()
            gid = str(guild_id)
            usage = data.get(gid, {}).get(section, {}).get("usage", {})
            entry = usage.get(str(user_id))
            if not entry or entry.get("date") != today:
                return 0
            return entry.get("count", 0)

    @staticmethod
    async def increment_usage(guild_id: int, section: str, user_id: int):
        today = date.today().isoformat()
        async with _lock:
            data = _read()
            gid = str(guild_id)
            if gid not in data:
                data[gid] = _default_guild()
            data[gid].setdefault(section, {})
            data[gid][section].setdefault("usage", {})
            usage = data[gid][section]["usage"]
            entry = usage.get(str(user_id))
            if not entry or entry.get("date") != today:
                entry = {"date": today, "count": 0}
            entry["count"] += 1
            usage[str(user_id)] = entry
            _write(data)

    # ---------- مين عطى مين تايم (عشان أمر $ان) ----------

    @staticmethod
    async def set_timeout_giver(guild_id: int, target_id: int, giver_id: int):
        async with _lock:
            data = _read()
            gid = str(guild_id)
            if gid not in data:
                data[gid] = _default_guild()
            data[gid].setdefault("time", {}).setdefault("active", {})
            data[gid]["time"]["active"][str(target_id)] = giver_id
            _write(data)

    @staticmethod
    async def get_timeout_giver(guild_id: int, target_id: int):
        async with _lock:
            data = _read()
            gid = str(guild_id)
            return data.get(gid, {}).get("time", {}).get("active", {}).get(str(target_id))

    @staticmethod
    async def clear_timeout_giver(guild_id: int, target_id: int):
        async with _lock:
            data = _read()
            gid = str(guild_id)
            active = data.get(gid, {}).get("time", {}).get("active", {})
            active.pop(str(target_id), None)
            _write(data)
