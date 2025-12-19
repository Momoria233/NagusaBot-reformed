import os, json, asyncio
from datetime import datetime, timedelta, timezone
import nonebot
from nonebot import logger
from nonebot import on_regex
from nonebot import on_message
from nonebot import require, get_bot
from nonebot.adapters.onebot.v11 import (
    Bot, MessageEvent, Message, GroupMessageEvent, MessageSegment
)
from nonebot.params import EventPlainText
from src.common.feature_manager import feature_manager
from src.common.resource import resource_manager
from src.common.config import global_config
from src.common.logger import get_group_name, get_user_display_name
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

feature_manager.register("广告撤回", ": \n在群内广告下面回复“请注意广告时间”可以撤回广告，并且加以处罚记录。")
feature_manager.register("自助撤回", ": \n回复自己的消息并发送“bot撤回一下”，让机器人协助撤回（通常用于撤回超时无法自己撤回的消息，前提是bot是管理员）。")

# Data storage: data/plugins/uniRecall/revoke_records.json
data_dir = resource_manager.get_data_dir("uniRecall")
revokeRec = data_dir / "revoke_records.json"
tz = timezone(timedelta(hours=8))
dailyStats = data_dir / "daily_stats.json"

if not revokeRec.exists():
    with open(revokeRec, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

with open(revokeRec, "r", encoding="utf-8") as f:
    revoke_record = json.load(f)

if not dailyStats.exists():
    with open(dailyStats, "w", encoding="utf-8") as f:
        json.dump({"date": datetime.now(tz).date().isoformat(), "count": 0, "users": []}, f, ensure_ascii=False, indent=2)
with open(dailyStats, "r", encoding="utf-8") as f:
    daily_stats = json.load(f)


def key_str(group_id: int, user_id: int) -> str:
    return f"{group_id}:{user_id}"

def save_records():
    with open(revokeRec, "w", encoding="utf-8") as f:
        json.dump(revoke_record, f, ensure_ascii=False, indent=2)

def save_daily_stats():
    with open(dailyStats, "w", encoding="utf-8") as f:
        json.dump(daily_stats, f, ensure_ascii=False, indent=2)

pending_kick_requests = {}

async def wait_for_kick_reply(key: str):
    fut = asyncio.get_event_loop().create_future()
    pending_kick_requests[key] = fut
    return await fut

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
        gname = await get_group_name(bot, group_id)
        rname = await get_user_display_name(bot, reply_user, group_id)
        tname = await get_user_display_name(bot, trigger_user, group_id)
        LoggingMsg = f"【冷却期广告】\n用户 {rname}({reply_user})\n群 {gname}({group_id})\n内容：{adMsg}\n触发人：{tname}({trigger_user})\n次数：{count}"
        await bot.send_private_msg(user_id=global_config.superuser_id, message=LoggingMsg)
        if trigger_user in getattr(global_config, "uni_recall_trusted_users", set()):
            if getattr(global_config, "backup_group_id", None):
                await bot.send_group_msg(group_id=global_config.backup_group_id, message=LoggingMsg)
        else:
            if getattr(global_config, "log_group_id", None):
                await bot.send_group_msg(group_id=global_config.log_group_id, message=LoggingMsg)
        await RecallTrigger.finish("20分钟内已处理过，无需重复。")
        return

    try:
        await bot.delete_msg(message_id=msg_id)
    except Exception as e:
        await RecallTrigger.finish(f"撤回失败：{e}")

    revoke_record[key] = {"count": count, "last_time": now.isoformat()}
    save_records()

    gname = await get_group_name(bot, group_id)
    rname = await get_user_display_name(bot, reply_user, group_id)
    tname = await get_user_display_name(bot, trigger_user, group_id)
    LoggingMsg = f"用户 {rname}({reply_user}) 在群 {gname}({group_id}) 发送了广告，内容为“{adMsg}”\n触发人：{tname}({trigger_user})，当前违规次数：{count}。"
    await bot.send_private_msg(user_id=global_config.superuser_id, message=LoggingMsg)
    if trigger_user in getattr(global_config, "uni_recall_trusted_users", set()):
        if getattr(global_config, "backup_group_id", None):
            await bot.send_group_msg(group_id=global_config.backup_group_id, message=LoggingMsg)
    else:
        if getattr(global_config, "log_group_id", None):
            await bot.send_group_msg(group_id=global_config.log_group_id, message=LoggingMsg)

    today_iso = now.date().isoformat()
    if daily_stats.get("date") != today_iso:
        daily_stats["date"] = today_iso
        daily_stats["count"] = 0
        daily_stats["users"] = []
    daily_stats["count"] = int(daily_stats.get("count", 0)) + 1
    if reply_user not in set(daily_stats.get("users", [])):
        daily_stats["users"].append(reply_user)
    save_daily_stats()

    # 处罚逻辑
    if count == 1:
        await RecallTrigger.finish(MessageSegment.at(reply_user)+" ⚠️本群广告时间为12-13点，第一次违规提醒，消息已被撤回。请注意群规。")
    elif count == 2:
        await bot.set_group_ban(group_id=group_id, user_id=reply_user, duration=7*24*3600)
        await RecallTrigger.finish(MessageSegment.at(reply_user)+" ⚠️本群广告时间为12-13点，这是第二次违规，已被禁言 7 天，请注意群规。")
    elif count >= 3:
        if not global_config.log_group_id:
            await RecallTrigger.finish("此为第三次违规发送广告，可以被移出群聊。")
        key = key_str(group_id, reply_user)
        gname = await get_group_name(bot, group_id)
        rname = await get_user_display_name(bot, reply_user, group_id)
        tname = await get_user_display_name(bot, trigger_user, group_id)
        LoggingMsg = f"用户 {rname}({reply_user}) 在群 {gname}({group_id}) 第三次违规发送广告，是否踢出？回复“是”则踢出，其他回复默认不踢。内容：{adMsg}\n触发人：{tname}({trigger_user})"
        await bot.send_group_msg(group_id=global_config.log_group_id, message=LoggingMsg)
        try:
            result = await asyncio.wait_for(wait_for_kick_reply(key), timeout=300)
            if result == "是":
                try:
                    await bot.set_group_kick(group_id=group_id, user_id=reply_user, reject_add_request=False)
                    await RecallTrigger.finish(MessageSegment.at(reply_user)+" 已被移出群聊。")
                except Exception as e:
                    await RecallTrigger.finish(f"踢出失败：{e}")
            else:
                await RecallTrigger.finish("已记录第三次违规，未执行踢出。")
        except asyncio.TimeoutError:
            await RecallTrigger.finish("审批超时，未执行踢出。")
        finally:
            pending_kick_requests.pop(key, None)

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

approval_msg = on_message(priority=1)

@approval_msg.handle()
async def handle_approval_msg(bot: Bot, event: GroupMessageEvent):
    if not global_config.log_group_id or event.group_id != global_config.log_group_id:
        return
    msg_text = event.message.extract_plain_text().strip()
    if msg_text not in {"是", "否"}:
        return
    processed = 0
    for key, fut in list(pending_kick_requests.items()):
        if isinstance(fut, asyncio.Future) and not fut.done():
            fut.set_result(msg_text)
            processed += 1
            break
    if processed > 0:
        await approval_msg.finish()

@scheduler.scheduled_job("cron", hour=22, minute=0, id="uniRecall_daily_report")
async def uni_recall_daily_report():
    try:
        bot = get_bot()
    except ValueError:
        return
    if not getattr(global_config, "log_group_id", None):
        return
    date = daily_stats.get("date")
    count = int(daily_stats.get("count", 0))
    users = daily_stats.get("users", [])
    if users:
        names = []
        for u in users:
            name = await get_user_display_name(bot, u)
            names.append(f"{name}({u})")
        users_str = ", ".join(names)
    else:
        users_str = "无"
    msg = f"今日广告撤回统计（{date}）\n撤回次数：{count}\n被撤回用户：{users_str}"
    try:
        await bot.send_group_msg(group_id=global_config.log_group_id, message=msg)
    except Exception:
        pass
    tz_now = datetime.now(tz)
    today_iso = tz_now.date().isoformat()
    daily_stats["date"] = today_iso
    daily_stats["count"] = 0
    daily_stats["users"] = []
    save_daily_stats()
