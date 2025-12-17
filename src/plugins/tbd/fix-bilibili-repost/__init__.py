# tbd：纯文字类型无法识别转发
# 相同账号转发不同群聊的bug还是未修复

import os
import json
import requests
import time
import asyncio
import random
from io import BytesIO
import qrcode
from nonebot import get_bot, require, get_driver, on_command, on_regex
from nonebot.rule import to_me
from nonebot.log import logger
# Legacy config import removed; plugin now uses DB-backed subscriptions and global config
from nonebot.adapters.onebot.v11 import MessageSegment, PrivateMessageEvent, Bot, Message
from nonebot.params import CommandArg
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from src.common.feature_manager import feature_manager
from src.common.models import Subscription
from src.common.resource import resource_manager
from src.common.config import global_config

from nonebot.exception import FinishedException

feature_manager.register("bilibili动态转发", ": \nbot现在会自动将部分烤肉动态转发到群里。")

# Memory cache for deduplication in current session
# Format: {group_id: {dynamic_id, ...}}
SENT_DYNAMICS_CACHE = {}

global EMERGENCY_STOP
# UID_GROUP_MAP is now deprecated, will load from DB
INTERVAL = 120
EMERGENCY_STOP = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# CACHE_DIR = os.path.join(os.path.join(BASE_DIR, "cache"), "bilibiliRepost")
CACHE_DIR = resource_manager.get_data_dir("bilibiliRepost")

logger.info(f"Bilibili Watch Plugin initialized. Interval: {INTERVAL} seconds")
# assets_dir = os.path.join(BASE_DIR, "assets")

def get_bilibili_cookie() -> str:
    return global_config.bilibili_cookie or ""

def load_cache(uid,group_id):
    cache_file = os.path.join(CACHE_DIR, f'dynamic_cache_{uid}_{group_id}.json')
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return []

def save_cache(uid, group_id,cache):
    cache_file = os.path.join(CACHE_DIR, f'dynamic_cache_{uid}_{group_id}.json')
    with open(cache_file, 'w') as f:
        json.dump(cache, f)

def get_user_dynamics(uid):
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}"
    cookie = get_bilibili_cookie()
    
    # Debug logging for cookie status
    if not cookie:
        logger.warning(f"Bilibili Cookie未加载! UID: {uid}")
    else:
        logger.info(f"Bilibili Cookie已加载 (长度: {len(cookie)}) UID: {uid}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Referer": f"https://space.bilibili.com/{uid}/dynamic",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Origin": "https://space.bilibili.com",
        "Connection": "keep-alive",
    }
    
    if cookie:
        headers["Cookie"] = cookie.strip()

    try:
        # Log actual request details for comparison with script
        # logger.info(f"Preparing request for UID {uid}")
        time.sleep(random.uniform(5, 10))
        
        response = requests.get(url, headers=headers, timeout=15)
        
        # Debug: Log what actually went out
        # logger.info(f"Sent Headers: {response.request.headers}")
        
        # Check status code first
        if response.status_code != 200:
            logger.warning(f"Bilibili API Status Code: {response.status_code} (UID: {uid})")
            # logger.warning(f"Sent Headers: {response.request.headers}")
            
        try:
            data = response.json()
        except json.JSONDecodeError:
            logger.error(f"Bilibili Response is not JSON! Code: {response.status_code}")
            logger.error(f"Response Preview: {response.text[:200]}")
            return {"code": None, "message": f"Not JSON (Status: {response.status_code})", "data": None}
            
    except Exception as e:
        return {"code": None, "message": str(e), "data": None}
    return data

