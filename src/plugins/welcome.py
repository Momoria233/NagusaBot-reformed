from nonebot.typing import T_State
from nonebot.adapters.onebot.v11 import Bot, Message, GroupIncreaseNoticeEvent # type: ignore
from nonebot import on_notice

NewWelcome = on_notice()

@NewWelcome.handle()
async def welcoming (bot: Bot, event: GroupIncreaseNoticeEvent, state: T_State):
    user = event.get_user_id()
    at = "欢迎[CQ:at,qq={}]老师来到北京BAO游客群！\n ".format(user)
    msg = at + '请老师先阅读群公告，有问题请私信群管理\n目前北京bao2.0仍未开票，请老师敬请期待，也祝老师在群里玩得愉快！'
    print(at)
    if event.group_id == 225173408: #群号记得换
        await NewWelcome.finish(message=Message(f'{msg}'))