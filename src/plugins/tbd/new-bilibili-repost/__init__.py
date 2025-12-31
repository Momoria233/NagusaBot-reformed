import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import httpx
from nonebot import get_bot, get_driver, on_command, on_regex, require
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER

from src.common.config import global_config
from src.common.feature_manager import feature_manager
from src.common.models import Subscription
from src.common.resource import resource_manager

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

PLUGIN_NAME = "bilibili动态转发"
feature_manager.register(PLUGIN_NAME, ": \nbot现在会自动将部分烤肉动态转发到群里。")

INTERVAL_SECONDS = 120

driver = get_driver()
_http_client: Optional[httpx.AsyncClient] = None

DATA_DIR = resource_manager.get_data_dir("new-bilibili-repost")
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

EMERGENCY_STOP = False


@driver.on_startup
async def _init_http_client():
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(15.0))


@driver.on_shutdown
async def _close_http_client():
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


def _cache_file(uid: str, group_id: int) -> Path:
    safe_uid = "".join(ch for ch in str(uid) if ch.isdigit())
    return CACHE_DIR / f"dynamic_cache_{safe_uid}_{int(group_id)}.json"


def _load_cache(uid: str, group_id: int) -> List[str]:
    path = _cache_file(uid, group_id)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    out: List[str] = []
    for x in payload:
        if x is None:
            continue
        out.append(str(x))
    return out


def _save_cache(uid: str, group_id: int, ids: Sequence[str]) -> None:
    path = _cache_file(uid, group_id)
    path.write_text(json.dumps(list(ids), ensure_ascii=False), encoding="utf-8")


def _get_text_desc(item: Dict[str, Any]) -> str:
    desc = (
        item.get("modules", {})
        .get("module_dynamic", {})
        .get("desc", {})
    )
    if isinstance(desc, dict):
        text = desc.get("text")
        if isinstance(text, str):
            return text.strip()
    return ""


def _get_author_name(item: Dict[str, Any]) -> str:
    author = (
        item.get("modules", {})
        .get("module_author", {})
        .get("name")
    )
    return str(author) if author else ""


def _get_pictures(item: Dict[str, Any]) -> List[str]:
    items = (
        item.get("modules", {})
        .get("module_dynamic", {})
        .get("major", {})
        .get("draw", {})
        .get("items", [])
    )
    if not isinstance(items, list):
        return []
    out: List[str] = []
    for pic in items:
        if not isinstance(pic, dict):
            continue
        src = pic.get("src")
        if isinstance(src, str) and src:
            out.append(src)
    return out


def _get_archive(item: Dict[str, Any]) -> Dict[str, Any]:
    archive = (
        item.get("modules", {})
        .get("module_dynamic", {})
        .get("major", {})
        .get("archive", {})
    )
    return archive if isinstance(archive, dict) else {}


def _get_article(item: Dict[str, Any]) -> Dict[str, Any]:
    article = (
        item.get("modules", {})
        .get("module_dynamic", {})
        .get("major", {})
        .get("article", {})
    )
    return article if isinstance(article, dict) else {}


