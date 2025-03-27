from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, Message, MessageSegment, GroupIncreaseNoticeEvent  # type: ignore
from nonebot import on_notice

NewWelcome = on_notice()


@NewWelcome.handle()
async def welcoming(bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    user = event.get_user_id()
    at = MessageSegment.at(event.get_user_id())
    msg1 = MessageSegment.text("欢迎")
    msg2 = MessageSegment.text("老师来到北京BAO游客群！\n请老师先阅读群公告，有问题请私信群管理\n目前北京bao2.0仍未开票，请老师敬请期待，也祝老师在群里玩得愉快！")
    if event.group_id == 225173408:  # 群号记得换
        await NewWelcome.finish(message=Message([msg1, at, msg2]))
