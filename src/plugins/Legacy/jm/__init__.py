from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.params import CommandArg
from nonebot.plugin import on_command
from nonebot.rule import to_me

from .jmdownload import jm_download, jm_init
from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.config import global_config

PLUGIN_REG_NAME = "jm"
PLUGIN_REAL_NAME = "JM"
FEATURE_JM = "jm"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[FeatureSpec(name=FEATURE_JM, default_open=False, description="使用/jm 车牌号 可以让bot下载jm上相应的本子。")],
    group_customize=True,
)

driver = get_driver()

@driver.on_startup
async def init_func():
    logger.info("loading jm config...")
    jm_init()
    logger.info("jm config loaded")


jmDown = on_command("jm", rule=to_me())

@jmDown.handle()
async def download_group(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_JM, event.group_id, event.user_id):
        await jmDown.finish() # Use finish to stop if disabled
        
    reply = MessageSegment.reply(event.message_id)
    at = MessageSegment.at(event.get_user_id())
    
    if number := args.extract_plain_text().strip():
        logger.info(f"downloading jmcode {number}")
        
        # Notify user that download started (optional, but good UX)
        # await jmDown.send(Message([reply, at, MessageSegment.text(" 开始下载，请稍候...")]))
        
        code, msg = await jm_download(number)
        
        if code != 0:
            text = MessageSegment.text(" " + msg)
            await jmDown.finish(message=Message([reply, at, text]))
            
        logger.info(f"Download success: {msg}")
        
        try:
            # msg is the absolute file path string
            await bot.call_api("upload_group_file", group_id=event.group_id, file=msg, name=f"{number}.pdf")
            success_msg = "下载并上传成功"
            text = MessageSegment.text(" " + success_msg)
            await jmDown.finish(message=Message([reply, at, text]))
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            text = MessageSegment.text(f" 上传失败: {str(e)}")
            await jmDown.finish(message=Message([reply, at, text]))

    else:
        msg = "请输入车牌号"
        text = MessageSegment.text(" " + msg)
        await jmDown.finish(message=Message([reply, at, text]))


@jmDown.handle()
async def download_private(bot: Bot, event: PrivateMessageEvent, args: Message = CommandArg()):
    user_id = event.get_user_id()
    
    # Check private permission
    if not global_config.jm_allow_private:
        # If private not allowed globally, check whitelist
        if int(user_id) not in global_config.jm_user_whitelist:
            logger.info(f"User {user_id} not in whitelist and private jm disabled")
            await jmDown.finish("私聊下载功能未开启。")

    reply = MessageSegment.reply(event.message_id)
    
    if number := args.extract_plain_text().strip():
        logger.info(f"downloading jmcode {number}")
        
        code, msg = await jm_download(number)
        
        if code != 0:
            text = MessageSegment.text(" " + msg)
            await jmDown.finish(message=Message([reply, text]))
            
        try:
            await bot.call_api("upload_private_file", user_id=int(user_id), file=msg, name=f"{number}.pdf")
            success_msg = "下载并上传成功"
            text = MessageSegment.text(" " + success_msg)
            await jmDown.finish(message=Message([reply, text]))
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            text = MessageSegment.text(f" 上传失败: {str(e)}")
            await jmDown.finish(message=Message([reply, text]))

    else:
        msg = "请输入车牌号"
        text = MessageSegment.text(" " + msg)
        await jmDown.finish(message=Message([reply, text]))
