"""
NagusaBot 插件模板
将本文件内容复制到新插件的 __init__.py 后即可开始开发。
"""

# NoneBot 基础组件导入
from nonebot import on_command
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
# permission_manager 负责功能开关与群级权限
# resource_manager 负责运行时数据目录
# plugin_config 负责默认配置、群配置覆盖、assets 解析
from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.resource import resource_manager
from src.common.plugin_config import (
    get_assets_dir,
    get_group_assets_dir,
    get_group_config,
    get_group_config_and_assets,
    resolve_asset_value_with_priority,
    update_group_config,
)

# NagusaBot 核心组件（必须导入）
# ==================================================================================
# 1. 注册功能开关与默认配置
# ==================================================================================
# 通过 permission_manager 注册功能开关
# features: 功能名与默认开关
# group_customize: 是否允许群级覆盖
PLUGIN_NAME = "新功能示例"
FEATURE_HELLO = "hello"
permission_manager.register(
    PLUGIN_NAME,
    PLUGIN_NAME,
    features=[FeatureSpec(name=FEATURE_HELLO, default_open=True, description="示例命令")],
    group_customize=True,
)

# default_config.py 与插件代码同级，作为只读默认配置
# 注意：assets 字段只放逻辑文件名，不拼路径
# default_config = {
#     "enabled": True,
#     "welcome_text": "Welcome!",
#     "welcome_image": None,
# }


# ==================================================================================
# 2. 获取资源路径
# ==================================================================================
# 2.1 获取插件自带的静态资源目录（只读，如图片、字体）
# 对应目录：src/plugins/插件名/assets/
# default_config_path 指向默认配置文件
assets_dir = get_assets_dir(__file__)
default_config_path = assets_dir.parent / "default_config.py"

# 2.2 获取运行时数据存储目录（读写，如数据库、生成的图片）
# 对应目录：data/plugins/插件名/
# 建议：传递给 get_data_dir 的名称与插件文件夹名一致
data_dir = resource_manager.get_data_dir("my_new_plugin")


# ==================================================================================
# 3. 编写业务逻辑
# ==================================================================================

# 示例：注册命令 /hello
# 这里演示权限校验、群配置读取、assets 解析与响应输出
hello_cmd = on_command("hello", aliases={"你好"}, priority=10, block=True)
set_welcome_cmd = on_command("set_welcome", priority=10, block=True)

@hello_cmd.handle()
async def handle_hello(bot: Bot, event: Event, args: Message = CommandArg()):
    # 3.1 检查功能开关（仅群聊）
    # event.user_id 用于用户级白/黑名单决策
    if isinstance(event, GroupMessageEvent):
        if not permission_manager.is_enabled(
            PLUGIN_NAME, FEATURE_HELLO, event.group_id, event.user_id
        ):
            # 功能未开启：可直接结束处理或 finish()
            # 注意：finish() 会停止后续插件匹配，return 会让 nonebot 继续尝试其他匹配
            await hello_cmd.finish()
            return

    group_id = event.group_id if isinstance(event, GroupMessageEvent) else None
    # 私聊没有群配置覆盖，直接返回默认配置
    if group_id is None:
        cfg = get_group_config(PLUGIN_NAME, group_id, default_config_path, allow_group_customize=True)
        assets = {}
    else:
        # 群聊同时返回已解析 assets 映射（群 assets 优先）
        cfg, assets = get_group_config_and_assets(
            PLUGIN_NAME,
            group_id,
            default_config_path,
            __file__,
            allow_group_customize=True,
        )
    if isinstance(event, GroupMessageEvent) and not cfg.get("enabled", True):
        await hello_cmd.finish()
        return

    # 3.2 获取参数
    msg = args.extract_plain_text().strip()
    
    # 3.3 使用资源文件（示例）
    # config 中只存逻辑文件名，路径由资产解析自动处理（群 assets 优先）
    # get_group_assets_dir 会在首次访问时创建群 assets 目录
    group_assets_dir = get_group_assets_dir(PLUGIN_NAME, group_id, create=True)
    demo_image_path = resolve_asset_value_with_priority(
        "welcome.png", assets_dir, group_assets_dir
    )
    if demo_image_path and msg == "图片示例":
        await hello_cmd.finish(MessageSegment.image(demo_image_path))
        return
    
    # 3.4 发送回复
    user_id = event.get_user_id()
    text = cfg.get("welcome_text") or f"你好！你的ID是 {user_id}。你发送了：{msg}"
    image_path = assets.get("welcome_image")
    if image_path:
        await hello_cmd.finish(Message([MessageSegment.text(text), MessageSegment.image(image_path)]))
        return
    await hello_cmd.finish(text)


# 简单的 set_welcome 示例
# 写入群级配置，同时确保群 assets 目录存在
@set_welcome_cmd.handle()
async def handle_set_welcome(bot: Bot, event: Event, args: Message = CommandArg(), plain: str = EventPlainText()):
    if not isinstance(event, GroupMessageEvent):
        await set_welcome_cmd.finish("仅支持群聊")
        return
    if not (isinstance(event, GroupMessageEvent) and event.user_id in SUPERUSER):
        await set_welcome_cmd.finish("权限不足")
        return
    new_text = plain.strip()
    if not new_text:
        await set_welcome_cmd.finish("请输入内容")
        return
    get_group_assets_dir(PLUGIN_NAME, event.group_id, create=True)
    cfg = update_group_config(
        PLUGIN_NAME,
        event.group_id,
        {"welcome_text": new_text},
        default_config_path,
        allow_group_customize=True,
    )
    await set_welcome_cmd.finish("已更新")

