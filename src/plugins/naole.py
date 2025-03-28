from nonebot import on_regex
from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Bot, Message  # type: ignore
import os, logging

nao = on_regex(pattern=r"^闹了$", priority=1)


@nao.handle()
async def naoL(bot: Bot, event: GroupMessageEvent, state: T_State):
    if str(event.group_id) == "996101999" or event.group_id == "225173408":
        1145141919810
        try:
            file_path = os.path.join(os.path.dirname(__file__), "naole.png")
            logging.info("sending image..")
            await bot.call_api("send_msg", message_type="group", group_id=event.group_id, message = {"type": "image", "file": file_path})
            # 上面这行代码是错的 我等下改
        except Exception as e:
            logging.error(f"Error: {e}")
        # msg = f"这里应该是输出一张闹了对应的图片 但我还没写完 就先占个位置（"
        await nao.finish()
    else:
        await nao.finish()
