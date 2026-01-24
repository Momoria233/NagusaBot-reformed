import re
import json
from datetime import datetime
import pytz
import os
from pathlib import Path

from typing import Union
from nonebot import logger, on_notice, on_command
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupIncreaseNoticeEvent,
    Message,
    MessageSegment,
    GroupMessageEvent,
    PrivateMessageEvent
)
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .config import Config
from src.common.feature_manager import feature_manager
from src.common.resource import resource_manager

# 注册功能
feature_manager.register("入群欢迎", ": \n新人入群自动欢迎，如果需要更改自动欢迎的内容请使用 /set_welcome 指令。")

assets_dir = resource_manager.get_bundled_asset_dir(__file__)
data_dir = resource_manager.get_data_dir("welcome")
config_file = data_dir / "config.json"

welcome_config = {}

def load_config():
    global welcome_config
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                welcome_config = {int(k): v for k, v in data.items()}
            # Merge legacy defaults for any missing groups
            merged = False
            for gid, msg in Config.welcome_message.items():
                if gid not in welcome_config:
                    welcome_config[gid] = msg
                    merged = True
            if merged:
                save_config()
        except Exception as e:
            logger.error(f"Failed to load welcome config: {e}")
            welcome_config = {}
    else:
        logger.info("Welcome config not found, migrating from legacy Config...")
        welcome_config = Config.welcome_message.copy()
        save_config()

def save_config():
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(welcome_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to save welcome config: {e}")

load_config()

NewWelcome = on_notice()

@NewWelcome.handle()
async def welcoming(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    if not feature_manager.is_enabled(event.group_id, "入群欢迎"):
        await NewWelcome.finish()
    
    group_id = event.group_id
    if group_id not in welcome_config:
        # No welcome message set for this group
        return

    logger.info(f"match group id {group_id}")
    raw_message = welcome_config[group_id]
    
    parts = re.split(r"\{([^}]+)\}", raw_message)
    message_list: list[MessageSegment] = []
    
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part:
                message_list.append(MessageSegment.text(part))
        else:
            match part:
                case "at":
                    message_list.append(MessageSegment.at(event.get_user_id()))
                case str() as string if re.match(r"img:(.*)", string):
                    img_name = re.match(r"img:(.*)", string).group(1)
                    img_path = assets_dir / img_name
                    logger.info(f"Loading image: {img_path}")
                    if img_path.exists():
                        message_list.append(MessageSegment.image(img_path))
                    else:
                        logger.warning(f"Image not found: {img_path}")
                        message_list.append(MessageSegment.text(f"[图片缺失: {img_name}]"))
                case str() as string if re.match(r"file:(.*)", string):
                    file_name = re.match(r"file:(.*)", string).group(1)
                    file_path = assets_dir / file_name
                    if file_path.exists():
                        message_list.append(MessageSegment.file(file_path))
                case str() as string if re.match(r"countdown:(.*)", string):
                    target_date_str = re.match(r"countdown:(.*)", string).group(1).strip()
                    try:
                        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
                        target_date = pytz.timezone("Asia/Shanghai").localize(target_date)
                        now = datetime.now(pytz.timezone("Asia/Shanghai"))
                        delta = target_date - now
                        days_remaining = delta.days
                        if days_remaining >= 0:
                            message_list.append(MessageSegment.text(f"{days_remaining}天"))
                        else:
                            message_list.append(MessageSegment.text("已过期"))
                    except ValueError:
                        logger.error(f"Invalid date format for countdown: {target_date_str}")
                        message_list.append(MessageSegment.text("?"))
                
    await NewWelcome.finish(Message(message_list))

# 新增：设置欢迎语指令
set_welcome_cmd = on_command("set_welcome", aliases={"设置欢迎语"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER)

@set_welcome_cmd.handle()
async def set_welcome_handle(bot: Bot, event: Union[GroupMessageEvent, PrivateMessageEvent], args: Message = CommandArg()):
    raw_args = args.extract_plain_text().strip()
    
    target_group_id = None
    welcome_msg = None

    if isinstance(event, GroupMessageEvent):
        target_group_id = event.group_id
        welcome_msg = raw_args
        if not welcome_msg:
             await set_welcome_cmd.finish("请提供欢迎语内容。支持占位符：{at}, {img:文件名}, {countdown:YYYY-MM-DD}")
    else:
        # Private Message
        parts = raw_args.split(maxsplit=1)
        if len(parts) < 2:
             await set_welcome_cmd.finish("私聊设置请使用格式：/set_welcome <群号> <内容>")
        
        gid_str, content = parts
        if not gid_str.isdigit():
             await set_welcome_cmd.finish("群号必须是数字。")
        
        target_group_id = int(gid_str)
        welcome_msg = content

    welcome_config[target_group_id] = welcome_msg
    save_config()
    await set_welcome_cmd.finish(f"群 {target_group_id} 欢迎语已更新为：\n{welcome_msg}")
