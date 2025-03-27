from nonebot.rule import to_me
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, MessageSegment, Message # type: ignore
from nonebot.params import CommandArg
from nonebot import get_driver
from nonebot import logger


from .jmdownload import jm_download, jm_init

driver = get_driver()


@driver.on_startup
async def init_func():
    logger.info("loading config...")
    jm_init()
    logger.info("config loaded")


jmDown = on_command("jm", rule=to_me(), priority=1, block=True)


@jmDown.handle()
async def download_func(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    # reply=MessageSegment.reply(event.message_id)
    at = MessageSegment.at(event.get_user_id())
    if number := args.extract_plain_text():
        logger.info(f"downloading jmcode {number}")
        code, msg = await jm_download(number)
        if code != 0:
            text = MessageSegment.text(" " + msg)
            await jmDown.finish(message=Message([at, text]))
        await bot.call_api("upload_group_file", group_id=event.group_id, file=msg, name=f"{number}.pdf")
        msg = "下载成功"
        text = MessageSegment.text(" " + msg)
        await jmDown.finish(message=Message([at, text]))

    else:
        msg = "请输入车牌号"
        text = MessageSegment.text(" " + msg)
        await jmDown.finish(message=Message([at, text]))