def _build_message_lines_for_item(
    item: Dict[str, Any],
    *,
    prefix: str = "",
    depth: int = 0,
) -> Tuple[List[str], List[str]]:
    dynamic_type = str(item.get("type") or "")
    dynamic_id = str(item.get("id_str") or "")
    url = f"https://t.bilibili.com/{dynamic_id}" if dynamic_id else ""

    lines: List[str] = []
    images: List[str] = []

    author = _get_author_name(item)
    title_head = f"{author} - 动态更新：{url}".strip(" -")
    if prefix:
        title_head = f"{prefix}{title_head}"
    lines.append(title_head)

    text = _get_text_desc(item)
    if text:
        lines.append(text)

    if dynamic_type == "DYNAMIC_TYPE_DRAW":
        pics = _get_pictures(item)
        images.extend(pics[:9])
        if not pics and not text:
            lines.append("（无文字内容）")

    elif dynamic_type == "DYNAMIC_TYPE_AV":
        archive = _get_archive(item)
        title = archive.get("title")
        bvid = archive.get("bvid")
        desc = archive.get("desc")
        cover = archive.get("cover")
        if isinstance(title, str) and title:
            lines.append(f"视频：{title}")
        if isinstance(bvid, str) and bvid:
            lines.append(f"https://www.bilibili.com/video/{bvid}")
        if isinstance(desc, str) and desc:
            lines.append(f"简介：{desc}")
        if isinstance(cover, str) and cover:
            images.append(cover)

    elif dynamic_type == "DYNAMIC_TYPE_WORD":
        if not text:
            lines.append("（无文字内容）")

    elif dynamic_type == "DYNAMIC_TYPE_ARTICLE":
        article = _get_article(item)
        title = article.get("title")
        jump_url = article.get("jump_url")
        covers = article.get("covers")
        if isinstance(title, str) and title:
            lines.append(f"专栏：{title}")
        if isinstance(jump_url, str) and jump_url:
            lines.append(jump_url)
        if isinstance(covers, list):
            for c in covers:
                if isinstance(c, str) and c:
                    images.append(c)

    elif dynamic_type == "DYNAMIC_TYPE_FORWARD":
        if not text:
            lines.append("（无文字内容）")
        if depth >= 1:
            return lines, images
        orig = item.get("orig")
        if not isinstance(orig, dict):
            lines.append("原动态：不可见/已删除")
            return lines, images
        orig_author = _get_author_name(orig)
        lines.append(f"转发自：{orig_author}" if orig_author else "转发自：")
        orig_lines, orig_images = _build_message_lines_for_item(
            orig,
            prefix="原动态：",
            depth=depth + 1,
        )
        lines.extend(orig_lines[1:] if orig_lines else [])
        images.extend(orig_images[:9])

    else:
        if not text:
            lines.append(f"（暂不支持的动态类型：{dynamic_type}）")

    return lines, images


def _build_message(lines: Sequence[str], images: Sequence[str]) -> Message:
    msg = Message()
    msg += MessageSegment.text("\n".join([x for x in lines if x]).strip())
    for img in images:
        msg += MessageSegment.image(img)
    return msg


async def _fetch_user_dynamics(uid: str) -> Dict[str, Any]:
    url = "https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space"
    params = {"host_mid": str(uid)}
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://space.bilibili.com/{uid}/dynamic",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://space.bilibili.com",
        "Connection": "keep-alive",
    }

    cookie = global_config.bilibili_cookie
    if cookie:
        headers["Cookie"] = cookie

    client = _http_client
    if client is None:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as tmp_client:
            resp = await tmp_client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    resp = await client.get(url, params=params, headers=headers)
    resp.raise_for_status()
    return resp.json()


