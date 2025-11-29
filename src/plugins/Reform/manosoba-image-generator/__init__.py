from nonebot import on_command
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message, Bot, Event
from nonebot.typing import T_State
from .generator import load_templates, get_template_by_id, draw_text_on_template
import os,base64

generate_img = on_command("举牌", aliases={"安安"}, priority=1)

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

@generate_img.handle()
async def handle_first_receive(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    templates = await load_templates(os.path.join(assets_dir, "config.json"))
    template = await get_template_by_id(templates, "default")
    raw_text = arg.extract_plain_text().strip()
    
    use_color = False
    if "【魔法】" in raw_text:
        use_color = True
        raw_text = raw_text.replace("【魔法】", "").strip()
    if "提拉米苏炖土豆" in raw_text:
        await generate_img.finish("不要提拉米苏炖土豆！")
    text = raw_text
    if not text and not use_color:
        await generate_img.finish("参数无效")
    
    if use_color:
        buf = await draw_text_on_template(template,text, color="#a08cf9")
    else:
        buf = await draw_text_on_template(template,text,color="#000000")
    #except Exception as e:
     #   await generate_img.finish(f"生成图片失败：{e}")
    
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    
    await generate_img.finish(Message(f"[CQ:image,file=base64://{img_base64}]"))

async def generate_img_resp(type, arg):
    templates = await load_templates(os.path.join(assets_dir, "config.json"))
    template = await get_template_by_id(templates,type)
    raw_text = arg.extract_plain_text().strip()
    buf = await draw_text_on_template(template,raw_text,color="#2a2320")
    return buf


generate_img_approve = on_command("赞同",priority=1)
@generate_img_approve.handle()
async def handle_approve(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    buf = await generate_img_resp("approve", arg)
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    await generate_img_approve.finish(Message(f"[CQ:image,file=base64://{img_base64}]"))

generate_img_false = on_command("伪证",priority=1)
@generate_img_false.handle()
async def handle_false(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    buf = await generate_img_resp("false", arg)
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    await generate_img_false.finish(Message(f"[CQ:image,file=base64://{img_base64}]"))

generate_img_question = on_command("疑问",priority=1)
@generate_img_question.handle()
async def handle_question(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    buf = await generate_img_resp("question", arg)
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    await generate_img_question.finish(Message(f"[CQ:image,file=base64://{img_base64}]"))

generate_img_refute = on_command("反驳",priority=1)
@generate_img_refute.handle()
async def handle_refute(bot: Bot, event: Event, state: T_State, arg: Message = CommandArg()):
    buf = await generate_img_resp("refute", arg)
    img_base64 = base64.b64encode(buf.getvalue()).decode()
    await generate_img_refute.finish(Message(f"[CQ:image,file=base64://{img_base64}]"))