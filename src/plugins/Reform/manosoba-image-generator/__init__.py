from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, Bot, Event, GroupMessageEvent
from nonebot.typing import T_State
from nonebot.plugin import PluginMetadata
import base64
import os
from src.common.permission_manager import FeatureSpec, permission_manager

PLUGIN_REG_NAME = "manosoba-image-generator"
PLUGIN_REAL_NAME = "魔裁举牌"
FEATURE_MAGIC = "魔裁举牌"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[FeatureSpec(name=FEATURE_MAGIC, default_open=True, description="输入/安安或/举牌 <文字内容> 可以生成安安举牌回复，加入【魔法】可更换为使用魔法时的文本颜色\n输入/赞同/反驳/疑问/伪证 <文字内容> 可以生成游戏中的四种回复")],
    group_customize=True,
)

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

async def generate(type_id: str, arg: Message, color: str | None = None):
    template = get_template_by_id(TEMPLATES, type_id)
    text = arg.extract_plain_text().strip()

    buf = await draw_text_on_template_async(template, text, color or "#000000")
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    return Message(f"[CQ:image,file=base64://{img_base64}]")

generate_img = on_command("举牌", aliases={"安安"}, priority=1)
@generate_img.handle()
async def handle_generate_img(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent):
        if not permission_manager.is_enabled(
            PLUGIN_REG_NAME, FEATURE_MAGIC, event.group_id, event.user_id
        ):
            return

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
    # Check permission inside new_generate if possible, but session object might not have event easily accessible
    # Better to check in each handler.
    result = await generate(type_id, arg)
    await session.finish(result)


generate_img_approve = on_command("赞同", priority=1)
@generate_img_approve.handle()
async def handle_approve(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_MAGIC, event.group_id, event.user_id
    ):
        return
    await new_generate("approve", generate_img_approve, arg)


generate_img_false = on_command("伪证", priority=1)
@generate_img_false.handle()
async def handle_false(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_MAGIC, event.group_id, event.user_id
    ):
        return
    await new_generate("false", generate_img_false, arg)


generate_img_question = on_command("疑问", priority=1)
@generate_img_question.handle()
async def handle_question(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_MAGIC, event.group_id, event.user_id
    ):
        return
    await new_generate("question", generate_img_question, arg)


generate_img_refute = on_command("反驳", priority=1)
@generate_img_refute.handle()
async def handle_refute(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    if isinstance(event, GroupMessageEvent) and not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_MAGIC, event.group_id, event.user_id
    ):
        return
    await new_generate("refute", generate_img_refute, arg)