def _extract_sorted_items(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = payload.get("data", {}).get("items", [])
    if not isinstance(items, list):
        return []
    only_dicts = [x for x in items if isinstance(x, dict)]

    def _key(it: Dict[str, Any]) -> int:
        v = it.get("id_str")
        try:
            return int(str(v))
        except Exception:
            return 0

    return sorted(only_dicts, key=_key, reverse=True)


def _pick_new_items(sorted_items: Sequence[Dict[str, Any]], known_ids: Sequence[str]) -> List[Dict[str, Any]]:
    known = set(str(x) for x in known_ids)
    new_items: List[Dict[str, Any]] = []
    for it in sorted_items:
        did = it.get("id_str")
        if did is None:
            continue
        did_s = str(did)
        if did_s in known:
            break
        new_items.append(it)
    new_items.reverse()
    return new_items


async def _check_and_send(uid: str, group_id: int, *, items: Sequence[Dict[str, Any]]) -> None:
    if not feature_manager.is_enabled(str(group_id), PLUGIN_NAME):
        return

    known_ids = _load_cache(uid, group_id)
    if not known_ids:
        newest_ids: List[str] = []
        for it in items[:200]:
            did = it.get("id_str")
            if did is None:
                continue
            newest_ids.append(str(did))
        if newest_ids:
            _save_cache(uid, group_id, newest_ids)
        return

    new_items = _pick_new_items(items, known_ids)
    if not new_items:
        return

    bot = get_bot()

    updated_ids = list(known_ids)
    for it in new_items:
        did = it.get("id_str")
        if did is None:
            continue
        did_s = str(did)
        lines, images = _build_message_lines_for_item(it)
        try:
            await bot.send_group_msg(group_id=group_id, message=_build_message(lines, images))
            if did_s in updated_ids:
                updated_ids.remove(did_s)
            updated_ids.insert(0, did_s)
        except Exception as e:
            logger.error(f"B站动态发送失败 uid={uid} group={group_id} id={did_s}: {e}")

    _save_cache(uid, group_id, updated_ids[:400])


def _is_cookie_problem(payload: Dict[str, Any]) -> Optional[str]:
    code = payload.get("code")
    if code in (-352, 403, -403):
        return str(code)
    return None


async def _run_for_uid(uid: str, group_ids: Sequence[int]) -> None:
    try:
        payload = await _fetch_user_dynamics(uid)
    except Exception as e:
        logger.warning(f"B站API请求失败 uid={uid}: {e}")
        return

    cookie_problem = _is_cookie_problem(payload)
    if cookie_problem is not None:
        logger.error(f"⚠️ B站Cookie可能失效 (Code {cookie_problem}) - UID: {uid}")
        return

    items = _extract_sorted_items(payload)
    if not items:
        return

    for gid in group_ids:
        await _check_and_send(uid, int(gid), items=items)


sub_add = on_command(
    "bili_sub",
    aliases={"bili订阅", "订阅bili", "订阅B站"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=5,
    block=True,
)


@sub_add.handle()
async def _handle_sub_add(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    uid = args.extract_plain_text().strip()
    if not uid.isdigit():
        await sub_add.finish("用法：/bili_sub <UID>")
    await Subscription.get_or_create(sub_type="bilibili", sub_id=uid, group_id=event.group_id)
    await sub_add.finish(f"已订阅 UID {uid} 的动态推送。")


sub_del = on_command(
    "bili_unsub",
    aliases={"bili退订", "退订bili", "退订B站"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=5,
    block=True,
)


@sub_del.handle()
async def _handle_sub_del(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    uid = args.extract_plain_text().strip()
    if not uid.isdigit():
        await sub_del.finish("用法：/bili_unsub <UID>")
    deleted = await Subscription.filter(sub_type="bilibili", sub_id=uid, group_id=event.group_id).delete()
    if deleted:
        await sub_del.finish(f"已退订 UID {uid} 的动态推送。")
    await sub_del.finish(f"本群未订阅 UID {uid}。")


sub_ls = on_command(
    "bili_list",
    aliases={"bili列表", "B站订阅列表"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=5,
    block=True,
)


@sub_ls.handle()
async def _handle_sub_ls(bot: Bot, event: GroupMessageEvent):
    subs = await Subscription.filter(sub_type="bilibili", group_id=event.group_id).all()
    if not subs:
        await sub_ls.finish("本群暂无 B 站订阅。")
    uids = sorted({s.sub_id for s in subs})
    await sub_ls.finish("本群 B 站订阅：\n" + "\n".join(uids))


pull_cmd = on_command(
    "bili_pull",
    aliases={"bili拉取", "拉取B站"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=5,
    block=True,
)


@pull_cmd.handle()
async def _handle_pull(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    uid = args.extract_plain_text().strip()
    if not uid.isdigit():
        await pull_cmd.finish("用法：/bili_pull <UID>")
    await _run_for_uid(uid, [event.group_id])
    await pull_cmd.finish("已尝试拉取最新动态。")


stop_cmd = on_regex(r"^B站动态紧急停止$", block=True, permission=SUPERUSER)


@stop_cmd.handle()
async def _handle_stop(bot: Bot, event: PrivateMessageEvent):
    global EMERGENCY_STOP
    EMERGENCY_STOP = True
    logger.error("B站动态监控已紧急停止。")
    await stop_cmd.finish("已紧急停止。")


@scheduler.scheduled_job("interval", seconds=INTERVAL_SECONDS)
async def _bilibili_watch_job():
    if EMERGENCY_STOP:
        return

    try:
        subs = await Subscription.filter(sub_type="bilibili").all()
    except Exception as e:
        logger.error(f"加载 B 站订阅失败: {e}")
        return

    uid_map: Dict[str, List[int]] = {}
    for sub in subs:
        uid_map.setdefault(str(sub.sub_id), []).append(int(sub.group_id))

    for uid, group_ids in uid_map.items():
        await _run_for_uid(uid, group_ids)

