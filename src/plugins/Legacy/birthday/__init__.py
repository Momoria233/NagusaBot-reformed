import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import List

import pytz
import requests
from nonebot import get_bot, get_driver, logger, on_command, require
from nonebot.adapters.onebot.v11 import Bot, Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.config import global_config
from src.common.resource import resource_manager

PLUGIN_REG_NAME = "birthday"
PLUGIN_REAL_NAME = "生日播报"
FEATURE_BIRTHDAY = "学生生日播报功能"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[FeatureSpec(name=FEATURE_BIRTHDAY, default_open=True, description="bot会在每天的00:00播报当天学生的生日")],
    group_customize=True,
)

# Configuration
SCHALE_DB_URL = "https://raw.githubusercontent.com/SchaleDB/SchaleDB/main/data/cn/students.json"
data_dir = resource_manager.data_root / "config" / PLUGIN_REG_NAME
data_dir.mkdir(parents=True, exist_ok=True)
data_path = data_dir / "students.json"

async def update_config():
    logger.info("Updating students data...")
    try:
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_running_loop()
            # Use global config proxy if needed, currently direct request
            res = await loop.run_in_executor(executor, requests.get, SCHALE_DB_URL)
        res.raise_for_status()
        
        with open(data_path, "wb") as file:
            file.write(res.content)
        logger.info("Data Updated!")
    except Exception as e:
        logger.error(f"Data update failed: {e}")
        if not data_path.exists():
            logger.error("Cache not found, cannot proceed.")
            return False
        logger.warning("Using cached data.")
    return True

tz = pytz.timezone("Asia/Shanghai")
driver = get_driver()
now = datetime.now(tz)
start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
logger.info(f"Current Start Date : {start_date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')}")

@driver.on_startup
async def init_func():
    # await update_config()
    next_date: datetime = start_date + timedelta(days=1)
    logger.info(f"Next action will occur at {next_date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')}")


def get_birthday(now: datetime) -> List[str]:
    now_mounth: int = now.month
    now_day: int = now.day

    students: List[str] = []
    s_students: set = set()
    
    if not data_path.exists():
        return []

    try:
        with open(data_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as e:
        logger.error(f"Failed to load student data: {e}")
        return []

    for student in data:
        birthday: str = student.get("BirthDay")
        name: str = student.get("PersonalName")
        
        if not birthday or not name:
            continue
            
        if name in s_students:
            continue
        s_students.add(name)
        
        try:
            parts = birthday.split("/")
            month: int = int(parts[0])
            day: int = int(parts[1])
        except (ValueError, IndexError):
            logger.warning(f"Invalid birthday format for {name}: {birthday}")
            continue
            
        if day == now_day and month == now_mounth:
            students.append(name)

    return students


@scheduler.scheduled_job("interval", days=1, start_date=start_date, id="job_birthday")
async def report_birthday():
    now = datetime.now(tz)
    next_date: datetime = now + timedelta(days=1)
    logger.info(f"report_birthday started at: {now.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')}")
    logger.info(f"Next action will be starting in {next_date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')}")

    res = await update_config()
    if not res:
        logger.error("Skip this action due to data update failure")
        return

    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_running_loop()
        students = await loop.run_in_executor(executor, get_birthday, now)
    
    logger.info(f"Today's birthday student: {students}")

    try:
        bot = get_bot()
    except ValueError:
        logger.critical("Bot not found")
        return

    if not students:
        await bot.send_private_msg(user_id=global_config.superuser_id, message="今天没有过生日的学生")
        return

    msg = f"老师，今天是{', '.join(students)}的生日，让我们祝她生日快乐！"

    # Get all groups list from bot
    try:
        group_list = await bot.get_group_list()
    except Exception as e:
        logger.error(f"Failed to get group list: {e}")
        return

    for group in group_list:
        group_id = group["group_id"]
        if permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_BIRTHDAY, group_id, None):
            try:
                await bot.send_group_msg(group_id=group_id, message=msg)
                await asyncio.sleep(0.5) # Avoid rate limit
            except Exception as e:
                logger.error(f"Failed to send birthday msg to {group_id}: {e}")

    # Send to Superuser
    try:
        await bot.send_private_msg(user_id=global_config.superuser_id, message=msg)
    except Exception:
        pass

    logger.info(f"Next action will occur at {next_date.strftime('%a %b %d %Y %H:%M:%S GMT%z (%Z)')}")


debug_command = on_command("debug_birthday", priority=10, permission=SUPERUSER)

@debug_command.handle()
async def debug_command_handler(args: Message = CommandArg()):
    if date := args.extract_plain_text():
        try:
            parts = date.split("/")
            month: int = int(parts[0])
            day: int = int(parts[1])
            now: datetime = datetime.now(tz)
            test_date: datetime = now.replace(month=month, day=day)
        except Exception:
            await debug_command.finish("格式错误，请输入 MM/DD")
            return

        res = await update_config()
        if not res:
            await debug_command.finish("数据更新失败")
            return

        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_running_loop()
            students = await loop.run_in_executor(executor, get_birthday, test_date)
            
        logger.info(f"Debug birthday student: {students}")
        
        if not students:
            await debug_command.finish("该日期没有过生日的学生")

        await debug_command.send(f"老师，今天是{', '.join(students)}的生日，让我们祝她生日快乐！")

    else:
        await debug_command.finish("please enter the date (month/day)")
