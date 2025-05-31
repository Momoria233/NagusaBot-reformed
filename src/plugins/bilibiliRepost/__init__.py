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

UID = config.bilibili_watch_uid
INTERVAL = 120
TARGET_GROUP = config.bilibili_watch_target_group

# 新增：定义 cache 目录并确保存在
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(os.path.join(BASE_DIR, "cache"),"bilibiliRepost")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_FILE = os.path.join(CACHE_DIR, f'dynamic_cache_{UID}.json')

logger.info(f"Bilibili Watch Plugin initialized for UID: {UID}, Interval: {INTERVAL} seconds, Target Group: {TARGET_GROUP}")
assets_dir = os.path.join(BASE_DIR, "assets")

# # def load_cookie():
# #     cookie_path = "cookie.txt"  # 路径可按需修改
# #     if not os.path.exists(cookie_path):
# #         return ""
# #     with open(cookie_path, "r", encoding="utf-8") as f:
# #         return f.read().strip()



# COOKIE = load_cookie()
# COOKIE = "DedeUserID=410532721;SESSDATA=bcf2f24f%2C1760058528%2Cbe338%2A42CjCZV6mNnZE5e4ExR7n9ZihmdrGtpau9Uv44-lPB9FCkHOkFKX1csfdndlQGxQCjEQsSVkFEOG1odXNBdE5KbzNxaHpYbEZYQmkzQk1PQ3YwWk95U3YxOXZxRTFEVms2OW9DYVZteHN2WEdGaDFuTHA4SDdNVmNuX29HbWpicXdpSkRBbTBkY2R3IIEC;bili_jct=81d4ad866328f4a238455fb7e4d6b103"
with open(os.path.join(assets_dir, "cookie.json"), "r", encoding="utf-8") as f:
    COOKIE = json.load(f).get("cookie", "")
cookiePath = os.path.join(assets_dir, "cookie.json")



def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return []


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
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

async def check_and_send():
    cache = load_cache()
    data = get_user_dynamics(UID)
    bot = get_bot()
    if data.get("code") == -352:
        logger.warning("B站API请求失败: -352，可能Cookie失效，请更新cookie.txt文件")
        await bot.send_private_msg(
            user_id=2447209382,
            message="B站API请求失败: -352，可能Cookie失效，请更新cookie.txt文件"
        )
        return
    if data.get("code") == 403 or data.get("code") == -403:
        logger.warning("访问被拒绝，Cookie可能已过期或无效，请更新cookie.txt文件")
        await bot.send_private_msg(
            user_id=2447209382,
            message="访问被拒绝，Cookie可能已过期或无效，请更新cookie.txt文件"
        )
        return
    logger.warning(f"API 原始返回内容: {data}")

    items = data.get("data", {}).get("items")
    if not items:
        logger.warning("未获取到动态内容，data中无 items 字段")
        return

    new_cache = cache.copy()

    # 首次运行：只缓存，不推送
    if not cache:
        logger.info("首次运行，仅缓存当前动态，不推送历史动态。")
        for item in items:
            dynamic_id = item.get("id_str")
            if dynamic_id:
                new_cache.append(dynamic_id)
        save_cache(new_cache[-100:])
        return

    for item in items:
        dynamic_id = item.get("id_str")
        if not dynamic_id or dynamic_id in cache:
            continue

        if item.get("type") != "DYNAMIC_TYPE_DRAW":
            continue

        description = (
            item.get("modules", {})
                .get("module_dynamic", {})
                .get("desc", {})
                .get("text", "")
        )
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

        dynamic_url = f"https://t.bilibili.com/{dynamic_id}"

        msg_list = [
            f"图文动态更新：{dynamic_url}",
            f"{description}" if description else "无文字内容"
        ]
        for pic_url in pictures:
            msg_list.append(f"[CQ:image,file={pic_url}]")

        try:
            await bot.send_group_msg(group_id=TARGET_GROUP, message="\n".join(msg_list))
        except Exception as e:
            logger.error(f"发送失败: {e}")

        new_cache.append(dynamic_id)

    save_cache(new_cache[-100:])


update_cookie = on_regex(r"^更新B站Cookie$",block=True)

@update_cookie.handle()
async def handle_update_cookie(bot: Bot , event: PrivateMessageEvent):
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
    for _ in range(60):  # 最多等60秒
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
    await check_and_send()