from nonebot import on_command, logger, get_driver
from nonebot.exception import FinishedException
from nonebot.adapters.onebot.v11 import (
    Bot, 
    PrivateMessageEvent, 
    GroupMessageEvent, 
    MessageEvent,
    Message, 
    MessageSegment
)
from nonebot.params import CommandArg
from src.common.feature_manager import feature_manager
from src.common.config import global_config

# Debug Log: Plugin Load
logger.info("Admin Settings Plugin: Loading...")

# Register the command
admin_cmd = on_command("admin", aliases={"settings", "管理"}, priority=5, block=True)

driver = get_driver()

@driver.on_startup
async def startup_sync():
    # Sync feature manager cache on startup
    # We do this here to ensure it runs after DB init
    logger.info("Admin Settings: Syncing feature manager cache...")
    await feature_manager.sync_cache()

@admin_cmd.handle()
async def handle_admin(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    logger.info(f"Admin Settings: Command triggered by user {event.user_id}")
    """
    Admin Settings Management Plugin
    Usage:
    
    Private Chat:
    1. /admin : List groups where user has admin permissions
    2. /admin <group_id> : List feature settings for a group
    3. /admin <group_id> <feature> <on/off> : Toggle a feature
    
    Group Chat:
    1. /admin : List feature settings for CURRENT group
    2. /admin <feature> <on/off> : Toggle a feature for CURRENT group
    """
    arg_str = args.extract_plain_text().strip()
    args_list = arg_str.split()
    user_id = event.user_id
    is_superuser = str(user_id) == str(global_config.superuser_id)

    # ==========================
    # Logic for Private Chat
    # ==========================
    if isinstance(event, PrivateMessageEvent):
        # Case 1: No arguments -> List Admin Groups
        if not args_list:
            await admin_cmd.send("正在获取您管理的群组列表，请稍候...")
            
            try:
                # Get all groups bot is in
                all_groups = await bot.get_group_list()
                admin_groups = []
                
                for group in all_groups:
                    gid = group['group_id']
                    gname = group['group_name']
                    
                    if is_superuser:
                        admin_groups.append(f"{gname} ({gid})")
                        continue
                    
                    try:
                        member_info = await bot.get_group_member_info(group_id=gid, user_id=user_id)
                        role = member_info.get('role', 'member')
                        if role in ['owner', 'admin']:
                            admin_groups.append(f"{gname} ({gid})")
                    except Exception:
                        continue
                
                if not admin_groups:
                    await admin_cmd.finish("您当前没有管理的群组（或Bot未加入您管理的群组）。")
                    
                msg = "您拥有管理权限的群组如下：\n" + "\n".join(admin_groups)
                msg += "\n\n请回复 '/admin <群号>' 查看该群功能设置。"
                await admin_cmd.finish(msg)
                
            except FinishedException:
                raise
            except Exception as e:
                logger.error(f"Error fetching admin groups: {e}")
                await admin_cmd.finish(f"获取群组列表失败: {e}")

        # Common logic for Case 2 & 3 needs group_id
        group_id_str = args_list[0]
        if not group_id_str.isdigit():
            await admin_cmd.finish("群号必须是数字。")
            
        group_id = int(group_id_str)
        
        # Verify permission
        if not is_superuser:
            try:
                member_info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
                if member_info.get('role') not in ['owner', 'admin']:
                    await admin_cmd.finish(f"您在群 {group_id} 没有管理权限。")
            except Exception:
                 await admin_cmd.finish(f"无法获取群 {group_id} 的成员信息，您可能不在该群中。")

        # Case 2: One argument -> List Features for Group
        if len(args_list) == 1:
            await show_group_settings(group_id)
            return

        # Case 3: Three arguments -> Set Feature (/admin <gid> <feature> <on/off>)
        if len(args_list) < 3:
            await admin_cmd.finish("指令格式错误。私聊请使用：/admin <群号> <功能名> <on/off>")
            
        feature_name = args_list[1]
        action = args_list[2]
        await set_group_feature(group_id, feature_name, action)

    # ==========================
    # Logic for Group Chat
    # ==========================
    elif isinstance(event, GroupMessageEvent):
        group_id = event.group_id
        
        # Verify permission in current group
        if not is_superuser:
            sender_role = event.sender.role
            if sender_role not in ['owner', 'admin']:
                # Silently ignore or politely refuse?
                # Usually silent ignore is better to avoid spam, but explicit command deserves reply
                await admin_cmd.finish("只有群主或管理员可以配置Bot功能。")

        # Case 1: No arguments -> List Features for CURRENT Group
        if not args_list:
            await show_group_settings(group_id, is_group_chat=True)
            return

        # Case 2: Two arguments -> Set Feature (/admin <feature> <on/off>)
        if len(args_list) == 2:
            feature_name = args_list[0]
            action = args_list[1]
            await set_group_feature(group_id, feature_name, action)
            return
            
        # Case 3: User tried to use private syntax in group (/admin <gid> ...)
        # We generally discourage this, but if gid matches current group, we can allow it.
        if args_list[0].isdigit() and int(args_list[0]) == group_id:
            if len(args_list) == 1:
                await show_group_settings(group_id, is_group_chat=True)
            elif len(args_list) == 3:
                await set_group_feature(group_id, args_list[1], args_list[2])
            else:
                await admin_cmd.finish("指令格式错误。群内请使用：/admin <功能名> <on/off>")
        else:
            await admin_cmd.finish("群内指令请直接使用：/admin <功能名> <on/off>\n（无需输入群号，仅支持配置本群）")

async def show_group_settings(group_id: int, is_group_chat: bool = False):
    features_status = []
    all_features = feature_manager.features # {name: desc}
    sorted_names = sorted(all_features.keys())
    
    for name in sorted_names:
        desc = all_features[name]
        enabled = feature_manager.is_enabled(str(group_id), name)
        status_icon = "✅" if enabled else "❌"
        features_status.append(f"{status_icon} {name}: {desc}")
        
    if not features_status:
        msg = f"本群暂无已注册的可配置功能。" if is_group_chat else f"群 {group_id} 暂无已注册的可配置功能。"
    else:
        header = f"本群功能配置：" if is_group_chat else f"群 {group_id} 功能配置："
        msg = header + "\n" + "\n".join(features_status)
        if is_group_chat:
            msg += "\n\n修改指令：/admin <功能名> <on/off>"
        else:
            msg += f"\n\n修改指令：/admin {group_id} <功能名> <on/off>"
        
    await admin_cmd.finish(msg)

async def set_group_feature(group_id: int, feature_name: str, action: str):
    action = action.lower()
    if action not in ["on", "off", "enable", "disable", "开启", "关闭", "true", "false"]:
        await admin_cmd.finish("操作只能是 on/off/开启/关闭")
        
    enable_flag = action in ["on", "enable", "开启", "true"]
    
    success = await feature_manager.set_feature(group_id, feature_name, enable_flag)
    
    if success:
        status_str = "开启" if enable_flag else "关闭"
        await admin_cmd.finish(f"已成功{status_str} {feature_name} 功能。")
    else:
        await admin_cmd.finish(f"设置失败，可能是功能名 '{feature_name}' 不存在。")
