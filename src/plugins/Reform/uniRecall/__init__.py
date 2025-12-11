import os, json
from datetime import datetime, timedelta, timezone
import nonebot
from nonebot import logger
from nonebot import on_regex
from nonebot.adapters.onebot.v11 import (
    Bot, MessageEvent, Message, GroupMessageEvent, MessageSegment
)
from nonebot.params import EventPlainText
from src.common.feature_manager import feature_manager
from src.common.resource import resource_manager
from src.common.config import global_config

feature_manager.register("广告撤回", ": \n在群内广告下面回复“请注意广告时间”可以撤回广告，并且加以处罚记录。")
feature_manager.register("自助撤回", ": \n回复自己的消息并发送“bot撤回一下”，让机器人协助撤回（通常用于撤回超时无法自己撤回的消息，前提是bot是管理员）。")

# Data storage: data/plugins/uniRecall/revoke_records.json
data_dir = resource_manager.get_data_dir("uniRecall")
revokeRec = data_dir / "revoke_records.json"
tz = timezone(timedelta(hours=8))

if not revokeRec.exists():
    with open(revokeRec, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

with open(revokeRec, "r", encoding="utf-8") as f:
    revoke_record = json.load(f)


def key_str(group_id: int, user_id: int) -> str:
    return f"{group_id}:{user_id}"

def save_records():
    with open(revokeRec, "w", encoding="utf-8") as f:
        json.dump(revoke_record, f, ensure_ascii=False, indent=2)


RecallTrigger = on_regex(r"^(请注意广告时间|bot撤回一下)$")


@RecallTrigger.handle()
async def recall_trigger(
    bot: Bot,
    event: GroupMessageEvent,
    text: str = EventPlainText()
):

    if not event.reply:
        await RecallTrigger.finish("请回复需要处理的消息。")

    text = text.strip()

    if text == "请注意广告时间":
        await handle_advertisement(bot, event)
        return

    if text == "bot撤回一下":
        await handle_user_recall(bot, event)
        return

async def handle_advertisement(bot: Bot, event: GroupMessageEvent):
    group_id = event.group_id
    if not feature_manager.is_enabled(group_id, "广告撤回"):
        return

    reply_user = event.reply.sender.user_id
    trigger_user = event.user_id
    msg_id = event.reply.message_id

    ad_msg_raw = await bot.get_msg(message_id=msg_id)
    adMsg = ""
    for seg in ad_msg_raw["message"]:
        if seg["type"] == "text":
            adMsg = seg["data"].get("text", "")
            break
        if seg["type"] == "image":
            adMsg = MessageSegment.image(seg["data"]["url"])
            break

    key = key_str(group_id, reply_user)
    now = datetime.now(tz)
    if now.hour == 12:
        logger.info("用户不在白名单中或当前时间为12点，忽略。")
        return
    record = revoke_record.get(key, {})
    if isinstance(record, int):
        count = record + 1
        last_time = None
    else:
        count = record.get("count", 0) + 1
        last_time_str = record.get("last_time")
        last_time = datetime.fromisoformat(last_time_str) if last_time_str else None

    if last_time and (now - last_time) < timedelta(minutes=20):
        LoggingMsg = f"【冷却期广告】\n用户 {reply_user}\n 群 {group_id}\n内容：{adMsg}\n触发人：{trigger_user}\n次数：{count}"
        await bot.send_private_msg(user_id=global_config.superuser_id, message=LoggingMsg)
        if global_config.log_group_id:
            await bot.send_group_msg(group_id=global_config.log_group_id, message=LoggingMsg)
        await RecallTrigger.finish("20分钟内已处理过，无需重复。")
        return

    try:
        await bot.delete_msg(message_id=msg_id)
    except Exception as e:
        await RecallTrigger.finish(f"撤回失败：{e}")

    revoke_record[key] = {"count": count, "last_time": now.isoformat()}
    save_records()

    LoggingMsg = f"用户 {reply_user} 在群 {group_id} 发送了广告，内容为“{adMsg}”\n触发人：{trigger_user}，当前违规次数：{count}。"
    await bot.send_private_msg(user_id=global_config.superuser_id, message=LoggingMsg)
    if global_config.log_group_id:
        await bot.send_group_msg(group_id=global_config.log_group_id, message=LoggingMsg)

    # 处罚逻辑
    if count == 1:
        await RecallTrigger.finish(MessageSegment.at(reply_user)+" ⚠️本群广告时间为12-13点，第一次违规提醒，消息已被撤回。请注意群规。")
    elif count == 2:
        await bot.set_group_ban(group_id=group_id, user_id=reply_user, duration=7*24*3600)
        await RecallTrigger.finish(MessageSegment.at(reply_user)+" ⚠️本群广告时间为12-13点，这是第二次违规，已被禁言 7 天，请注意群规。")
    elif count >= 3:
        await RecallTrigger.finish("此为第三次违规发送广告，可以被移出群聊。")

async def handle_user_recall(bot: Bot, event: GroupMessageEvent):
    if not feature_manager.is_enabled(event.group_id, "自助撤回"):
        return

    reply_user = event.reply.sender.user_id
    if reply_user != event.user_id:
        await RecallTrigger.finish(MessageSegment.at(event.user_id)+" 你只能撤回你自己的消息。")

    try:
        await bot.delete_msg(message_id=event.reply.message_id)
        await RecallTrigger.finish(MessageSegment.at(event.user_id)+" 已撤回。")
    except Exception as e:
        await RecallTrigger.finish(MessageSegment.at(event.user_id)+f" 撤回失败：{e}")
