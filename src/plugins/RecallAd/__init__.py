import os, json
from datetime import datetime, timedelta, timezone

from nonebot import logger
from nonebot import on_message, on_regex
from nonebot.adapters.onebot.v11 import (
    Bot, MessageEvent, Message, GroupMessageEvent
)
from nonebot.typing import T_State
from nonebot.params import EventMessage

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
revokeRec = os.path.join(assets_dir,"revoke_records.json")
tz = timezone(timedelta(hours=8))
whitelist = [2447209382, 123456789]  # Replace with actual user IDs

with open(revokeRec, "r", encoding="utf-8") as f:
    revoke_record = json.load(f)

def key_str(group_id: int, user_id: int) -> str:
    return f"{group_id}:{user_id}"

def save_records():
    with open(revokeRec, "w", encoding="utf-8") as f:
        json.dump(revoke_record, f, ensure_ascii=False, indent=2)

RecallNotice = on_message(priority=1, block=True)
@RecallNotice.handle()
async def RecallNotice_handle(bot: Bot, event: GroupMessageEvent, state: T_State, message: Message = EventMessage()):
    if not event.reply:
        logger.info("没有引用消息，忽略。")
        return
    group_id = event.group_id
    user_id = event.reply.sender.user_id
    replyusr_id = event.user_id
    key = key_str(group_id, user_id)

    now = datetime.now(tz)
    if replyusr_id not in whitelist or now.hour == 12:
        logger.info("用户不在白名单中或当前时间为12点，忽略。")
        return
    if message.extract_plain_text().strip() != "请注意广告时间":
        if message.extract_plain_text().strip() != "bot撤回一下":
            logger.info("消息内容不符合要求，忽略。")
            return
        else:
            if event.user_id == 2447209382:
                await bot.delete_msg(message_id=event.reply.message_id)
                await RecallNotice.finish("消息已撤回。")
        logger.info("消息内容不符合要求，忽略。")
        return

    try:
        await bot.delete_msg(message_id=event.reply.message_id)
    except Exception as e:
        await RecallNotice.finish(f"撤回失败：{e}")

    # 计时逻辑
    record = revoke_record.get(key, {})
    # 兼容旧数据（int类型）
    if isinstance(record, int):
        count = record + 1
        last_time = None
    else:
        count = record.get("count", 0) + 1
        last_time_str = record.get("last_time")
        last_time = datetime.fromisoformat(last_time_str) if last_time_str else None

    if last_time and (now - last_time) < timedelta(minutes=20):
        await RecallNotice.finish("20分钟内已处理过该用户，无需重复操作。")
        return

    revoke_record[key] = {"count": count, "last_time": now.isoformat()}
    save_records()

    if count == 1:
        await RecallNotice.finish("⚠️本群广告时间为12-13点，第一次违规提醒，消息已被撤回。请注意群规。")
    elif count == 2:
        await bot.set_group_ban(group_id=group_id, user_id=user_id, duration=7 * 24 * 60 * 60)
        await RecallNotice.finish("⚠️本群广告时间为12-13点，这是第二次违规，已被禁言 7 天，请注意群规。")
    elif count == 3:
        await bot.set_group_kick(group_id=group_id, user_id=user_id, reject_add_request=False)
        await RecallNotice.finish("第三次违规发送广告，已移出群聊。")
    else:
        await bot.send_private_msg(user_id=2447209382, message=f"error occured: {count},{key}")