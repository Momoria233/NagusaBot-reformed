import re
from datetime import datetime
import pytz
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
from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.plugin_config import (
    get_assets_dir,
    get_group_assets_dir,
    get_group_config,
    resolve_asset_value_with_priority,
    update_group_config,
)

PLUGIN_REG_NAME = "legacy-welcome"
PLUGIN_REAL_NAME = "入群欢迎"
FEATURE_WELCOME = "welcome"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[FeatureSpec(name=FEATURE_WELCOME, default_open=True, description="入群欢迎")],
    group_customize=True,
)

assets_dir = get_assets_dir(__file__)
default_config_path = Path(__file__).parent / "config.py"


def _seed_legacy_defaults():
    for gid, msg in Config.welcome_message.items():
        try:
            current = get_group_config(
                PLUGIN_REG_NAME,
                gid,
                default_config_path,
                allow_group_customize=True,
            )
            if current.get("welcome_message"):
                continue
            update_group_config(
                PLUGIN_REG_NAME,
                gid,
                {"welcome_message": msg},
                default_config_path,
                allow_group_customize=True,
            )
        except Exception as e:
            logger.error(f"Failed to seed welcome config for {gid}: {e}")


_seed_legacy_defaults()

NewWelcome = on_notice()

@NewWelcome.handle()
async def welcoming(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    if not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_WELCOME, event.group_id, event.user_id
    ):
        await NewWelcome.finish()
    
    group_id = event.group_id
    config = get_group_config(
        PLUGIN_REG_NAME,
        group_id,
        default_config_path,
        allow_group_customize=True,
    )
    raw_message = config.get("welcome_message")
    if not raw_message:
        return

    logger.info(f"match group id {group_id}")
    group_assets_dir = get_group_assets_dir(PLUGIN_REG_NAME, group_id, create=True)
    
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
                    img_path = resolve_asset_value_with_priority(
                        img_name, assets_dir, group_assets_dir
                    )
                    logger.info(f"Loading image: {img_path}")
                    if img_path is not None:
                        message_list.append(MessageSegment.image(img_path))
                    else:
                        logger.warning(f"Image not found: {img_path}")
                        message_list.append(MessageSegment.text(f"[图片缺失: {img_name}]"))
                case str() as string if re.match(r"file:(.*)", string):
                    file_name = re.match(r"file:(.*)", string).group(1)
                    file_path = resolve_asset_value_with_priority(
                        file_name, assets_dir, group_assets_dir
                    )
                    if file_path is not None:
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

    get_group_assets_dir(PLUGIN_REG_NAME, target_group_id, create=True)
    update_group_config(
        PLUGIN_REG_NAME,
        target_group_id,
        {"welcome_message": welcome_msg},
        default_config_path,
        allow_group_customize=True,
    )
    await set_welcome_cmd.finish(f"群 {target_group_id} 欢迎语已更新为：\n{welcome_msg}")
