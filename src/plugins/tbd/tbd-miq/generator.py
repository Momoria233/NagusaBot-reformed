from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps
import textwrap
import os
from src.common.resource import resource_manager

assets_dir = resource_manager.get_bundled_asset_dir(__file__)

async def draw_quote(
    avatar_bytes: bytes,
    nickname: str,
    text: str,
    time_str: str,
    width: int = 800,
) -> Image.Image:
    """
    生成 Telegram 风格的 Quote 图片
    """

    # 加载头像并裁剪为圆形
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((100, 100))
    mask = Image.new("L", (100, 100), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, 100, 100), fill=255)
    avatar.putalpha(mask)

    # 文字部分参数
    font_path = assets_dir / "SourceHanSansSC-VF.otf"  # 可改为你系统的字体
    font_name = ImageFont.truetype(font_path, 36)
    font_text = ImageFont.truetype(font_path, 32)
    font_time = ImageFont.truetype(font_path, 26)

    # 计算文字换行
    max_text_width = width - 200
    wrapped_text = textwrap.fill(text, width=32)

    # 创建画布
    card_margin = 40
    text_height = 0
    for line in wrapped_text.split("\n"):
        text_height += font_text.getbbox(line)[3] - font_text.getbbox(line)[1] + 8
    card_height = max(180, text_height + 140)
    img = Image.new("RGBA", (width, card_height + 80), (245, 245, 245, 255))
    draw = ImageDraw.Draw(img)

    # 绘制白色卡片带圆角阴影
    shadow_offset = 8
    card = Image.new("RGBA", (width - 2 * card_margin, card_height), (255, 255, 255, 255))
    shadow = Image.new("RGBA", (width - 2 * card_margin, card_height), (0, 0, 0, 80))
    img.paste(shadow, (card_margin + shadow_offset, 40 + shadow_offset), shadow)
    img.paste(card, (card_margin, 40))

    # 绘制头像
    img.paste(avatar, (card_margin + 30, 60), avatar)

    # 绘制文字
    text_x = card_margin + 150
    text_y = 70
    draw.text((text_x, text_y), nickname, font=font_name, fill=(33, 33, 33))
    text_y += 50

    draw.multiline_text(
        (text_x, text_y),
        wrapped_text,
        font=font_text,
        fill=(50, 50, 50),
        spacing=8
    )

    # 绘制时间
    bbox = draw.textbbox((0, 0), time_str, font=font_time)
    time_w = bbox[2] - bbox[0]
    time_h = bbox[3] - bbox[1]
    draw.text(
        (width - card_margin - time_w - 30, card_height + 60 - time_h),
        time_str,
        font=font_time,
        fill=(130, 130, 130)
    )

    return img
