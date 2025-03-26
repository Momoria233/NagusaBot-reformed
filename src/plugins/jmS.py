#tbd 下载jm的一个func 写着玩的


from nonebot.rule import to_me
from nonebot.plugin import on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg

# from Utils import jm

jmDown = on_command("jm",rule=to_me(),priority=1,block=True)

@jmDown.handle()
async def download_func(args: Message = CommandArg()):
    if number := args.extract_plain_text():
        await jmDown.finish("")
    else:
        msg = "请输入车牌号"
        await jmDown.finish(message=msg)