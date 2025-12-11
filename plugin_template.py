"""
NagusaBot Plugin Template
复制此文件内容到新插件的 __init__.py 中即可快速开始开发。
"""

import os
from pathlib import Path

# NoneBot 基础组件
from nonebot import on_command, on_message, on_notice, logger
from nonebot.params import CommandArg, EventPlainText
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    GroupMessageEvent,
    PrivateMessageEvent,
    Message,
    MessageSegment
)
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State

# NagusaBot 核心组件 (必须导入)
from src.common.feature_manager import feature_manager  # 功能开关管理器
from src.common.resource import resource_manager      # 资源与数据路径管理器
from src.common.config import global_config           # 全局配置

# ==================================================================================
# 1. 注册功能开关
# ==================================================================================
# 第一个参数是功能名称（用于管理员开关），第二个参数是功能描述（用于 /help 显示）
PLUGIN_NAME = "新功能示例"
feature_manager.register(PLUGIN_NAME, ": \n这是一个新功能的示例描述，将在帮助菜单中显示。")


# ==================================================================================
# 2. 获取资源路径
# ==================================================================================
# 2.1 获取插件自带的静态资源目录 (只读，如图片、字体)
# 对应目录：src/plugins/您的插件名/assets/
assets_dir = resource_manager.get_bundled_asset_dir(__file__)

# 2.2 获取运行时数据存储目录 (读写，如数据库、生成的图片)
# 对应目录：data/plugins/您的插件名/
# 注意：传递给 get_data_dir 的名称建议与插件文件夹名一致
data_dir = resource_manager.get_data_dir("my_new_plugin")


# ==================================================================================
# 3. 编写业务逻辑
# ==================================================================================

# 示例：注册一个命令 /hello
hello_cmd = on_command("hello", aliases={"你好"}, priority=10, block=True)

@hello_cmd.handle()
async def handle_hello(bot: Bot, event: Event, args: Message = CommandArg()):
    # 3.1 检查功能开关 (仅针对群聊)
    if isinstance(event, GroupMessageEvent):
        if not feature_manager.is_enabled(event.group_id, PLUGIN_NAME):
            # 如果功能未开启，直接结束处理，或者 finish()
            # 注意：finish() 会停止后续其他插件的匹配，return 会让 nonebot 继续尝试其他匹配
            await hello_cmd.finish()
            return

    # 3.2 获取参数
    msg = args.extract_plain_text().strip()
    
    # 3.3 使用资源文件 (示例)
    # image_path = assets_dir / "welcome.png"
    # if image_path.exists():
    #     await hello_cmd.finish(MessageSegment.image(image_path))
    
    # 3.4 使用全局配置 (示例)
    # superuser = global_config.superuser_id
    
    # 3.5 发送回复
    user_id = event.get_user_id()
    await hello_cmd.finish(f"你好！你的ID是 {user_id}。你发送了：{msg}")

