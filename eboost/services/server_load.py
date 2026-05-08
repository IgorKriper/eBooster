from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eboost.core.config import Settings, get_settings
from eboost.core.time import as_utc, utcnow
from eboost.models import ServerLoadState
from eboost.services import logs
from eboost.services.vpn.factory import get_vpn_provider
from eboost.services.vpn.marzban import MarzbanVpnProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServerSpec:
    code: str
    name: str
    host: str
    priority: int
    capacity_mbps: int


async def server_load_monitor_loop(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    settings = get_settings()
    while True:
        try:
            async with session_maker() as session:
                await refresh_server_loads(bot, session, settings=settings)
                await session.commit()
        except Exception:
            logger.exception("Server load monitor failed")
        await asyncio.sleep(settings.server_load_check_interval_seconds)


async def refresh_server_loads(bot: Bot, session: AsyncSession, *, settings: Settings | None = None) -> list[ServerLoadState]:
    settings = settings or get_settings()
    states = await ensure_server_states(session, settings=settings)
    provider = get_vpn_provider(settings)
    if not isinstance(provider, MarzbanVpnProvider):
        return states

    now = utcnow()
    try:
        system_stats = await provider.get_system_stats()
        nodes = await provider.get_nodes()
        start = min((as_utc(state.last_sample_at) for state in states if state.last_sample_at), default=now - timedelta(minutes=5))
        usage = await provider.get_nodes_usage(start=start, end=now)
        metrics = _metrics_from_marzban(states, system_stats=system_stats, nodes=nodes, usage=usage, now=now)
        for state in states:
            metric = metrics.get(state.code)
            if metric is None:
                continue
            state.rx_bytes = metric["rx_bytes"]
            state.tx_bytes = metric["tx_bytes"]
            state.load_percent = metric["load_percent"]
            state.last_sample_at = now
            state.last_error = None
        await _sync_hosts(provider, states)
    except Exception as exc:
        for state in states:
            state.last_error = str(exc)
        await logs.system_log(session, event="server_load_error", details={"error": str(exc)})

    for state in states:
        await _maybe_notify_admins(bot, session, state, settings=settings)
    return states


async def ensure_server_states(session: AsyncSession, *, settings: Settings | None = None) -> list[ServerLoadState]:
    settings = settings or get_settings()
    specs = _server_specs(settings)
    result = await session.execute(select(ServerLoadState))
    existing = {state.code: state for state in result.scalars().all()}
    states: list[ServerLoadState] = []
    for spec in specs:
        state = existing.get(spec.code)
        if state is None:
            state = ServerLoadState(
                code=spec.code,
                name=spec.name,
                host=spec.host,
                priority=spec.priority,
                capacity_mbps=spec.capacity_mbps,
                is_enabled=True,
            )
            session.add(state)
        state.name = spec.name
        state.host = spec.host
        state.priority = spec.priority
        state.capacity_mbps = spec.capacity_mbps
        states.append(state)
    return sorted(states, key=lambda state: state.priority)


async def set_server_enabled(
    session: AsyncSession,
    *,
    code: str,
    enabled: bool,
    admin_id: int | None = None,
) -> ServerLoadState | None:
    states = await ensure_server_states(session)
    state = next((item for item in states if item.code == code), None)
    if state is None:
        return None
    state.is_enabled = enabled
    if admin_id is not None:
        await logs.admin_log(
            session,
            admin_id=admin_id,
            action="server_enabled" if enabled else "server_disabled",
            details={"server": state.name, "code": state.code},
        )
    provider = get_vpn_provider(get_settings())
    if isinstance(provider, MarzbanVpnProvider):
        try:
            await _sync_hosts(provider, states)
        except Exception as exc:
            state.last_error = str(exc)
            await logs.system_log(session, event="server_sync_error", details={"error": str(exc), "server": state.name})
    return state


def format_server_loads(states: list[ServerLoadState]) -> str:
    rows = []
    for state in sorted(states, key=_sort_key):
        status = "включён" if state.is_enabled else "отключён"
        error = "\nОшибка: <code>{}</code>".format(_short(state.last_error)) if state.last_error else ""
        rows.append(
            f"<b>{state.name}</b>\n"
            f"Загрузка: <b>{state.load_percent:.0f}%</b>\n"
            f"Статус: <b>{status}</b>{error}"
        )
    return "<b>📊 Нагрузка серверов</b>\n\n" + "\n\n".join(rows)


def _server_specs(settings: Settings) -> list[ServerSpec]:
    specs: list[ServerSpec] = []
    for raw_item in settings.vpn_server_specs.split(";"):
        item = raw_item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split("|")]
        if len(parts) != 5:
            continue
        code, name, host, priority, capacity_mbps = parts
        specs.append(
            ServerSpec(
                code=code.lower(),
                name=name,
                host=host,
                priority=int(priority),
                capacity_mbps=int(capacity_mbps),
            )
        )
    return specs