async def check_and_send_for_uid(uid, group_id):
    if not feature_manager.is_enabled(group_id, "bilibili动态转发"):
        return

    cache = load_cache(uid, group_id)
    logger.info(f"cache: {cache}")
    data = get_user_dynamics(uid)
    bot = get_bot()
    
    code = data.get("code")
    message = data.get("message")

    if code != 0:
        logger.warning(f"B站API返回异常 code={code} message={message} (UID: {uid})")
        if code == -352:
            logger.error(f"⚠️ B站Cookie可能失效 (Code -352) - UID: {uid}")
        if code == 403 or code == -403:
            logger.error(f"⚠️ B站Cookie可能失效 (Code 403) - UID: {uid}")
        return

    data_obj = data.get("data")
    items = None
    if isinstance(data_obj, dict):
        items = data_obj.get("items")
        if items is None:
            for k in ("list", "cards"):
                if k in data_obj:
                    items = data_obj.get(k)
                    break

    if not isinstance(items, list) or len(items) == 0:
        data_keys = list(data_obj.keys()) if isinstance(data_obj, dict) else None
        logger.warning(
            f"未获取到动态内容 items为空或字段不存在 (UID: {uid}) code={code} message={message} data_keys={data_keys}"
        )
        return

    # 按时间排序items(假设id_str可以用于排序,因为B站动态ID是递增的)
    sorted_items = sorted(items, key=lambda x: x.get("id_str", "0"), reverse=True)
    
    # 首次运行处理
    if not cache:
        logger.info(f"首次运行，仅缓存最新动态，不推送历史动态。UID: {uid}")
        new_cache = []
        for item in sorted_items[:100]:  # 只缓存最新的100条
            dynamic_id = item.get("id_str")
            if dynamic_id:
                new_cache.append(dynamic_id)
        save_cache(uid, group_id, new_cache)
        return

    # 获取最新的动态ID用于比对
    latest_cached_id = str(cache[0]) if cache else "0"
    
    # 保持现有缓存并准备更新
    new_cache = cache.copy()  # 复制现有缓存而不是创建空列表

    # 处理新动态
    new_dynamics = []
    
    # Init memory cache for this group if not exists
    if group_id not in SENT_DYNAMICS_CACHE:
        SENT_DYNAMICS_CACHE[group_id] = set()
        # Pre-fill with existing file cache to avoid re-sending on restart if file is fresh
        for cid in cache:
            SENT_DYNAMICS_CACHE[group_id].add(str(cid))

    for item in sorted_items:
        dynamic_id = str(item.get("id_str"))
        if not dynamic_id:
            continue
            
        # 如果当前动态ID小于等于最新缓存的ID,说明后面都是旧动态,可以跳出循环
        # 使用int转换确保数字比较正确 (B站ID是纯数字字符串)
        try:
            if int(dynamic_id) <= int(latest_cached_id):
                break
        except ValueError:
            # Fallback to string comparison if ID is not int (unlikely for Bilibili)
            if dynamic_id <= latest_cached_id:
                break
        
        # Memory Deduplication Check
        if dynamic_id in SENT_DYNAMICS_CACHE[group_id]:
            continue

        new_dynamics.append(item)

    # 倒序处理,确保最新的动态最后发送
    for item in reversed(new_dynamics):
        dynamic_id = item.get("id_str")
        
        # 动态处理代码保持不变
        dynamic_type = item.get("type")
        author_name = (
            item.get("modules", {})
                .get("module_author", {})
                .get("name", "")
        )
        dynamic_url = f"https://t.bilibili.com/{dynamic_id}"
        msg_list = [f"{author_name} - 动态更新：{dynamic_url}"]

        # 图文动态
        if dynamic_type == "DYNAMIC_TYPE_DRAW":
            description = (
                item.get("modules", {})
                    .get("module_dynamic", {})
                    .get("desc", {})
                    .get("text", "")
            )
            msg_list.append(description if description else "无文字内容")
            pictures = []
            pic_items = (
                item.get("modules", {})
                    .get("module_dynamic", {})
                    .get("major", {})
                    .get("draw", {})
                    .get("items", [])
            )
            for pic in pic_items:
                if "src" in pic:
                    pictures.append(pic["src"])
            for pic_url in pictures:
                msg_list.append(f"[CQ:image,file={pic_url}]")
            if not pictures:
                msg_list.append("无图片")

        # 视频动态
        elif dynamic_type == "DYNAMIC_TYPE_AV":
            archive = (
                item.get("modules", {})
                    .get("module_dynamic", {})
                    .get("major", {})
                    .get("archive", {})
            )
            title = archive.get("title", "")
            bvid = archive.get("bvid", "")
            desc = archive.get("desc", "")
            cover = archive.get("cover", "")
            video_url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""
            msg_list.append(f"视频：{title}\n{video_url}")
            if desc:
                msg_list.append(f"简介：{desc}")
            if cover:
                msg_list.append(f"[CQ:image,file={cover}]")

        # 转发动态
        elif dynamic_type == "DYNAMIC_TYPE_FORWARD":
            desc = (
                item.get("modules", {})
                    .get("module_dynamic", {})
                    .get("desc", {})
                    .get("text", "")
            )
            msg_list.append(desc if desc else "无文字内容")
            orig = item.get("orig")
            if orig:
                orig_author = (
                    orig.get("modules", {})
                        .get("module_author", {})
                        .get("name", "")
                )
                orig_type = orig.get("type")
                orig_url = f"https://t.bilibili.com/{orig.get('id_str', '')}"
                msg_list.append(f"转发自：{orig_author}\n{orig_url}")
                # 展示原动态内容
                orig_desc_obj = (
                    orig.get("modules", {})
                        .get("module_dynamic", {})
                        .get("desc")
                )
                orig_desc = ""
                if orig_desc_obj and isinstance(orig_desc_obj, dict):
                    orig_desc = orig_desc_obj.get("text", "")
                if orig_desc:
                    msg_list.append(f"原动态内容：{orig_desc}")
                # 视频
                orig_archive = (
                    orig.get("modules", {})
                        .get("module_dynamic", {})
                        .get("major", {})
                        .get("archive", {})
                )
                if orig_archive:
                    orig_title = orig_archive.get("title", "")
                    orig_bvid = orig_archive.get("bvid", "")
                    orig_cover = orig_archive.get("cover", "")
                    orig_video_url = f"https://www.bilibili.com/video/{orig_bvid}" if orig_bvid else ""
                    msg_list.append(f"原视频：{orig_title}\n{orig_video_url}")
                    if orig_cover:
                        msg_list.append(f"[CQ:image,file={orig_cover}]")
                # 图文
                orig_draw = (
                    orig.get("modules", {})
                        .get("module_dynamic", {})
                        .get("major", {})
                        .get("draw", {})
                        .get("items", [])
                )
                for pic in orig_draw:
                    if "src" in pic:
                        msg_list.append(f"[CQ:image,file={pic['src']}]")

        # 纯文字动态
        elif dynamic_type == "RICH_TEXT_NODE_TYPE_TEXT":
            desc_obj = (
                item.get("modules", {})
                    .get("module_dynamic", {})
                    .get("desc")
            )
            description = ""
            if desc_obj and isinstance(desc_obj, dict):
                description = desc_obj.get("text", "")
            msg_list.append(description if description else "无文字内容")

        # 其他类型
        else:
            msg_list.append(f"暂不支持的动态类型：{dynamic_type}")
            try:
                await bot.send_private_msg(user_id=global_config.superuser_id, message="\n".join(msg_list))
            except Exception:
                logger.error("Failed to notify superuser for unsupported dynamic type")
            return

        try:
            await bot.send_group_msg(group_id=group_id, message="\n".join(msg_list))
            # 发送成功后将新动态ID添加到缓存开头
            if dynamic_id not in new_cache:
                new_cache.insert(0, dynamic_id)
            # Update memory cache
            SENT_DYNAMICS_CACHE[group_id].add(dynamic_id)
        except Exception as e:
            logger.error(f"发送失败: {e}")

    # 保存更新后的缓存(保持最多100条)
    if new_cache != cache:  # 只有当缓存发生变化时才保存
        save_cache(uid, group_id, new_cache[:100])

