from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List
import requests
import asyncio
import pytz
import json
import os
from nonebot.adapters.onebot.v11 import Bot
from nonebot import get_driver
from nonebot import get_bot
from nonebot import require
from nonebot import logger

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from .config import Config


async def update_config():
    logger.info("Updating students data...")
    try:
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(executor, requests.get, Config.data_url)
        res.raise_for_status()
        if not os.path.exists(Config.data_path):
            os.makedirs(os.path.dirname(Config.data_path))
        with open(Config.data_path, "wb") as file:
            file.write(res.content)
        logger.info("Data Updated!")
    except:
        if not os.path.exists(Config.data_path):
            logger.error("Data update failed, cache not found.")
            return False
        logger.warning("Data update failed, using cache instead.")
    return True

start_date = None
driver = get_driver()


@driver.on_startup
async def init_func():
    await update_config()
    global start_date, tz
    tz = pytz.timezone("Asia/Shanghai")
    start_date = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    logger.info(f"Next action will occur at {start_date.strftime("%a %b %d %Y %H:%M:%S GMT%z (%Z)")}")


def get_birthday(now: datetime) -> List[str]:

    now_mounth: int = now.month
    now_day: int = now.day

    students: List[str] = []
    with open(Config.data_path, "r", encoding="utf-8") as file:
        data = json.load(file.read())
    for student in data:
        birthday: str = student["BirthDay"]
        name: str = student["PersonalName"]
        if "（" in name or "）" in name:
            logger.warning(f"Skipping student {name} due to the same student.")
            continue
        try:
            month: int = int(birthday.split("/")[0])
            day: int = int(birthday.split("/")[1])
        except (ValueError, IndexError):
            logger.warning(f"An error occurred while converting {name}'s birthday, so the student will not be counted in the data")
            continue
        if day == now_day and month == now_mounth:
            students.append(name)

    return students


@scheduler.scheduled_job("interval", days=1, start_date=start_date, id="job_birthday")
async def report_birthday():
    global tz
    now: datetime = datetime.now(tz)

    res = await update_config()
    if not res:
        logger.error("Skip this action")
        return

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        students = await loop.run_in_executor(executor, get_birthday, now)
    logger.info(f"Today's birthday girl: {students}")

    bot = get_bot()
    if not isinstance(bot, Bot):
        logger.critical("Bot not found")
        return
    for id in Config.target_group_id:
        bot.send_group_msg(group_id=id, message=f"老师，今天是{students}的生日，让我们祝她生日快乐！")  # TODO 换装去重

    next_date: datetime = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    logger.info(f"Next action will occur at {next_date.strftime("%a %b %d %Y %H:%M:%S GMT%z (%Z)")}")
