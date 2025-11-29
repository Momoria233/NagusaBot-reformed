from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, Bot, Event
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
import base64
import os

from .Utils import (
    TEMPLATES,
    get_template_by_id,
    draw_text_on_template_async,
)

__plugin_meta__ = PluginMetadata(
    name="manosoba-reply-generator",
    description="a reply img generator from the game manosoba",
    usage="",
    config=None,
    type="application",
    homepage="https://github.com/Momoria233/manosoba-reply-generator",
    supported_adapters={"~onebot.v11"}
)

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

async def generate(type_id: str, arg: Message, color: str | None = None):
    template = get_template_by_id(TEMPLATES, type_id)
    text = arg.extract_plain_text().strip()

    buf = await draw_text_on_template_async(template, text, color or "#000000")
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    return Message(f"[CQ:image,file=base64://{img_base64}]")

generate_img = on_command("举牌", aliases={"安安"}, priority=1)
@generate_img.handle()
async def handle_generate_img(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    raw_text = arg.extract_plain_text().strip()
    use_color = "【魔法】" in raw_text
    if use_color:
        raw_text = raw_text.replace("【魔法】", "").strip()

    if not raw_text and not use_color:
        await generate_img.finish("参数无效")

    color = "#a08cf9" if use_color else "#000000"
    result = await generate("default", Message(raw_text), color=color)
    await generate_img.finish(result)


async def new_generate(type_id: str, session, arg):
    result = await generate(type_id, arg)
    await session.finish(result)


generate_img_approve = on_command("赞同", priority=1)
@generate_img_approve.handle()
async def handle_approve(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    await new_generate("approve", generate_img_approve, arg)


generate_img_false = on_command("伪证", priority=1)
@generate_img_false.handle()
async def handle_false(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    await new_generate("false", generate_img_false, arg)


generate_img_question = on_command("疑问", priority=1)
@generate_img_question.handle()
async def handle_question(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    await new_generate("question", generate_img_question, arg)


generate_img_refute = on_command("反驳", priority=1)
@generate_img_refute.handle()
async def handle_refute(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    await new_generate("refute", generate_img_refute, arg)
