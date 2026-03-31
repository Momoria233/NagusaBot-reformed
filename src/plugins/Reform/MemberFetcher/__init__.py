import csv
import os
from datetime import datetime
from pathlib import Path

from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, PrivateMessageEvent, Message
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER

from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.resource import resource_manager

PLUGIN_NAME = "MemberFetcher"
FEATURE_FETCH = "fetch_members"

permission_manager.register(
    PLUGIN_NAME,
    "群成员爬取",
    features=[
        FeatureSpec(name=FEATURE_FETCH, default_open=True, description="爬取群成员信息")
    ],
    group_customize=False,
)

# Restore on_command to support aliases and arguments
fetch_cmd = on_command("fetch_members", aliases={"爬取群成员", "fetchMember"}, priority=10, block=True)

@fetch_cmd.handle()
async def handle_fetch(bot: Bot, event: PrivateMessageEvent, args: Message = CommandArg()):
    logger.info("starting group member fetch")
    if not isinstance(event, PrivateMessageEvent):
        await fetch_cmd.finish("此命令仅限私聊使用")

    # Determine target group ID
    arg_text = args.extract_plain_text().strip()
    target_group_id = 99610199  # Default target
    
    if arg_text:
        if arg_text.isdigit():
            target_group_id = int(arg_text)
        else:
            await fetch_cmd.finish("请输入有效的群号")

    await fetch_cmd.send(f"开始爬取群 {target_group_id} 的成员信息...")

    # 1. Verify group existence and bot membership
    try:
        group_info = await bot.get_group_info(group_id=target_group_id)
        logger.info(f"Group info: {group_info}")
    except Exception as e:
        await fetch_cmd.finish(f"无法获取群 {target_group_id} 信息，请确认Bot是否在群内。\n错误: {e}")
        return

    # 2. Fetch members
    try:
        member_list = await bot.get_group_member_list(group_id=target_group_id)
        logger.info(f"Fetched {len(member_list) if member_list else 0} members")
    except Exception as e:
        await fetch_cmd.finish(f"获取群成员失败: {e}")
        return

    if not member_list:
        await fetch_cmd.finish(f"未获取到任何成员信息 (Bot可能无权获取或群为空)")
        return

    # Prepare data directory
    data_dir = resource_manager.get_data_dir(PLUGIN_NAME)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"members_{target_group_id}_{timestamp}.csv"
    filepath = data_dir / filename

    # Write to CSV
    try:
        # Only include user_id
        fieldnames = ["user_id"]
        
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for member in member_list:
                # Filter only user_id
                writer.writerow({"user_id": member["user_id"]})
                
        # Send file to user
        await fetch_cmd.send(f"爬取完成，共 {len(member_list)} 名成员。正在上传文件...")
        
        try:
            # Upload file using OneBot API
            await bot.call_api(
                "upload_private_file",
                user_id=event.user_id,
                file=str(filepath.absolute()),
                name=filename
            )
        except Exception as e:
            await fetch_cmd.finish(f"文件上传失败: {e}\n文件保存在本地: {filepath}")
            
    except Exception as e:
        await fetch_cmd.finish(f"处理失败: {e}")
