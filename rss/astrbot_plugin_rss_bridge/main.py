from __future__ import annotations

import asyncio
import hashlib
import html
import json
import re
import shlex
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import aiohttp
import feedparser
from PIL import Image
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

PLUGIN_NAME = "astrbot_plugin_rss_bridge"
STATE_VERSION = 1
MAX_SEEN_CACHE = 200
DEFAULT_USER_AGENT = "astrbot-plugin-rss-bridge/0.1.0"
MESSAGE_TEMPLATE_PRESETS = {
    "classic": (
        "【RSS 更新】{alias}\n"
        "{feed_title_line}"
        "{title_line}"
        "{published_line}"
        "{summary_line}"
        "{link_line}"
    ),
    "pretty": (
        "┏━📰 RSS 更新 ━┓\n"
        "🔖 订阅：{alias}\n"
        "{feed_title_pretty}"
        "{title_pretty}"
        "{published_pretty}"
        "{summary_pretty}"
        "{link_pretty}"
        "┗━━━━━━━━━━━━┛"
    ),
    "compact": "📰 {alias}\n{title}\n{link}",
}
OVERFLOW_TEMPLATE_PRESETS = {
    "classic": (
        "【RSS 更新】{alias}\n"
        "本次检测到 {new_count} 条新内容，为避免刷屏仅推送最近 {sent_count} 条，其余 {skipped_count} 条已跳过。"
    ),
    "pretty": (
        "┏━📢 RSS 汇总 ━┓\n"
        "🔖 订阅：{alias}\n"
        "📥 新增：{new_count} 条\n"
        "✅ 已推送：{sent_count} 条\n"
        "⏭️ 跳过：{skipped_count} 条\n"
        "┗━━━━━━━━━━━━┛"
    ),
    "compact": "{alias}：新增 {new_count} 条，已推送 {sent_count} 条，跳过 {skipped_count} 条",
}
IMAGE_TEMPLATE_PRESETS = {
    "aurora": r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <style>
    body { margin: 0; font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 45%, #22c55e 100%); }
    .card { width: 1120px; margin: 0 auto; color: #f8fafc; padding: 44px; box-sizing: border-box; }
    .panel { background: rgba(15, 23, 42, 0.72); border: 1px solid rgba(255,255,255,0.14); box-shadow: 0 20px 60px rgba(0,0,0,0.25); border-radius: 28px; padding: 34px; backdrop-filter: blur(14px); }
    .badge { display:inline-block; padding: 8px 14px; border-radius: 999px; background: rgba(255,255,255,0.12); font-size: 20px; margin-bottom: 18px; }
    .title { font-size: 32px; line-height: 1.45; font-weight: 700; margin-bottom: 18px; }
    .meta { font-size: 20px; color: #dbeafe; margin-bottom: 18px; }
    .summary { font-size: 24px; line-height: 1.7; color: #e2e8f0; background: rgba(255,255,255,0.08); border-radius: 20px; padding: 20px 22px; }
    .footer { margin-top: 22px; font-size: 16px; color: rgba(255,255,255,0.75); }
  </style>
</head>
<body>
  <div class="card">
    <div class="panel">
      <div class="badge">📰 RSS 更新</div>
      <div class="title">{{ title }}</div>
      {% if published %}<div class="meta">🕒 {{ published }}</div>{% endif %}
      {% if summary %}<div class="summary">{{ summary }}</div>{% endif %}
      <div class="footer">{{ render_time }}</div>
    </div>
  </div>
</body>
</html>
""",
    "newspaper": r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <style>
    body { margin: 0; background: #f6efe2; font-family: Georgia, "Times New Roman", "Songti SC", serif; color: #1f2937; }
    .paper { width: 1080px; margin: 0 auto; padding: 40px; box-sizing: border-box; background: linear-gradient(180deg, #fbf7ef 0%, #f3ead8 100%); border-left: 10px solid #7c2d12; border-right: 10px solid #7c2d12; }
    .top { border-bottom: 4px double #7c2d12; padding-bottom: 14px; margin-bottom: 24px; }
    .tag { font-size: 18px; letter-spacing: 4px; color: #7c2d12; text-transform: uppercase; }
    .title { font-size: 34px; line-height: 1.45; font-weight: 700; margin-bottom: 18px; }
    .meta { font-size: 19px; color: #6b7280; margin-bottom: 18px; }
    .summary { font-size: 24px; line-height: 1.85; text-align: justify; column-count: 2; column-gap: 28px; }
    .footer { margin-top: 18px; font-size: 16px; color: #92400e; border-top: 1px dashed #b45309; padding-top: 12px; }
  </style>
</head>
<body>
  <div class="paper">
    <div class="top">
      <div class="tag">RSS BULLETIN</div>
    </div>
    <div class="title">{{ title }}</div>
    {% if published %}<div class="meta">{{ published }}</div>{% endif %}
    {% if summary %}<div class="summary">{{ summary }}</div>{% endif %}
    <div class="footer">{{ render_time }}</div>
  </div>
</body>
</html>
""",
    "glass": r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <style>
    body { margin:0; background:
      radial-gradient(circle at top left, #f472b6 0%, transparent 28%),
      radial-gradient(circle at top right, #60a5fa 0%, transparent 34%),
      linear-gradient(135deg, #111827 0%, #312e81 50%, #1f2937 100%);
      font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }
    .wrap { width: 1120px; margin: 0 auto; padding: 44px; box-sizing: border-box; }
    .card { padding: 34px; border-radius: 32px; background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.18); backdrop-filter: blur(22px); color: white; box-shadow: 0 18px 60px rgba(0,0,0,0.3); }
    .row { display:flex; justify-content: space-between; gap: 16px; align-items: center; margin-bottom: 18px; }
    .chip { background: rgba(255,255,255,0.18); border-radius: 999px; padding: 8px 14px; font-size: 18px; }
    .title { font-size: 30px; line-height: 1.5; margin-bottom: 14px; }
    .summary { background: rgba(15,23,42,0.25); border-radius: 22px; padding: 18px 20px; font-size: 23px; line-height: 1.72; color: #eef2ff; }
    .footer { margin-top: 18px; font-size: 16px; color: #dbeafe; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="row">
        <div class="chip">✨ 精美预览</div>
        {% if published %}<div class="chip">{{ published }}</div>{% endif %}
      </div>
      <div class="title">{{ title }}</div>
      {% if summary %}<div class="summary">{{ summary }}</div>{% endif %}
      <div class="footer">{{ render_time }}</div>
    </div>
  </div>
</body>
</html>
""",
    "minimal": r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <style>
    body { margin: 0; background: #ffffff; font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif; color: #111827; }
    .wrap { width: 1040px; margin: 0 auto; padding: 40px; box-sizing: border-box; }
    .head { border-bottom: 1px solid #e5e7eb; padding-bottom: 18px; margin-bottom: 24px; }
    .title { font-size: 32px; line-height: 1.5; margin-bottom: 16px; }
    .meta { color: #6b7280; font-size: 18px; margin-bottom: 18px; }
    .summary { font-size: 22px; line-height: 1.75; color: #1f2937; }
    .footer { margin-top: 20px; font-size: 16px; color: #6b7280; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <div class="title">{{ title }}</div>
    </div>
    {% if published %}<div class="meta">{{ published }}</div>{% endif %}
    {% if summary %}<div class="summary">{{ summary }}</div>{% endif %}
    <div class="footer">{{ render_time }}</div>
  </div>
</body>
</html>
""",
}
GROUP_PREFERENCE_DEFAULTS = {
    "template_style": "",
    "message_render_mode": "",
    "image_template_style": "",
    "preview_render_mode": "",
}


class RSSBridgePlugin(Star):
    def __init__(
        self,
        context: Context,
        config: AstrBotConfig | dict[str, Any] | None = None,
        *_args,
        **_kwargs,
    ):
        super().__init__(context)
        self.config = config or {}
        self._state_lock = asyncio.Lock()
        self._refresh_lock = asyncio.Lock()
        self._poll_task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None
        self._state: dict[str, Any] | None = None
        self._data_dir: Path = Path(get_astrbot_data_path()) / "plugin_data" / PLUGIN_NAME
        self._state_file: Path = self._data_dir / "state.json"
        self._rendered_dir: Path = self._data_dir / "rendered"

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        await self._ensure_state_loaded()
        if self._poll_task and not self._poll_task.done():
            return

        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("[%s] RSS 轮询任务已启动", PLUGIN_NAME)

    @filter.command("rss")
    async def rss(self, event: AstrMessageEvent):
        """管理群组 RSS 订阅并自动推送更新。"""
        tokens = self._parse_command_tokens(event.message_str)
        if not tokens or tokens[0].lower() in {"help", "h", "?"}:
            yield event.plain_result(self._help_text())
            return

        action = tokens[0].lower()

        if not getattr(event.message_obj, "group_id", ""):
            yield event.plain_result("请在群聊里使用 /rss 命令，这样每个群才能维护独立的 RSS 配置。")
            return

        if self._requires_admin(action) and not self._is_group_admin(event):
            yield event.plain_result(self._admin_denied_message())
            return

        if action == "add":
            if len(tokens) < 3:
                yield event.plain_result("用法：/rss add <名称> <RSS链接>")
                return
            alias = tokens[1].strip()
            url = tokens[2].strip()
            message = await self._handle_add_subscription(event, alias, url)
            yield event.plain_result(message)
            return

        if action in {"del", "delete", "remove", "rm"}:
            if len(tokens) < 2:
                yield event.plain_result("用法：/rss del <名称>")
                return
            message = await self._handle_delete_subscription(event, tokens[1].strip())
            yield event.plain_result(message)
            return

        if action == "rename":
            if len(tokens) < 3:
                yield event.plain_result("用法：/rss rename <旧名称> <新名称>")
                return
            message = await self._handle_rename_subscription(
                event,
                tokens[1].strip(),
                tokens[2].strip(),
            )
            yield event.plain_result(message)
            return

        if action == "list":
            message = await self._handle_list_subscriptions(event)
            yield event.plain_result(message)
            return

        if action in {"check", "pull", "now"}:
            alias = tokens[1].strip() if len(tokens) > 1 else None
            message = await self._handle_check_subscriptions(event, alias)
            yield event.plain_result(message)
            return

        if action in {"preview", "template"}:
            preview_args = tokens[1:]
            async for preview_result in self._handle_preview_template(event, preview_args):
                yield preview_result
            return

        if action == "style":
            message = await self._handle_style_command(event, tokens[1:])
            yield event.plain_result(message)
            return

        yield event.plain_result(
            "未知子命令。可用命令：add、del、rename、list、check、style、preview、help"
        )

    async def terminate(self):
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _poll_loop(self):
        await asyncio.sleep(5)
        while True:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("[%s] RSS 轮询任务执行失败", PLUGIN_NAME)

            await asyncio.sleep(self._poll_interval_seconds())

    async def _poll_once(self):
        await self._ensure_state_loaded()
        async with self._state_lock:
            state = self._state or self._default_state()
            tasks: list[tuple[str, str]] = []
            for umo, group_data in state.get("groups", {}).items():
                feeds = group_data.get("feeds", {})
                for alias in feeds:
                    tasks.append((umo, alias))

        for umo, alias in tasks:
            result = await self._refresh_subscription(umo, alias, manual=False)
            if result.get("error"):
                logger.warning(
                    "[%s] 检查订阅失败: group=%s alias=%s error=%s",
                    PLUGIN_NAME,
                    umo,
                    alias,
                    result["error"],
                )

    async def _handle_add_subscription(
        self, event: AstrMessageEvent, alias: str, url: str
    ) -> str:
        alias = alias.strip()
        if not alias:
            return "订阅名称不能为空。"
        if len(alias) > 50:
            return "订阅名称过长，请控制在 50 个字符以内。"
        if not self._is_valid_http_url(url):
            return "RSS 链接无效，请提供以 http:// 或 https:// 开头的地址。"

        try:
            probe = await self._probe_feed(url)
        except Exception as exc:
            logger.warning("[%s] RSS 链接校验失败: %s", PLUGIN_NAME, exc)
            return f"添加失败：{exc}"

        umo = event.unified_msg_origin
        async with self._refresh_lock:
            await self._ensure_state_loaded()
            async with self._state_lock:
                group_data = self._get_or_create_group_state(umo)
                feeds = group_data["feeds"]
                existing_key = self._find_alias_key(feeds, alias)
                if existing_key:
                    return f"本群中已经存在名为 “{existing_key}” 的订阅。"

                feeds[alias] = {
                    "url": url,
                    "feed_title": probe["feed_title"],
                    "etag": probe["etag"],
                    "last_modified": probe["last_modified"],
                    "seen_entries": probe["seen_entries"],
                    "initialized": True,
                    "last_checked_at": self._now_iso(),
                    "last_error": "",
                }
                await self._save_state_locked()

        title = probe["feed_title"] or "未识别标题"
        count = len(probe["seen_entries"])
        return (
            f"已添加订阅：{alias}\n"
            f"源标题：{title}\n"
            f"当前群已隔离保存此订阅。\n"
            f"已记录当前 {count} 条历史内容作为基线，后续只推送新增内容。"
        )

    async def _handle_delete_subscription(
        self, event: AstrMessageEvent, alias: str
    ) -> str:
        umo = event.unified_msg_origin
        async with self._refresh_lock:
            await self._ensure_state_loaded()
            async with self._state_lock:
                group_data = self._get_group_state(umo)
                if not group_data:
                    return "本群还没有任何 RSS 订阅。"

                feeds = group_data.get("feeds", {})
                actual_alias = self._find_alias_key(feeds, alias)
                if not actual_alias:
                    return f"没有找到名为 “{alias}” 的订阅。"

                feeds.pop(actual_alias, None)
                if not feeds:
                    self._state["groups"].pop(umo, None)
                await self._save_state_locked()

        return f"已删除订阅：{actual_alias}"

    async def _handle_rename_subscription(
        self, event: AstrMessageEvent, old_alias: str, new_alias: str
    ) -> str:
        if not new_alias:
            return "新名称不能为空。"
        if len(new_alias) > 50:
            return "新名称过长，请控制在 50 个字符以内。"

        umo = event.unified_msg_origin
        async with self._refresh_lock:
            await self._ensure_state_loaded()
            async with self._state_lock:
                group_data = self._get_group_state(umo)
                if not group_data:
                    return "本群还没有任何 RSS 订阅。"

                feeds = group_data.get("feeds", {})
                actual_old_alias = self._find_alias_key(feeds, old_alias)
                if not actual_old_alias:
                    return f"没有找到名为 “{old_alias}” 的订阅。"

                existing_new_alias = self._find_alias_key(feeds, new_alias)
                if existing_new_alias and existing_new_alias != actual_old_alias:
                    return f"本群中已经存在名为 “{existing_new_alias}” 的订阅。"

                subscription = feeds.pop(actual_old_alias)
                feeds[new_alias] = subscription
                await self._save_state_locked()

        return f"已将订阅 “{actual_old_alias}” 重命名为 “{new_alias}”"

    async def _handle_list_subscriptions(self, event: AstrMessageEvent) -> str:
        umo = event.unified_msg_origin
        await self._ensure_state_loaded()
        async with self._state_lock:
            group_data = self._get_group_state(umo)
            if not group_data or not group_data.get("feeds"):
                return "本群还没有 RSS 订阅。\n可用：/rss add <名称> <RSS链接>"

            lines = ["本群 RSS 订阅列表："]
            for alias, item in group_data["feeds"].items():
                title = item.get("feed_title") or "未识别标题"
                url = item.get("url") or ""
                lines.append(f"- {alias}")
                lines.append(f"  标题：{title}")
                lines.append(f"  链接：{url}")
            return "\n".join(lines)

    async def _handle_check_subscriptions(
        self, event: AstrMessageEvent, alias: str | None
    ) -> str:
        umo = event.unified_msg_origin
        await self._ensure_state_loaded()
        async with self._state_lock:
            group_data = self._get_group_state(umo)
            if not group_data or not group_data.get("feeds"):
                return "本群还没有 RSS 订阅。"

            if alias:
                actual_alias = self._find_alias_key(group_data["feeds"], alias)
                if not actual_alias:
                    return f"没有找到名为 “{alias}” 的订阅。"
                targets = [actual_alias]
            else:
                targets = list(group_data["feeds"].keys())

        checked = 0
        pushed = 0
        errors: list[str] = []
        for target_alias in targets:
            result = await self._refresh_subscription(umo, target_alias, manual=True)
            checked += 1
            pushed += int(result.get("sent_count", 0))
            if result.get("error"):
                errors.append(f"{target_alias}: {result['error']}")

        if errors:
            return (
                f"手动检查完成：共检查 {checked} 个订阅，成功推送 {pushed} 条。\n"
                f"失败项：{'；'.join(errors)}"
            )
        return f"手动检查完成：共检查 {checked} 个订阅，成功推送 {pushed} 条新内容。"

    async def _handle_style_command(
        self, event: AstrMessageEvent, args: list[str]
    ) -> str:
        umo = event.unified_msg_origin
        if not args:
            return await self._handle_show_group_style(umo)

        subcommand = args[0].lower()
        if subcommand == "reset":
            await self._update_group_preferences(
                umo,
                template_style="",
                message_render_mode="",
                image_template_style="",
                preview_render_mode="",
            )
            return "已清空本群模板偏好，后续将回退到全局插件配置。"

        if len(args) < 2:
            return (
                "用法：\n"
                "/rss style                      查看本群模板配置\n"
                "/rss style text <classic|pretty|compact|custom>\n"
                "/rss style image <aurora|newspaper|glass|minimal>\n"
                "/rss style render <text|image>\n"
                "/rss style preview <text|image>\n"
                "/rss style reset"
            )

        value = args[1].lower()
        if subcommand == "text":
            if value not in {"classic", "pretty", "compact", "custom"}:
                return "文本模板仅支持：classic / pretty / compact / custom"
            await self._update_group_preferences(umo, template_style=value)
            return f"已将本群文本模板风格设置为：{value}"

        if subcommand == "image":
            if value not in IMAGE_TEMPLATE_PRESETS:
                return "图片模板仅支持：aurora / newspaper / glass / minimal"
            await self._update_group_preferences(umo, image_template_style=value)
            return f"已将本群图片模板风格设置为：{value}"

        if subcommand == "render":
            if value not in {"text", "image"}:
                return "推送模式仅支持：text / image"
            await self._update_group_preferences(umo, message_render_mode=value)
            return f"已将本群实际推送模式设置为：{value}"

        if subcommand == "preview":
            if value not in {"text", "image"}:
                return "预览模式仅支持：text / image"
            await self._update_group_preferences(umo, preview_render_mode=value)
            return f"已将本群模板预览模式设置为：{value}"

        return "未知 style 子命令，可用：text / image / render / preview / reset"

    async def _handle_show_group_style(self, umo: str) -> str:
        await self._ensure_state_loaded()
        preferences = self._get_group_preferences(umo)
        return (
            "本群模板配置：\n"
            f"- 文本模板：{self._template_style(umo=umo)}"
            + ("（群自定义）" if preferences.get("template_style") else "（全局默认）")
            + "\n"
            f"- 图片模板：{self._image_template_style(umo=umo)}"
            + ("（群自定义）" if preferences.get("image_template_style") else "（全局默认）")
            + "\n"
            f"- 实际推送模式：{self._message_render_mode(umo)}"
            + ("（群自定义）" if preferences.get("message_render_mode") else "（全局默认）")
            + "\n"
            f"- 预览模式：{self._preview_mode(umo)}"
            + ("（群自定义）" if preferences.get("preview_render_mode") else "（全局默认）")
            + "\n\n"
            "可用命令：\n"
            "/rss style text <classic|pretty|compact|custom>\n"
            "/rss style image <aurora|newspaper|glass|minimal>\n"
            "/rss style render <text|image>\n"
            "/rss style preview <text|image>\n"
            "/rss style reset"
        )

    async def _refresh_subscription(
        self, umo: str, alias: str, manual: bool
    ) -> dict[str, Any]:
        async with self._refresh_lock:
            await self._ensure_state_loaded()
            async with self._state_lock:
                subscription = self._get_subscription_copy(umo, alias)
                if not subscription:
                    return {"error": "订阅不存在"}

            try:
                result = await self._fetch_feed(
                    subscription["url"],
                    subscription.get("etag") or None,
                    subscription.get("last_modified") or None,
                )
            except Exception as exc:
                await self._update_subscription_meta(
                    umo,
                    alias,
                    last_error=str(exc),
                    last_checked_at=self._now_iso(),
                )
                return {"error": str(exc), "sent_count": 0}

            if result["not_modified"]:
                await self._update_subscription_meta(
                    umo,
                    alias,
                    last_checked_at=self._now_iso(),
                    last_error="",
                )
                return {"sent_count": 0, "not_modified": True}

            seen_entries = list(subscription.get("seen_entries", []))
            entries = result["entries"]
            feed_title = result["feed_title"] or subscription.get("feed_title") or alias

            if not subscription.get("initialized", False):
                baseline = [item["fingerprint"] for item in entries]
                await self._update_subscription_state(
                    umo,
                    alias,
                    feed_title=feed_title,
                    etag=result["etag"],
                    last_modified=result["last_modified"],
                    seen_entries=self._merge_seen_entries(seen_entries, baseline),
                    initialized=True,
                    last_checked_at=self._now_iso(),
                    last_error="",
                )
                return {"sent_count": 0, "initialized": True}

            unseen_entries = [
                item for item in entries if item["fingerprint"] not in set(seen_entries)
            ]
            if not unseen_entries:
                await self._update_subscription_state(
                    umo,
                    alias,
                    feed_title=feed_title,
                    etag=result["etag"],
                    last_modified=result["last_modified"],
                    last_checked_at=self._now_iso(),
                    last_error="",
                )
                return {"sent_count": 0}

            max_push = self._max_entries_per_push()
            to_send = list(reversed(unseen_entries[:max_push]))
            sent_entries: list[dict[str, Any]] = []
            skipped_count = max(0, len(unseen_entries) - len(to_send))

            try:
                for entry in to_send:
                    await self._send_entry_update(umo, alias, feed_title, entry)
                    sent_entries.append(entry)

                if skipped_count > 0:
                    await self._send_overflow_update(
                        umo,
                        alias=alias,
                        new_count=len(unseen_entries),
                        sent_count=len(to_send),
                        skipped_count=skipped_count,
                    )
            except Exception as exc:
                merged_seen = self._merge_seen_entries(
                    seen_entries,
                    [item["fingerprint"] for item in sent_entries],
                )
                await self._update_subscription_state(
                    umo,
                    alias,
                    feed_title=feed_title,
                    etag=result["etag"],
                    last_modified=result["last_modified"],
                    seen_entries=merged_seen,
                    last_checked_at=self._now_iso(),
                    last_error=str(exc),
                )
                return {"sent_count": len(sent_entries), "error": str(exc)}

            merged_seen = self._merge_seen_entries(
                seen_entries,
                [item["fingerprint"] for item in unseen_entries],
            )
            await self._update_subscription_state(
                umo,
                alias,
                feed_title=feed_title,
                etag=result["etag"],
                last_modified=result["last_modified"],
                seen_entries=merged_seen,
                last_checked_at=self._now_iso(),
                last_error="",
            )
            return {
                "sent_count": len(to_send),
                "skipped_count": skipped_count,
                "manual": manual,
            }

    async def _probe_feed(self, url: str) -> dict[str, Any]:
        result = await self._fetch_feed(url)
        if result["not_modified"]:
            raise RuntimeError("RSS 探测失败：服务器返回了未修改状态。")
        if not result["entries"] and not result["feed_title"]:
            raise RuntimeError("未识别到有效的 RSS/Atom 内容。")
        return {
            "feed_title": result["feed_title"],
            "etag": result["etag"],
            "last_modified": result["last_modified"],
            "seen_entries": [item["fingerprint"] for item in result["entries"]],
        }

    async def _fetch_feed(
        self,
        url: str,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> dict[str, Any]:
        session = await self._get_session()
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified

        async with session.get(url, headers=headers, allow_redirects=True) as response:
            if response.status == 304:
                return {
                    "not_modified": True,
                    "feed_title": "",
                    "entries": [],
                    "etag": etag,
                    "last_modified": last_modified,
                }
            if response.status >= 400:
                raise RuntimeError(f"请求失败，HTTP {response.status}")

            body = await response.read()
            response_etag = response.headers.get("ETag", "")
            response_last_modified = response.headers.get("Last-Modified", "")

        parsed = feedparser.parse(body)
        entries = [self._normalize_entry(item) for item in parsed.entries]
        feed_title = self._clean_text(getattr(parsed.feed, "title", "")) or ""

        if getattr(parsed, "bozo", False) and not entries:
            bozo_exc = getattr(parsed, "bozo_exception", None)
            raise RuntimeError(f"解析失败：{bozo_exc or '返回内容不是有效 RSS/Atom'}")

        return {
            "not_modified": False,
            "feed_title": feed_title,
            "entries": entries,
            "etag": response_etag,
            "last_modified": response_last_modified,
        }

    def _normalize_entry(self, entry: Any) -> dict[str, str]:
        title = self._clean_text(entry.get("title") or "") or "无标题"
        link = (entry.get("link") or "").strip()
        summary = self._extract_summary(entry)
        published = self._extract_published(entry)
        identity_source = (
            entry.get("id")
            or entry.get("guid")
            or link
            or f"{title}|{published}|{summary[:120]}"
        )
        fingerprint = hashlib.sha1(identity_source.encode("utf-8", "ignore")).hexdigest()
        return {
            "fingerprint": fingerprint,
            "title": title,
            "link": link,
            "summary": summary,
            "published": published,
        }

    def _extract_summary(self, entry: Any) -> str:
        summary = entry.get("summary") or entry.get("description") or ""
        if not summary and entry.get("content"):
            content_list = entry.get("content") or []
            if content_list and isinstance(content_list[0], dict):
                summary = content_list[0].get("value") or ""
        return self._clean_text(summary)

    def _extract_published(self, entry: Any) -> str:
        for key in ("published", "updated", "created"):
            value = entry.get(key)
            if not value:
                continue
            try:
                dt = parsedate_to_datetime(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
            except Exception:
                return self._clean_text(str(value))

        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            value = entry.get(key)
            if value:
                try:
                    dt = datetime(
                        value.tm_year,
                        value.tm_mon,
                        value.tm_mday,
                        value.tm_hour,
                        value.tm_min,
                        value.tm_sec,
                        tzinfo=timezone.utc,
                    )
                    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
                except Exception:
                    continue
        return ""

    def _format_entry_message(
        self,
        alias: str,
        feed_title: str,
        entry: dict[str, str],
        style: str | None = None,
        umo: str | None = None,
    ) -> str:
        context = self._build_message_template_context(
            alias,
            feed_title,
            entry,
            summary_limit=self._summary_max_length(),
        )
        template = self._entry_template(style, umo)
        fallback = MESSAGE_TEMPLATE_PRESETS.get(
            self._template_style(style, umo), MESSAGE_TEMPLATE_PRESETS["pretty"]
        )
        return self._render_template(template, context, fallback)

    def _format_overflow_message(
        self,
        alias: str,
        new_count: int,
        sent_count: int,
        skipped_count: int,
        style: str | None = None,
        umo: str | None = None,
    ) -> str:
        context = {
            "alias": alias,
            "new_count": str(new_count),
            "sent_count": str(sent_count),
            "skipped_count": str(skipped_count),
        }
        template = self._overflow_template(style, umo)
        fallback = OVERFLOW_TEMPLATE_PRESETS.get(
            self._template_style(style, umo), OVERFLOW_TEMPLATE_PRESETS["pretty"]
        )
        return self._render_template(template, context, fallback)

    async def _handle_preview_template(
        self, event: AstrMessageEvent, args: list[str]
    ):
        umo = event.unified_msg_origin
        mode = self._preview_mode(umo)
        style = ""
        show_all = False
        use_feed_preview = False
        alias_parts: list[str] = []

        for arg in args:
            normalized = arg.strip().lower()
            if normalized in {"text", "image"}:
                mode = normalized
            elif normalized in {"all", "styles"}:
                show_all = True
            elif normalized in {"feed", "source"}:
                use_feed_preview = True
            elif normalized in self._all_template_styles():
                style = normalized
            else:
                alias_parts.append(arg)

        alias = " ".join(alias_parts).strip()
        if alias:
            use_feed_preview = True

        preview_alias = "演示订阅"
        preview_feed_title = "AstrBot 官方博客"
        preview_entry = {
            "title": "AstrBot RSS 模板预览示例",
            "published": "2026-03-22 12:00:00 +0800",
            "summary": (
                "这是一条用于预览推送模板的演示消息。你可以在插件配置中切换 "
                "template_style，或者填写自定义模板字符串。"
            ),
            "link": "https://example.com/rss-preview",
        }

        if use_feed_preview:
            if not alias:
                yield event.plain_result("用法：/rss preview <订阅名称> [text|image]\n例如：/rss preview 少数派 image")
                return
            real_preview = await self._build_feed_preview_entry(umo, alias)
            if real_preview.get("error"):
                yield event.plain_result(f"预览失败：{real_preview['error']}")
                return
            preview_alias = real_preview["alias"]
            preview_feed_title = real_preview["feed_title"]
            preview_entry = real_preview["entry"]

        if mode == "image":
            styles = self._image_preview_styles(style, show_all, umo)
            yield event.plain_result(
                ("开始预览真实 RSS 内容图片模板：" if use_feed_preview else "开始预览图片模板：")
                + "、".join(styles)
                + "\n如需查看全部图片风格，可用：/rss preview all image"
            )
            for style_name in styles:
                try:
                    image_path = await self._render_entry_image(
                        alias=preview_alias,
                        feed_title=preview_feed_title,
                        entry=preview_entry,
                        style=style_name,
                    )
                    yield event.plain_result(
                        f"图片模板：{style_name}"
                        + (f"\n预览来源：{preview_alias}" if use_feed_preview else "")
                    )
                    yield event.image_result(str(image_path))
                except Exception as exc:
                    logger.warning("[%s] 图片模板预览失败: %s", PLUGIN_NAME, exc)
                    yield event.plain_result(
                        f"图片模板 {style_name} 预览失败：{exc}\n"
                        "请确认 AstrBot 已安装文转图依赖。"
                    )
            return

        styles = self._text_preview_styles(style, show_all, umo)
        preview_blocks: list[str] = []
        for style_name in styles:
            preview_blocks.append(
                f"=== 文本模板：{style_name} ==="
                + (f"\n预览来源：{preview_alias}" if use_feed_preview else "")
                + "\n"
                + self._format_entry_message(
                    preview_alias,
                    preview_feed_title,
                    preview_entry,
                    style=style_name,
                    umo=umo,
                )
                + "\n\n"
                + self._format_overflow_message(
                    alias=preview_alias,
                    new_count=8,
                    sent_count=3,
                    skipped_count=5,
                    style=style_name,
                    umo=umo,
                )
            )
        yield event.plain_result("\n\n".join(preview_blocks))

    async def _send_entry_update(
        self, umo: str, alias: str, feed_title: str, entry: dict[str, str]
    ):
        render_mode = self._message_render_mode(umo)
        if render_mode == "image":
            try:
                image_path = await self._render_entry_image(alias, feed_title, entry, umo=umo)
                chain = MessageChain().file_image(str(image_path))
                if entry.get("link"):
                    chain.message(f"\n来源：{entry['link']}")
                await self.context.send_message(umo, chain)
                return
            except Exception as exc:
                logger.warning("[%s] 图片推送失败，已回退文本: %s", PLUGIN_NAME, exc)

        message = self._format_entry_message(alias, feed_title, entry, umo=umo)
        await self.context.send_message(umo, MessageChain().message(message))

    async def _send_overflow_update(
        self, umo: str, alias: str, new_count: int, sent_count: int, skipped_count: int
    ):
        render_mode = self._message_render_mode(umo)
        if render_mode == "image":
            try:
                image_path = await self._render_overflow_image(
                    alias=alias,
                    new_count=new_count,
                    sent_count=sent_count,
                    skipped_count=skipped_count,
                    umo=umo,
                )
                await self.context.send_message(umo, MessageChain().file_image(str(image_path)))
                return
            except Exception as exc:
                logger.warning("[%s] 图片汇总推送失败，已回退文本: %s", PLUGIN_NAME, exc)

        await self.context.send_message(
            umo,
            MessageChain().message(
                self._format_overflow_message(
                    alias=alias,
                    new_count=new_count,
                    sent_count=sent_count,
                    skipped_count=skipped_count,
                    umo=umo,
                )
            ),
        )

    async def _render_entry_image(
        self,
        alias: str,
        feed_title: str,
        entry: dict[str, str],
        style: str | None = None,
        umo: str | None = None,
    ) -> str:
        template = self._image_template(style, umo)
        data = self._build_message_template_context(
            alias,
            feed_title,
            entry,
            summary_limit=self._image_summary_max_length(),
        )
        rendered_path = await self.html_render(
            template,
            data,
            return_url=False,
            options=self._image_render_options(),
        )
        return await self._maybe_compress_rendered_image(str(rendered_path))

    async def _render_overflow_image(
        self,
        alias: str,
        new_count: int,
        sent_count: int,
        skipped_count: int,
        style: str | None = None,
        umo: str | None = None,
    ) -> str:
        template = self._image_template(style, umo)
        data = {
            "alias": alias,
            "feed_title": "RSS 批量更新汇总",
            "title": f"本次新增 {new_count} 条内容",
            "published": self._now_iso(),
            "summary": (
                f"已推送 {sent_count} 条；为避免刷屏，已跳过 {skipped_count} 条。"
            ),
            "link": "",
        }
        rendered_path = await self.html_render(
            template,
            data,
            return_url=False,
            options=self._image_render_options(),
        )
        return await self._maybe_compress_rendered_image(str(rendered_path))

    async def _build_feed_preview_entry(self, umo: str, alias: str) -> dict[str, Any]:
        await self._ensure_state_loaded()
        async with self._state_lock:
            subscription = self._get_subscription_copy(umo, alias)
            if not subscription:
                return {"error": f"本群没有找到名为 “{alias}” 的 RSS 订阅。"}

        try:
            result = await self._fetch_feed(subscription["url"])
        except Exception as exc:
            return {"error": f"读取 RSS 失败：{exc}"}

        entries = result.get("entries") or []
        if not entries:
            return {"error": "该 RSS 源当前没有可用于预览的内容。"}

        return {
            "alias": alias,
            "feed_title": result.get("feed_title") or subscription.get("feed_title") or alias,
            "entry": entries[0],
        }

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session and not self._session.closed:
            return self._session

        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._request_timeout_seconds()),
            headers={"User-Agent": self._user_agent()},
        )
        return self._session

    async def _ensure_state_loaded(self):
        if self._state is not None:
            return

        async with self._state_lock:
            if self._state is not None:
                return

            self._data_dir.mkdir(parents=True, exist_ok=True)
            self._rendered_dir.mkdir(parents=True, exist_ok=True)
            if self._state_file.exists():
                try:
                    self._state = self._normalize_state(
                        json.loads(self._state_file.read_text(encoding="utf-8"))
                    )
                    return
                except Exception:
                    logger.exception("[%s] 读取状态文件失败，已回退到空状态", PLUGIN_NAME)

            self._state = self._default_state()
            await self._save_state_locked()

    def _default_state(self) -> dict[str, Any]:
        return {"version": STATE_VERSION, "groups": {}}

    def _normalize_state(self, raw: Any) -> dict[str, Any]:
        state = self._default_state()
        if not isinstance(raw, dict):
            return state

        groups = raw.get("groups", {})
        if not isinstance(groups, dict):
            return state

        normalized_groups: dict[str, Any] = {}
        for umo, group_data in groups.items():
            if not isinstance(umo, str) or not isinstance(group_data, dict):
                continue
            feeds = group_data.get("feeds", {})
            if not isinstance(feeds, dict):
                continue

            normalized_feeds: dict[str, Any] = {}
            for alias, item in feeds.items():
                if not isinstance(alias, str) or not isinstance(item, dict):
                    continue
                normalized_feeds[alias] = {
                    "url": str(item.get("url") or ""),
                    "feed_title": str(item.get("feed_title") or ""),
                    "etag": str(item.get("etag") or ""),
                    "last_modified": str(item.get("last_modified") or ""),
                    "seen_entries": [
                        str(value)
                        for value in item.get("seen_entries", [])
                        if isinstance(value, str)
                    ][:MAX_SEEN_CACHE],
                    "initialized": bool(item.get("initialized", False)),
                    "last_checked_at": str(item.get("last_checked_at") or ""),
                    "last_error": str(item.get("last_error") or ""),
                }

            raw_preferences = group_data.get("preferences", {})
            preferences = dict(GROUP_PREFERENCE_DEFAULTS)
            if isinstance(raw_preferences, dict):
                for key in preferences.keys():
                    preferences[key] = str(raw_preferences.get(key) or "")

            normalized_groups[umo] = {
                "feeds": normalized_feeds,
                "preferences": preferences,
            }

        state["groups"] = normalized_groups
        return state

    async def _save_state_locked(self):
        self._data_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = self._state_file.with_suffix(".tmp")
        tmp_file.write_text(
            json.dumps(self._state or self._default_state(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_file.replace(self._state_file)

    def _get_or_create_group_state(self, umo: str) -> dict[str, Any]:
        groups = self._state.setdefault("groups", {})
        group_state = groups.setdefault(
            umo,
            {"feeds": {}, "preferences": dict(GROUP_PREFERENCE_DEFAULTS)},
        )
        group_state.setdefault("feeds", {})
        group_state.setdefault("preferences", dict(GROUP_PREFERENCE_DEFAULTS))
        for key, value in GROUP_PREFERENCE_DEFAULTS.items():
            group_state["preferences"].setdefault(key, value)
        return group_state

    def _get_group_state(self, umo: str) -> dict[str, Any] | None:
        return (self._state or {}).get("groups", {}).get(umo)

    def _get_group_preferences(self, umo: str | None) -> dict[str, str]:
        if not umo:
            return dict(GROUP_PREFERENCE_DEFAULTS)
        group_data = self._get_group_state(umo)
        if not group_data:
            return dict(GROUP_PREFERENCE_DEFAULTS)
        preferences = group_data.get("preferences", {})
        merged = dict(GROUP_PREFERENCE_DEFAULTS)
        if isinstance(preferences, dict):
            for key in merged.keys():
                merged[key] = str(preferences.get(key) or "")
        return merged

    async def _update_group_preferences(self, umo: str, **kwargs):
        await self._ensure_state_loaded()
        async with self._state_lock:
            group_data = self._get_or_create_group_state(umo)
            preferences = group_data.setdefault("preferences", dict(GROUP_PREFERENCE_DEFAULTS))
            for key, value in kwargs.items():
                if key in GROUP_PREFERENCE_DEFAULTS:
                    preferences[key] = str(value or "")
            await self._save_state_locked()

    def _get_subscription_copy(self, umo: str, alias: str) -> dict[str, Any] | None:
        group_data = self._get_group_state(umo)
        if not group_data:
            return None
        feeds = group_data.get("feeds", {})
        actual_alias = self._find_alias_key(feeds, alias)
        if not actual_alias:
            return None
        return dict(feeds[actual_alias])

    async def _update_subscription_meta(self, umo: str, alias: str, **kwargs):
        await self._ensure_state_loaded()
        async with self._state_lock:
            group_data = self._get_group_state(umo)
            if not group_data:
                return
            feeds = group_data.get("feeds", {})
            actual_alias = self._find_alias_key(feeds, alias)
            if not actual_alias:
                return
            feeds[actual_alias].update(kwargs)
            await self._save_state_locked()

    async def _update_subscription_state(self, umo: str, alias: str, **kwargs):
        await self._ensure_state_loaded()
        async with self._state_lock:
            group_data = self._get_group_state(umo)
            if not group_data:
                return
            feeds = group_data.get("feeds", {})
            actual_alias = self._find_alias_key(feeds, alias)
            if not actual_alias:
                return
            feeds[actual_alias].update(kwargs)
            await self._save_state_locked()

    def _find_alias_key(self, feeds: dict[str, Any], alias: str) -> str | None:
        target = alias.casefold()
        for feed_alias in feeds.keys():
            if feed_alias.casefold() == target:
                return feed_alias
        return None

    def _merge_seen_entries(
        self, existing_entries: list[str], new_entries: list[str]
    ) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()
        for value in list(new_entries) + list(existing_entries):
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
            if len(merged) >= MAX_SEEN_CACHE:
                break
        return merged

    def _parse_command_tokens(self, message: str) -> list[str]:
        text = message.strip()
        if not text:
            return []
        try:
            tokens = shlex.split(text)
        except ValueError:
            tokens = text.split()

        if tokens:
            head = tokens[0].lstrip("/").lower()
            if head == "rss":
                return tokens[1:]
        return tokens

    def _help_text(self) -> str:
        return (
            "RSS 群组订阅插件\n"
            "支持 OneBot V11 / Telegram 群聊隔离订阅。\n\n"
            "命令：\n"
            "/rss add <名称> <RSS链接>  添加订阅\n"
            "/rss del <名称>            删除订阅\n"
            "/rss rename <旧名称> <新名称>  重命名订阅\n"
            "/rss list                  查看本群订阅\n"
            "/rss check [名称]          立即检查更新\n"
            "/rss style                 查看/设置本群模板风格\n"
            "/rss preview <订阅名称> [text|image]  预览真实 RSS 内容\n"
            "/rss preview [风格] [text|image]  预览模板\n"
            "/rss preview all image     预览全部图片风格\n"
            "/rss help                  查看帮助\n\n"
            "文本风格：classic / pretty / compact\n"
            "图片风格：aurora / newspaper / glass / minimal\n\n"
            "如果要按群设置模板，可用：\n"
            "/rss style text pretty\n"
            "/rss style image glass\n"
            "/rss style render image\n\n"
            "如果名称里有空格，请使用引号，例如：\n"
            '/rss add "少数派" https://sspai.com/feed'
        )

    def _clean_text(self, value: str) -> str:
        text = html.unescape(value or "")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _is_valid_http_url(self, value: str) -> bool:
        try:
            parsed = urlparse(value)
        except Exception:
            return False
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _poll_interval_seconds(self) -> int:
        value = int(self.config.get("poll_interval_seconds", 300) or 300)
        return max(60, value)

    def _request_timeout_seconds(self) -> int:
        value = int(self.config.get("request_timeout_seconds", 15) or 15)
        return max(5, value)

    def _summary_max_length(self) -> int:
        value = int(self.config.get("summary_max_length", 180) or 180)
        return max(50, value)

    def _image_summary_max_length(self) -> int:
        value = int(self.config.get("image_summary_max_length", 0) or 0)
        return max(0, value)

    def _max_entries_per_push(self) -> int:
        value = int(self.config.get("max_entries_per_push", 3) or 3)
        return max(1, value)

    def _user_agent(self) -> str:
        value = str(self.config.get("user_agent", DEFAULT_USER_AGENT) or "").strip()
        return value or DEFAULT_USER_AGENT

    def _image_render_options(self) -> dict[str, Any]:
        return {
            "type": "png",
            "full_page": True,
            "animations": "disabled",
            "caret": "hide",
            "scale": self._image_render_scale(),
            "timeout": self._image_render_timeout_ms(),
        }

    async def _maybe_compress_rendered_image(self, image_path: str) -> str:
        quality = self._image_compression_quality()
        if quality >= 100:
            return image_path

        try:
            await self._ensure_state_loaded()
            return await asyncio.to_thread(
                self._compress_rendered_image_sync,
                image_path,
                quality,
            )
        except Exception as exc:
            logger.warning("[%s] 图片压缩失败，已使用原图: %s", PLUGIN_NAME, exc)
            return image_path

    def _compress_rendered_image_sync(self, image_path: str, quality: int) -> str:
        source_path = Path(image_path)
        if not source_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        self._rendered_dir.mkdir(parents=True, exist_ok=True)
        target_path = self._rendered_dir / f"{source_path.stem}-{uuid4().hex}.jpg"
        with Image.open(source_path) as img:
            if img.mode not in {"RGB", "L"}:
                img = img.convert("RGB")
            img.save(
                target_path,
                format="JPEG",
                quality=quality,
                optimize=True,
                subsampling=0,
            )
        return str(target_path)

    def _image_render_scale(self) -> str:
        value = str(self.config.get("image_render_scale", "device") or "").strip().lower()
        if value in {"css", "device"}:
            return value
        return "device"

    def _image_render_timeout_ms(self) -> int:
        value = int(self.config.get("image_render_timeout_ms", 15000) or 15000)
        return max(3000, value)

    def _image_compression_quality(self) -> int:
        value = int(self.config.get("image_compression_quality", 95) or 95)
        return min(100, max(80, value))

    def _requires_admin(self, action: str) -> bool:
        if action in {"help", "h", "?", "list"}:
            return self._admin_only_list()
        return self._admin_only_commands()

    def _is_group_admin(self, event: AstrMessageEvent) -> bool:
        for value in (
            getattr(event, "role", ""),
            getattr(getattr(event.message_obj, "sender", None), "role", ""),
        ):
            normalized = str(value or "").strip().lower()
            if normalized in {"admin", "owner", "superadmin"}:
                return True
        return False

    def _admin_only_commands(self) -> bool:
        return self._get_bool_config("admin_only_commands", True)

    def _admin_only_list(self) -> bool:
        return self._get_bool_config("admin_only_list", False)

    def _admin_denied_message(self) -> str:
        value = str(
            self.config.get(
                "admin_denied_message",
                "只有群管理员才可以管理本群的 RSS 订阅。",
            )
            or ""
        ).strip()
        return value or "只有群管理员才可以管理本群的 RSS 订阅。"

    def _entry_template(self, style: str | None = None, umo: str | None = None) -> str:
        style = self._template_style(style, umo)
        if style == "custom":
            custom_template = str(self.config.get("custom_message_template", "") or "").strip()
            if custom_template:
                return custom_template
            style = "pretty"
        return MESSAGE_TEMPLATE_PRESETS.get(style, MESSAGE_TEMPLATE_PRESETS["pretty"])

    def _overflow_template(self, style: str | None = None, umo: str | None = None) -> str:
        style = self._template_style(style, umo)
        if style == "custom":
            custom_template = str(self.config.get("custom_overflow_template", "") or "").strip()
            if custom_template:
                return custom_template
            style = "pretty"
        return OVERFLOW_TEMPLATE_PRESETS.get(style, OVERFLOW_TEMPLATE_PRESETS["pretty"])

    def _template_style(self, style: str | None = None, umo: str | None = None) -> str:
        group_style = self._get_group_preferences(umo).get("template_style", "")
        value = str(style or group_style or self.config.get("template_style", "pretty") or "").strip().lower()
        if value in {"classic", "pretty", "compact", "custom"}:
            return value
        return "pretty"

    def _image_template(self, style: str | None = None, umo: str | None = None) -> str:
        return IMAGE_TEMPLATE_PRESETS.get(
            self._image_template_style(style, umo), IMAGE_TEMPLATE_PRESETS["aurora"]
        )

    def _image_template_style(self, style: str | None = None, umo: str | None = None) -> str:
        group_style = self._get_group_preferences(umo).get("image_template_style", "")
        value = str(style or group_style or self.config.get("image_template_style", "aurora") or "").strip().lower()
        if value in IMAGE_TEMPLATE_PRESETS:
            return value
        return "aurora"

    def _message_render_mode(self, umo: str | None = None) -> str:
        group_mode = self._get_group_preferences(umo).get("message_render_mode", "")
        value = str(group_mode or self.config.get("message_render_mode", "text") or "").strip().lower()
        if value in {"text", "image"}:
            return value
        return "text"

    def _preview_mode(self, umo: str | None = None) -> str:
        group_mode = self._get_group_preferences(umo).get("preview_render_mode", "")
        value = str(
            group_mode
            or self.config.get("preview_render_mode", self._message_render_mode(umo))
            or ""
        ).strip().lower()
        if value in {"text", "image"}:
            return value
        return "text"

    def _all_template_styles(self) -> set[str]:
        return set(MESSAGE_TEMPLATE_PRESETS) | set(IMAGE_TEMPLATE_PRESETS) | {"custom"}

    def _text_preview_styles(self, style: str, show_all: bool, umo: str | None = None) -> list[str]:
        if style and style in MESSAGE_TEMPLATE_PRESETS:
            return [style]
        if show_all:
            return list(MESSAGE_TEMPLATE_PRESETS.keys())
        return [self._template_style(umo=umo)]

    def _image_preview_styles(self, style: str, show_all: bool, umo: str | None = None) -> list[str]:
        if style and style in IMAGE_TEMPLATE_PRESETS:
            return [style]
        if show_all:
            return list(IMAGE_TEMPLATE_PRESETS.keys())
        return [self._image_template_style(umo=umo)]

    def _build_message_template_context(
        self,
        alias: str,
        feed_title: str,
        entry: dict[str, str],
        summary_limit: int | None = None,
    ) -> dict[str, str]:
        summary = entry.get("summary", "")
        if summary_limit is not None and summary_limit > 0 and len(summary) > summary_limit:
            summary = f"{summary[:summary_limit]}..."

        safe_feed_title = feed_title if feed_title and feed_title != alias else ""
        title = entry.get("title", "")
        published = entry.get("published", "")
        link = entry.get("link", "")

        context = {
            "alias": alias,
            "feed_title": safe_feed_title,
            "title": title,
            "published": published,
            "summary": summary,
            "link": link,
            "render_time": self._render_timestamp_beijing(),
            "feed_title_line": f"源标题：{safe_feed_title}\n" if safe_feed_title else "",
            "title_line": f"标题：{title}\n" if title else "",
            "published_line": f"时间：{published}\n" if published else "",
            "summary_line": f"摘要：{summary}\n" if summary else "",
            "link_line": f"链接：{link}\n" if link else "",
            "feed_title_pretty": f"🏷️ 源站：{safe_feed_title}\n" if safe_feed_title else "",
            "title_pretty": f"📌 标题：{title}\n" if title else "",
            "published_pretty": f"🕒 时间：{published}\n" if published else "",
            "summary_pretty": f"📝 摘要：{summary}\n" if summary else "",
            "link_pretty": f"🔗 链接：{link}\n" if link else "",
            "newline": "\n",
        }
        return context

    def _render_template(
        self, template: str, context: dict[str, str], fallback_template: str
    ) -> str:
        try:
            rendered = template.format_map(_SafeFormatDict(context))
        except Exception as exc:
            logger.warning("[%s] 模板渲染失败，已回退默认模板: %s", PLUGIN_NAME, exc)
            rendered = fallback_template.format_map(_SafeFormatDict(context))

        rendered = rendered.replace("\r\n", "\n").strip()
        rendered = re.sub(r"\n{3,}", "\n\n", rendered)
        return rendered

    def _get_bool_config(self, key: str, default: bool) -> bool:
        value = self.config.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off"}:
                return False
        return bool(value)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _render_timestamp_beijing(self) -> str:
        from datetime import timedelta

        tz = timezone(timedelta(hours=8))
        return datetime.now(tz).strftime("北京时间：%Y-%m-%d %H:%M:%S")


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return ""
