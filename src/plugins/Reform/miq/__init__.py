from io import BytesIO
from datetime import datetime
import base64
import asyncio
import hashlib

from typing import Dict, List, Optional

import httpx
from nonebot import on_command, on_message
from nonebot.rule import to_me
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    GroupMessageEvent,
    Message,
)
from nonebot.params import CommandArg

from src.common.feature_manager import feature_manager

from .generator import draw_quote, draw_chat_log


feature_manager.register("miq", ": \n引用消息生成图片。")


# miq_cmd = on_command("miq", rule=to_me(), priority=5, block=True)
miq_cmd = on_command("miq",aliases={"语录"},rule=to_me())
# miqtest_cmd = on_command("miqtest", rule=to_me(), priority=5, block=True)
miqtest_cmd = on_command("miqtest",rule=to_me())

message_history: Dict[int, List[Dict]] = {}

record_msg = on_message()

_AVATAR_FETCH_SEMAPHORE = asyncio.Semaphore(2)
_DEFAULT_AVATAR_MD5S: Optional[set[str]] = None
_DEFAULT_AVATAR_MD5S_LOCK = asyncio.Lock()
_MAX_IMAGES = 9


def _normalize_user_id(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _is_probably_image_bytes(data: bytes) -> bool:
    if not data or len(data) < 64:
        return False
    if data[:2] == b"\xff\xd8":
        return True
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"GIF":
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


async def _get_default_avatar_md5s(client: httpx.AsyncClient) -> set[str]:
    global _DEFAULT_AVATAR_MD5S
    if _DEFAULT_AVATAR_MD5S is not None:
        return _DEFAULT_AVATAR_MD5S
    async with _DEFAULT_AVATAR_MD5S_LOCK:
        if _DEFAULT_AVATAR_MD5S is not None:
            return _DEFAULT_AVATAR_MD5S
        default_md5s: set[str] = set()
        probe_user_id = 0
        probe_urls = [
            f"https://q1.qlogo.cn/g?b=qq&nk={probe_user_id}&s=640",
            f"https://q.qlogo.cn/g?b=qq&nk={probe_user_id}&s=640",
            f"https://q.qlogo.cn/headimg_dl?dst_uin={probe_user_id}&spec=640&img_type=jpg",
            f"https://q.qlogo.cn/headimg_dl?dst_uin={probe_user_id}&spec=640",
        ]
        for u in probe_urls:
            try:
                resp = await client.get(u)
                resp.raise_for_status()
                data = resp.content
                if _is_probably_image_bytes(data):
                    default_md5s.add(hashlib.md5(data).hexdigest())
            except (httpx.HTTPError, asyncio.TimeoutError):
                continue
        _DEFAULT_AVATAR_MD5S = default_md5s
        return default_md5s


async def get_avatar_bytes(
    user_id: int,
    bot: Optional[Bot] = None,
    client: Optional[httpx.AsyncClient] = None,
    default_md5s: Optional[set[str]] = None,
) -> bytes:
    urls = []
    if bot:
        try:
            info = await bot.get_stranger_info(user_id=user_id)
            qq_url = info.get("qlogo") or f"https://q.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640&img_type=jpg"
            if qq_url:
                urls.append(qq_url)
        except Exception:
            print(f"[miq] get_stranger_info failed: user_id={user_id}")

    urls.extend([
        f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640",
        f"https://q.qlogo.cn/g?b=qq&nk={user_id}&s=640",
        f"https://q.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640&img_type=jpg",
        f"https://q2.qlogo.cn/headimg_dl?dst_uin={user_id}&spec=640",
    ])

    async with _AVATAR_FETCH_SEMAPHORE:
        if client is None:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://im.qq.com/",
            }
            timeout = httpx.Timeout(10.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client2:
                default_md5s2 = default_md5s if default_md5s is not None else await _get_default_avatar_md5s(client2)
                return await get_avatar_bytes(user_id, bot=bot, client=client2, default_md5s=default_md5s2)
        if default_md5s is None:
            default_md5s = await _get_default_avatar_md5s(client)

        last_exc: Optional[Exception] = None
        for attempt in range(3):
            saw_too_small = False
            for url in urls:
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.content
                    if not _is_probably_image_bytes(data):
                        continue

                    content_type = (resp.headers.get("content-type") or "").lower()
                    if content_type and "image" not in content_type:
                        continue

                    if len(data) < 256:
                        continue

                    if len(data) < 2048:
                        print(f"[miq] avatar too small: user_id={user_id} url={url} len={len(data)}")
                        saw_too_small = True
                        continue

                    md5 = hashlib.md5(data).hexdigest()
                    if default_md5s and md5 in default_md5s:
                        print(f"[miq] avatar hit default: user_id={user_id} url={url} len={len(data)}")
                        continue

                    return data
                except (httpx.HTTPError, asyncio.TimeoutError) as e:
                    last_exc = e
            if saw_too_small:
                break
            await asyncio.sleep(0.5 * (2 ** attempt))

    if last_exc is not None:
        print(f"[miq] avatar fetch failed: user_id={user_id} exc={type(last_exc).__name__}")
        raise last_exc
    raise RuntimeError("Failed to fetch avatar")


def build_placeholder_avatar() -> bytes:
    from PIL import Image

    img = Image.new("RGB", (100, 100), (200, 200, 200))
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def encode_image_to_base64(img) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@record_msg.handle()
async def record_group_message(event: GroupMessageEvent):
    group_id = event.group_id
    if not feature_manager.is_enabled(group_id, "miq"):
        return
    history = message_history.get(group_id)
    if history is None:
        history = []
        message_history[group_id] = history
    text_parts = []
    images: List[str] = []
    for seg in event.message:
        if seg.type == "text":
            text_parts.append(seg.data.get("text", ""))
        elif seg.type == "image":
            raw = seg.data.get("url") or seg.data.get("file") or ""
            if isinstance(raw, str) and raw:
                if raw.startswith("http") or raw.startswith("base64://"):
                    if len(images) < _MAX_IMAGES:
                        images.append(raw)
        elif seg.type == "face":
            text_parts.append("[表情]")
        elif seg.type == "record":
            text_parts.append("[语音]")
        elif seg.type == "video":
            text_parts.append("[视频]")
    text = "".join(text_parts).strip()
    if not text and not images:
        return
    sender = event.sender
    nickname = sender.card or sender.nickname or str(event.user_id)
    history.append(
        {
            "message_id": event.message_id,
            "user_id": event.user_id,
            "nickname": nickname,
            "text": text,
            "time": event.time,
            "images": images,
        }
    )
    if len(history) > 200:
        history.pop(0)


@miq_cmd.handle()
async def handle_miq(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    reply = getattr(event, "reply", None)

    group_name = None
    group_id = None
    if isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        if not feature_manager.is_enabled(group_id, "miq"):
            return
        try:
            info = await bot.get_group_info(group_id=group_id)
            group_name = info.get("group_name") or str(group_id)
        except Exception:
            group_name = str(group_id)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://im.qq.com/",
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        default_md5s = await _get_default_avatar_md5s(client)
        avatar_mem: Dict[int, bytes] = {}

        async def avatar_for(uid: int) -> bytes:
            cached = avatar_mem.get(uid)
            if cached is not None:
                return cached
            data = await get_avatar_bytes(uid, bot=bot, client=client, default_md5s=default_md5s)
            avatar_mem[uid] = data
            return data
        async def fetch_image_bytes_from_url(url: str) -> Optional[bytes]:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.content
            except Exception:
                return None
        def extract_image_metas_from_segments(segments) -> List[str]:
            metas: List[str] = []
            for seg in segments:
                t = getattr(seg, "type", None) if not isinstance(seg, dict) else seg.get("type")
                d = getattr(seg, "data", None) if not isinstance(seg, dict) else seg.get("data")
                if isinstance(d, dict) and t == "image":
                    raw = d.get("url") or d.get("file") or ""
                    if isinstance(raw, str) and raw and (raw.startswith("http") or raw.startswith("base64://")):
                        if len(metas) < _MAX_IMAGES:
                            metas.append(raw)
            return metas
        async def resolve_images_from_metas(metas: List[str]) -> List[bytes]:
            out: List[bytes] = []
            for m in metas[:_MAX_IMAGES]:
                if m.startswith("base64://"):
                    try:
                        out.append(base64.b64decode(m[len("base64://"):]))
                    except Exception:
                        continue
                elif m.startswith("http"):
                    b = await fetch_image_bytes_from_url(m)
                    if b:
                        out.append(b)
            return out
        async def collect_image_bytes_from_segments(segments) -> List[bytes]:
            metas = extract_image_metas_from_segments(segments)
            return await resolve_images_from_metas(metas)
        arg_text = args.extract_plain_text().strip()
        count = None
        if arg_text.isdigit():
            count = int(arg_text)
            if count < 1:
                count = 1
            if count > 20:
                count = 20
        if reply is None:
            if isinstance(event, GroupMessageEvent) and group_id is not None and isinstance(count, int):
                history = message_history.get(group_id) or []
                if not history:
                    await miq_cmd.finish("暂无可用的消息记录。")
                selected = history[-count:] if count <= len(history) else history
                records: List[Dict[str, str]] = []
                for item in selected:
                    user_id = item["user_id"]
                    nickname = item["nickname"]
                    text = item["text"]
                    dt = datetime.fromtimestamp(item["time"])
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                    imgs_bytes = await resolve_images_from_metas([x for x in item.get("images", []) if isinstance(x, str)])
                    try:
                        avatar_bytes = await avatar_for(user_id)
                    except Exception:
                        avatar_bytes = build_placeholder_avatar()
                    records.append(
                        {
                            "avatar_bytes": avatar_bytes,
                            "nickname": nickname,
                            "text": text,
                            "time_str": time_str,
                            "images": imgs_bytes,
                        }
                    )
                if records:
                    img = draw_chat_log(records, group_name=group_name)
                    img_b64 = encode_image_to_base64(img)
                    cq = f"[CQ:image,file=base64://{img_b64}]"
                    await miq_cmd.finish(Message(cq))
            await miq_cmd.finish("请回复消息或使用 /miq 数字。")

        forward_id = None
        for seg in reply.message:
            if seg.type == "forward":
                forward_id = seg.data.get("id")
                break

        if forward_id:
            try:
                forward = await bot.call_api("get_forward_msg", id=forward_id)
            except Exception:
                forward = None
            nodes = None
            if isinstance(forward, dict):
                if isinstance(forward.get("messages"), list):
                    nodes = forward["messages"]
                elif isinstance(forward.get("forward_msgs"), list):
                    nodes = forward["forward_msgs"]
            if nodes:
                name_to_user_id: Optional[Dict[str, int]] = None
                records: List[Dict[str, str]] = []
                for node in nodes[:50]:
                    sender_info = node.get("sender", {}) or {}
                    user_id = None
                    for candidate in (
                        sender_info.get("user_id"),
                        sender_info.get("uin"),
                        sender_info.get("id"),
                        node.get("user_id"),
                        node.get("sender_id"),
                        node.get("uin"),
                    ):
                        user_id = _normalize_user_id(candidate)
                        if user_id is not None:
                            break
                    nickname = sender_info.get("nickname") or (str(user_id) if user_id is not None else "")
                    if nickname and user_id == 1094950020 and group_id is not None:
                        if name_to_user_id is None:
                            try:
                                members = await bot.get_group_member_list(group_id=group_id)
                                mapping: Dict[str, int] = {}
                                if isinstance(members, list):
                                    for m in members:
                                        uid = _normalize_user_id((m or {}).get("user_id"))
                                        if uid is None:
                                            continue
                                        card = (m or {}).get("card")
                                        nick = (m or {}).get("nickname")
                                        if isinstance(card, str) and card:
                                            mapping.setdefault(card, uid)
                                        if isinstance(nick, str) and nick:
                                            mapping.setdefault(nick, uid)
                                name_to_user_id = mapping
                            except Exception:
                                name_to_user_id = {}
                        resolved = name_to_user_id.get(str(nickname)) if name_to_user_id else None
                        if resolved is not None and resolved != user_id:
                            user_id = resolved
                    content = node.get("content") or node.get("message") or []
                    text_parts = []
                    image_metas: List[str] = []
                    for seg in content:
                        if seg.get("type") == "text":
                            text_parts.append(seg.get("data", {}).get("text", ""))
                        elif seg.get("type") == "image":
                            data = seg.get("data", {}) or {}
                            raw = data.get("url") or data.get("file") or ""
                            if isinstance(raw, str) and raw and (raw.startswith("http") or raw.startswith("base64://")):
                                if len(image_metas) < _MAX_IMAGES:
                                    image_metas.append(raw)
                        elif seg.get("type") == "face":
                            text_parts.append("[表情]")
                        elif seg.get("type") == "record":
                            text_parts.append("[语音]")
                        elif seg.get("type") == "video":
                            text_parts.append("[视频]")
                    text = "".join(text_parts).strip()
                    if not text:
                        text = "[非文本消息]"
                    ts = node.get("time")
                    if ts:
                        dt = datetime.fromtimestamp(ts)
                    else:
                        dt = datetime.now()
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                    imgs_bytes = await resolve_images_from_metas(image_metas)
                    try:
                        if user_id is not None:
                            avatar_bytes = await avatar_for(user_id)
                        else:
                            avatar_bytes = build_placeholder_avatar()
                    except Exception:
                        avatar_bytes = build_placeholder_avatar()
                    records.append(
                        {
                            "avatar_bytes": avatar_bytes,
                            "nickname": nickname,
                            "text": text,
                            "time_str": time_str,
                            "images": imgs_bytes,
                        }
                    )
                if records:
                    img = draw_chat_log(records, group_name=group_name)
                    img_b64 = encode_image_to_base64(img)
                    cq = f"[CQ:image,file=base64://{img_b64}]"
                    await miq_cmd.finish(Message(cq))

        arg_text = args.extract_plain_text().strip()
        count = 1
        if arg_text.isdigit():
            count = int(arg_text)
            if count < 1:
                count = 1
            if count > 20:
                count = 20

        if isinstance(event, GroupMessageEvent) and group_id is not None and count > 1:
            history = message_history.get(group_id) or []
            target_id = reply.message_id
            index = None
            for i, item in enumerate(history):
                if item["message_id"] == target_id:
                    index = i
                    break
            if index is not None:
                start = max(0, index - count + 1)
                selected = history[start : index + 1]
                records: List[Dict[str, str]] = []
                for item in selected:
                    user_id = item["user_id"]
                    nickname = item["nickname"]
                    text = item["text"]
                    dt = datetime.fromtimestamp(item["time"])
                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                    imgs_bytes = await resolve_images_from_metas([x for x in item.get("images", []) if isinstance(x, str)])
                    try:
                        avatar_bytes = await avatar_for(user_id)
                    except Exception:
                        avatar_bytes = build_placeholder_avatar()
                    records.append(
                        {
                            "avatar_bytes": avatar_bytes,
                            "nickname": nickname,
                            "text": text,
                            "time_str": time_str,
                            "images": imgs_bytes,
                        }
                    )
                if records:
                    img = draw_chat_log(records, group_name=group_name)
                    img_b64 = encode_image_to_base64(img)
                    cq = f"[CQ:image,file=base64://{img_b64}]"
                    await miq_cmd.finish(Message(cq))

        sender = reply.sender
        sender_id = sender.user_id
        nickname = sender.card or sender.nickname or str(sender_id)
        display_name = nickname

        text_parts = []
        for seg in reply.message:
            if seg.type == "text":
                text_parts.append(seg.data.get("text", ""))
            elif seg.type == "face":
                text_parts.append("[表情]")
            elif seg.type == "record":
                text_parts.append("[语音]")
            elif seg.type == "video":
                text_parts.append("[视频]")
        text = "".join(text_parts).strip()
        if not text:
            # text = "[该消息不包含纯文本内容]"
            text = ""
        reply_imgs = await collect_image_bytes_from_segments(reply.message)

        msg_detail = await bot.get_msg(message_id=reply.message_id)
        msg_sender = msg_detail.get("sender") or {}
        msg_sender_id = _normalize_user_id(msg_sender.get("user_id"))
        if msg_sender_id is not None:
            sender_id = msg_sender_id

        msg_sender_name = msg_sender.get("card") or msg_sender.get("nickname")
        if msg_sender_name:
            display_name = str(msg_sender_name)
        ts = msg_detail.get("time")
        if ts:
            time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        else:
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            avatar_bytes = await avatar_for(sender_id)
        except Exception:
            avatar_bytes = build_placeholder_avatar()

        img = draw_quote(
            avatar_bytes=avatar_bytes,
            nickname=display_name,
            text=text,
            time_str=time_str,
            group_name=group_name,
            images=reply_imgs,
        )
        img_b64 = encode_image_to_base64(img)
        cq = f"[CQ:image,file=base64://{img_b64}]"
        await miq_cmd.finish(Message(cq))


@miqtest_cmd.handle()
async def handle_miqtest(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    group_name = None
    if isinstance(event, GroupMessageEvent):
        if not feature_manager.is_enabled(event.group_id, "miq"):
            return
        try:
            info = await bot.get_group_info(group_id=event.group_id)
            group_name = info.get("group_name") or str(event.group_id)
        except Exception:
            group_name = str(event.group_id)

    user_id = event.user_id
    sender = getattr(event, "sender", None)
    nickname = None
    if sender is not None:
        nickname = getattr(sender, "card", None) or getattr(sender, "nickname", None)
    if not nickname:
        nickname = str(user_id)
    display_name = nickname

    text = args.extract_plain_text().strip()
    if not text:
        text = "这是一条 miq 测试消息。"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Referer": "https://im.qq.com/",
    }
    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        default_md5s = await _get_default_avatar_md5s(client)
        try:
            avatar_bytes = await get_avatar_bytes(user_id, bot=bot, client=client, default_md5s=default_md5s)
        except Exception as e:
            print(f"[miq] Exception while fetching avatar for user {user_id} occured: {e}")
            avatar_bytes = build_placeholder_avatar()

    img = draw_quote(
        avatar_bytes=avatar_bytes,
        nickname=display_name,
        text=text,
        time_str=time_str,
        group_name=group_name,
    )
    img_b64 = encode_image_to_base64(img)
    cq = f"[CQ:image,file=base64://{img_b64}]"
    await miqtest_cmd.finish(Message(cq))