def _metrics_from_marzban(
    states: list[ServerLoadState],
    *,
    system_stats: dict[str, Any],
    nodes: list[dict[str, Any]],
    usage: dict[str, Any],
    now,
) -> dict[str, dict[str, float | int]]:
    node_records = _usage_records(usage)
    metrics: dict[str, dict[str, float | int]] = {}
    for state in states:
        if state.code == "de":
            rx_speed = _number(system_stats, "incoming_bandwidth_speed", "incoming_bandwidth", "download_speed")
            tx_speed = _number(system_stats, "outgoing_bandwidth_speed", "outgoing_bandwidth", "upload_speed")
            bps = (rx_speed + tx_speed) * 8
            metrics[state.code] = {
                "rx_bytes": int(state.rx_bytes + max(rx_speed, 0)),
                "tx_bytes": int(state.tx_bytes + max(tx_speed, 0)),
                "load_percent": _load_percent(bps, state.capacity_mbps),
            }
            continue

        node = _match_node(state, nodes)
        record = _match_usage_record(state, node, node_records)
        rx_bytes = int(_number(record, "downlink", "download", "rx", "incoming", "total_downlink"))
        tx_bytes = int(_number(record, "uplink", "upload", "tx", "outgoing", "total_uplink"))
        previous = as_utc(state.last_sample_at)
        seconds = max((now - previous).total_seconds(), 1) if previous else 300
        bps = max(rx_bytes + tx_bytes, 0) * 8 / seconds
        metrics[state.code] = {
            "rx_bytes": max(rx_bytes, state.rx_bytes),
            "tx_bytes": max(tx_bytes, state.tx_bytes),
            "load_percent": _load_percent(bps, state.capacity_mbps),
        }
    return metrics


async def _sync_hosts(provider: MarzbanVpnProvider, states: list[ServerLoadState]) -> None:
    hosts = await provider.get_hosts()
    if not isinstance(hosts, dict):
        return
    state_by_host = {state.host: state for state in states}
    changed = False
    for inbound, items in hosts.items():
        if not isinstance(items, list):
            continue
        managed = []
        others = []
        for item in items:
            if not isinstance(item, dict):
                others.append(item)
                continue
            state = _state_for_host_item(item, state_by_host)
            if state is None:
                others.append(item)
                continue
            item["remark"] = state.name
            item["address"] = state.host
            if "is_disabled" in item:
                item["is_disabled"] = not state.is_enabled
            if "disabled" in item:
                item["disabled"] = not state.is_enabled
            managed.append(item)
            changed = True
        if managed:
            hosts[inbound] = sorted(managed, key=lambda item: _sort_key(_state_for_host_item(item, state_by_host))) + others
            changed = True
    if changed:
        await provider.update_hosts(hosts)


async def _maybe_notify_admins(bot: Bot, session: AsyncSession, state: ServerLoadState, *, settings: Settings) -> None:
    now = utcnow()
    # Skip nodes we have not sampled yet (e.g. first run or Marzban error)
    if state.load_percent is None:
        return
    if state.load_percent < settings.server_load_reset_percent:
        state.alert_level = None
        state.alert_sent_at = None
        return
    level = None
    cooldown = None
    if state.load_percent >= settings.server_load_critical_percent:
        level = "critical"
        cooldown = timedelta(hours=settings.server_load_critical_cooldown_hours)
    elif state.load_percent >= settings.server_load_warning_percent:
        level = "warning"
        cooldown = timedelta(hours=settings.server_load_warning_cooldown_hours)
    if level is None:
        return
    last_sent = as_utc(state.alert_sent_at)
    if state.alert_level == level and last_sent and now - last_sent < cooldown:
        return
    text = (
        "<b>⚠️ Сервер перегружен</b>\n\n"
        f"Сервер: <b>{state.name}</b>\n"
        f"Загрузка: <b>{state.load_percent:.0f}%</b>"
    )
    for admin_id in settings.admin_id_set:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception("Could not send server load alert to admin %s", admin_id)
    state.alert_level = level
    state.alert_sent_at = now
    await logs.system_log(
        session,
        event="server_load_alert",
        details={"server": state.name, "load": state.load_percent, "level": level},
    )


def _usage_records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in ("items", "nodes", "usages", "data", "results"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return [value for value in data.values() if isinstance(value, dict)]


def _match_node(state: ServerLoadState, nodes: list[dict[str, Any]]) -> dict[str, Any]:
    for node in nodes:
        text = " ".join(str(node.get(key, "")) for key in ("name", "address", "host"))
        if state.host in text or state.code in text.lower() or state.name.lower() in text.lower():
            return node
    return {}


def _match_usage_record(
    state: ServerLoadState,
    node: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    node_id = node.get("id")
    node_name = str(node.get("name", ""))
    for record in records:
        text = " ".join(str(record.get(key, "")) for key in ("node_id", "node", "node_name", "name", "address", "host"))
        if (node_id is not None and str(node_id) in text) or state.host in text or state.code in text.lower() or node_name in text:
            return record
    return {}


def _state_for_host_item(item: dict[str, Any], state_by_host: dict[str, ServerLoadState]) -> ServerLoadState | None:
    host = str(item.get("address") or item.get("host") or item.get("sni") or "")
    return state_by_host.get(host)


def _number(data: dict[str, Any], *keys: str) -> float:
    for key in keys:
        value = data.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                continue
    return 0


def _load_percent(bps: float, capacity_mbps: int) -> float:
    capacity_bps = max(capacity_mbps, 1) * 1_000_000
    return max(0, min(100, bps / capacity_bps * 100))


def _sort_key(state: ServerLoadState | None) -> tuple[int, int, float, int]:
    if state is None:
        return (1, 1, 100, 999)
    overloaded = int(state.load_percent >= get_settings().server_load_warning_percent)
    return (int(not state.is_enabled), overloaded, state.load_percent if not overloaded else state.priority, state.priority)


def _short(value: str | None) -> str:
    if not value:
        return ""
    return value if len(value) <= 160 else value[:157] + "..."