EmergencyStop = on_regex(r"^B站动态紧急停止$", block=True)
@EmergencyStop.handle()
async def handle_emergency_stop(bot: Bot, event: PrivateMessageEvent):
    global EMERGENCY_STOP
    EMERGENCY_STOP = True
    logger.error("Bilibili动态监控已紧急停止。")
    await EmergencyStop.finish()



@scheduler.scheduled_job("interval", seconds=INTERVAL)
async def bilibili_watch_job():
    if EMERGENCY_STOP:
        logger.error("Bilibili动态监控已紧急停止。")
        return
        
    # Load subscriptions from DB
    try:
        subs = await Subscription.filter(sub_type="bilibili").all()
    except Exception as e:
        logger.error(f"Failed to load subscriptions: {e}")
        return

    # Group by UID to avoid duplicate requests
    # {uid: [group_id, ...]}
    uid_map = {}
    for sub in subs:
        uid = sub.sub_id
        if uid not in uid_map:
            uid_map[uid] = []
        uid_map[uid].append(sub.group_id)

    # Fallback: if no subscriptions present, try legacy config mapping
    if not uid_map:
        try:
            from .config import config as legacy_cfg
            for uid, group_id in legacy_cfg.bilibili_watch_uid_group_map.items():
                await check_and_send_for_uid(uid, group_id)
        except Exception:
            pass

    for uid, group_ids in uid_map.items():
        # Optimization: Fetch once, send to multiple groups
        # But check_and_send_for_uid currently handles one group.
        # For now, iterate groups to keep logic simple, or refactor check_and_send_for_uid.
        # Given the existing structure, check_and_send_for_uid relies on per-group cache.
        # So we just iterate.
        for group_id in group_ids:
            await check_and_send_for_uid(uid, group_id)

reload_cmd = on_command("bilibiliReload", aliases={"手动刷新B站"}, priority=5, block=True)

@reload_cmd.handle()
async def handle_reload(bot: Bot):
    await reload_cmd.send("开始手动刷新B站动态...")
    try:
        await bilibili_watch_job()
        await reload_cmd.finish("B站动态刷新完成。")
    except FinishedException:
        pass
    except Exception as e:
        logger.error(f"Manual reload failed: {e}")
        await reload_cmd.finish(f"刷新失败: {e}")

