from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupIncreaseNoticeEvent  # type: ignore
from nonebot import on_notice
import json

NewWelcome = on_notice()


@NewWelcome.handle()
async def welcoming(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    with open('group_welcome_messages.json', 'r', encoding='utf-8') as f:
        welcome_msg = json.load(f)
    user = event.get_user_id()
    group_id = event.group_id
    at = MessageSegment.at(event.get_user_id())
    msg1 = MessageSegment.text("欢迎")
    if group_id in welcome_msg:
        msg2 = MessageSegment.text(welcome_msg[group_id])
        await NewWelcome.finish(message=Message([msg1, at, msg2]))
    else:
        await NewWelcome.finish()
