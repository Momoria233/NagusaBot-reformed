# tbd：纯文字类型无法识别转发


import os
import json
import requests
import time
from io import BytesIO
import qrcode
from nonebot import get_bot, require, get_driver, on_command, on_regex
from nonebot.rule import to_me
from nonebot.log import logger
from .config import config
from nonebot.adapters.onebot.v11 import MessageSegment, PrivateMessageEvent, Bot, Message
from nonebot.params import CommandArg
require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

UID_GROUP_MAP = config.bilibili_watch_uid_group_map
INTERVAL = 120

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(os.path.join(BASE_DIR, "cache"), "bilibiliRepost")
os.makedirs(CACHE_DIR, exist_ok=True)

logger.info(f"Bilibili Watch Plugin initialized for UIDs: {list(UID_GROUP_MAP.keys())}, Interval: {INTERVAL} seconds")
assets_dir = os.path.join(BASE_DIR, "assets")

with open(os.path.join(assets_dir, "cookie.json"), "r", encoding="utf-8") as f:
    COOKIE = json.load(f).get("cookie", "")
cookiePath = os.path.join(assets_dir, "cookie.json")

def get_cache_file(uid,group_id):
    return os.path.join(CACHE_DIR, f'dynamic_cache_{uid}_{group_id}.json')

def load_cache(uid,group_id):
    cache_file = get_cache_file(uid,group_id)
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    return []

def save_cache(uid, group_id,cache):
    cache_file = get_cache_file(uid,group_id)
    with open(cache_file, 'w') as f:
        json.dump(cache, f)

def get_user_dynamics(uid):
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}"
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
        "Cookie": COOKIE,
    }
    response = requests.get(url, headers=headers)
    return response.json()

async def check_and_send_for_uid(uid, group_id):
    cache = load_cache(uid,group_id)
    data = get_user_dynamics(uid)
    bot = get_bot()
    if data.get("code") == -352:
        logger.warning(f"B站API请求失败: -352，可能Cookie失效，请更新cookie.txt文件 (UID: {uid})")
        await bot.send_private_msg(
            user_id=2447209382,
            message=f"B站API请求失败: -352，可能Cookie失效，请更新cookie.txt文件 (UID: {uid})"
        )
        return
    if data.get("code") == 403 or data.get("code") == -403:
        logger.warning(f"访问被拒绝，Cookie可能已过期或无效，请更新cookie.txt文件 (UID: {uid})")
        await bot.send_private_msg(
            user_id=2447209382,
            message=f"访问被拒绝，Cookie可能已过期或无效，请更新cookie.txt文件 (UID: {uid})"
        )
        return

    items = data.get("data", {}).get("items")
    if not items:
        logger.warning(f"未获取到动态内容，data中无 items 字段 (UID: {uid})")
        return
    # logger.info(items)
    new_cache = cache.copy()

    if not cache:
        logger.info(f"首次运行，仅缓存当前动态，不推送历史动态。UID: {uid}")
        for item in items:
            dynamic_id = item.get("id_str")
            if dynamic_id:
                new_cache.append(dynamic_id)
        save_cache(uid, group_id,new_cache[-100:])
        return

    for item in items:
        dynamic_id = item.get("id_str")
        if not dynamic_id:
            continue
        if dynamic_id in cache or dynamic_id in new_cache:
            logger.warning(f"动态 {dynamic_id} 已存在于缓存中，跳过推送 (UID: {uid})")
            # 防止本轮重复推送
            continue

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
                orig_desc = (
                    orig.get("modules", {})
                        .get("module_dynamic", {})
                        .get("desc", {})
                        .get("text", "")
                )
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
                if not description and "rich_text_nodes" in desc_obj:
                    description = "".join([node.get("text", "") for node in desc_obj["rich_text_nodes"]])
            msg_list.append(description if description else "无文字内容")

        # 其他类型
        else:
            msg_list.append(f"暂不支持的动态类型：{dynamic_type}")

        try:
            await bot.send_group_msg(group_id=group_id, message="\n".join(msg_list))
        except Exception as e:
            logger.error(f"发送失败: {e}")

        new_cache.append(dynamic_id)
    save_cache(uid,group_id, new_cache[-100:])

update_cookie = on_regex(r"^更新B站Cookie$", block=True)

@update_cookie.handle()
async def handle_update_cookie(bot: Bot, event: PrivateMessageEvent):
    try:
        qrcode_key, qrcode_url = get_qrcode()
        img = qrcode.make(qrcode_url)
        buf = BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        await update_cookie.send(MessageSegment.image(buf))
        time.sleep(30)
        login_url = poll_login(qrcode_key)
        logger.info(f"{qrcode_key}/n{qrcode_url}/n{login_url}")
        if login_url:
            cookies = get_cookies_from_url(login_url)
            cookie_str = save_cookie(cookies)
            await update_cookie.send("登录成功，cookie已保存。")
            await update_cookie.send(f"Cookie:{cookie_str}")
        else:
            await update_cookie.send("二维码过期或用户取消，登录失败。")
    except Exception as e:
        await update_cookie.send(f"发生错误: {str(e)}")

def get_qrcode():
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers).json()
    qrcode_key = resp['data']['qrcode_key']
    qrcode_url = resp['data']['url']
    return qrcode_key, qrcode_url

def poll_login(qrcode_key):
    url = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "qrcode_key": qrcode_key
    }
    for _ in range(60):
        resp = requests.post(url, headers=headers, data=data)
        if resp.status_code != 200:
            return None
        try:
            json_data = resp.json()
        except Exception:
            return None
        if json_data['data']['code'] == 0:
            return json_data['data']['url']
        elif json_data['data']['code'] == 86038:
            return None
        time.sleep(1)
    return None

def get_cookies_from_url(url):
    session = requests.Session()
    session.get(url)
    return session.cookies.get_dict()

def save_cookie(cookies):
    dedeuserid = cookies.get("DedeUserID", "")
    sessdata = cookies.get("SESSDATA", "")
    bili_jct = cookies.get("bili_jct", "")
    cookie_str = f"DedeUserID={dedeuserid};SESSDATA={sessdata};bili_jct={bili_jct}"
    with open(cookiePath, "w", encoding="utf-8") as f:
        json.dump({"cookie": cookie_str}, f, ensure_ascii=False, indent=4)
    return cookie_str

@scheduler.scheduled_job("interval", seconds=INTERVAL)
async def bilibili_watch_job():
    for uid, group_id in UID_GROUP_MAP.items():
        await check_and_send_for_uid(uid, group_id)
