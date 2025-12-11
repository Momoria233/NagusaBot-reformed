from nonebot import on_command, logger
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from src.common.feature_manager import feature_manager

# Register admin feature
feature_manager.register("功能管理", ": \n管理员指令：开启/关闭 [功能名]，查看本群功能。")

# Command: Enable Feature
enable_cmd = on_command("开启", aliases={"enable", "启用"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=5)

@enable_cmd.handle()
async def handle_enable(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    feature_name = args.extract_plain_text().strip()
    if not feature_name:
        await enable_cmd.finish("请输入要开启的功能名称。")
    
    # Check if feature exists
    all_features = feature_manager.config.get("all_features", {})
    if feature_name not in all_features:
        # Fuzzy match or suggestion could be added here
        await enable_cmd.finish(f"未找到功能：{feature_name}。请使用 /help 查看可用功能。")
    
    feature_manager.set_feature(str(event.group_id), feature_name, True)
    logger.info(f"Group {event.group_id} enabled feature {feature_name}")
    await enable_cmd.finish(f"已为本群开启功能：{feature_name}")

# Command: Disable Feature
disable_cmd = on_command("关闭", aliases={"disable", "禁用"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=5)

@disable_cmd.handle()
async def handle_disable(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    feature_name = args.extract_plain_text().strip()
    if not feature_name:
        await disable_cmd.finish("请输入要关闭的功能名称。")
    
    # Check if feature exists
    all_features = feature_manager.config.get("all_features", {})
    if feature_name not in all_features:
        await disable_cmd.finish(f"未找到功能：{feature_name}。")
        
    feature_manager.set_feature(str(event.group_id), feature_name, False)
    logger.info(f"Group {event.group_id} disabled feature {feature_name}")
    await disable_cmd.finish(f"已为本群关闭功能：{feature_name}")

# Command: List Features (Admin view)
list_cmd = on_command("本群功能", aliases={"ls_features"}, permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER, priority=5)

@list_cmd.handle()
async def handle_list(bot: Bot, event: GroupMessageEvent):
    enabled = feature_manager.get_group_features(str(event.group_id))
    all_f = feature_manager.config.get("all_features", {})
    
    msg = "== 本群功能状态 ==\n"
    for f in all_f:
        state = "✅" if f in enabled else "❌"
        msg += f"{state} {f}\n"
        
    await list_cmd.finish(msg)
