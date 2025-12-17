from io import BytesIO
from datetime import datetime
import base64

from typing import Dict, List

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


miq_cmd = on_command("miq", rule=to_me(), priority=5, block=True)
miqtest_cmd = on_command("miqtest", rule=to_me(), priority=5, block=True)

message_history: Dict[int, List[Dict]] = {}

record_msg = on_message(priority=90, block=False)


async def get_avatar_bytes(user_id: int) -> bytes:
    url = f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


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
    history = message_history.get(group_id)
    if history is None:
        history = []
        message_history[group_id] = history

    text_parts = []
    for seg in event.message:
        if seg.type == "text":
            text_parts.append(seg.data.get("text", ""))
    text = "".join(text_parts).strip()
    if not text:
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
        }
    )
    if len(history) > 200:
        history.pop(0)


@miq_cmd.handle()
async def handle_miq(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    reply = getattr(event, "reply", None)
    if reply is None:
        await miq_cmd.finish("请先回复需要生成图片的消息，然后再发送 /miq。")

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
            records: List[Dict[str, str]] = []
            for node in nodes[:50]:
                sender_info = node.get("sender", {}) or {}
                user_id = sender_info.get("user_id")
                nickname = sender_info.get("nickname") or (str(user_id) if user_id is not None else "")
                content = node.get("content") or node.get("message") or []
                text_parts = []
                for seg in content:
                    if seg.get("type") == "text":
                        text_parts.append(seg.get("data", {}).get("text", ""))
                text = "".join(text_parts).strip()
                if not text:
                    text = "[非文本消息]"
                ts = node.get("time")
                if ts:
                    dt = datetime.fromtimestamp(ts)
                else:
                    dt = datetime.now()
                time_str = dt.strftime("%Y-%m-%d %H:%M")
                try:
                    if user_id is not None:
                        avatar_bytes = await get_avatar_bytes(user_id)
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
                try:
                    avatar_bytes = await get_avatar_bytes(user_id)
                except Exception:
                    avatar_bytes = build_placeholder_avatar()
                records.append(
                    {
                        "avatar_bytes": avatar_bytes,
                        "nickname": nickname,
                        "text": text,
                        "time_str": time_str,
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
    text = "".join(text_parts).strip()
    if not text:
        text = "[该消息不包含纯文本内容]"

    msg_detail = await bot.get_msg(message_id=reply.message_id)
    ts = msg_detail.get("time")
    if ts:
        time_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    else:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        avatar_bytes = await get_avatar_bytes(sender_id)
    except Exception:
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

    try:
        avatar_bytes = await get_avatar_bytes(user_id)
    except Exception:
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
