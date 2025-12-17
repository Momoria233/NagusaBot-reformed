from io import BytesIO
from typing import Tuple, List, Dict

from PIL import Image, ImageDraw, ImageFont


def load_fonts() -> Tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    candidates = ["msyh.ttc", "msyh.ttf", "simhei.ttf", "simsun.ttc"]
    for name in candidates:
        try:
            name_font = ImageFont.truetype(name, 32)
            text_font = ImageFont.truetype(name, 28)
            time_font = ImageFont.truetype(name, 22)
            return name_font, text_font, time_font
        except Exception:
            continue
    default_font = ImageFont.load_default()
    return default_font, default_font, default_font


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    lines: List[str] = []
    line = ""
    for ch in text:
        candidate = line + ch
        if not line:
            line = ch
            continue
        length = font.getlength(candidate)
        if length <= max_width:
            line = candidate
        else:
            lines.append(line)
            line = ch
    if line:
        lines.append(line)
    if not lines:
        lines = [""]
    return "\n".join(lines)


def draw_quote(
    avatar_bytes: bytes,
    nickname: str,
    text: str,
    time_str: str,
    group_name: str | None = None,
    width: int = 800,
) -> Image.Image:
    avatar = Image.open(BytesIO(avatar_bytes)).convert("RGBA")
    avatar_size = 96
    avatar = avatar.resize((avatar_size, avatar_size))
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    avatar.putalpha(mask)

    font_name, font_text, font_time = load_fonts()

    bg_color = (245, 246, 250, 255)
    card_margin = 40
    card_height_min = 180
    img_height_min = 260
    avatar_size = 96
    avatar_x_offset = 30
    avatar_y_offset = 56
    text_right_padding = 36
    name_color = (20, 23, 26)
    text_color = (55, 60, 63)
    time_color = (133, 144, 160)

    card_x0 = card_margin
    card_y0 = 40
    card_x1 = width - card_margin

    avatar_x = card_x0 + avatar_x_offset
    avatar_y = card_y0 + avatar_y_offset

    text_x = avatar_x + avatar_size + 22
    max_text_width = card_x1 - text_x - text_right_padding

    temp_img = Image.new("RGBA", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    wrapped_text = wrap_text(text, font_text, max_text_width)
    bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=font_text, spacing=4)
    text_height = bbox[3] - bbox[1]

    card_height = max(card_height_min, 40 + avatar_size + text_height)
    img_height = max(img_height_min, card_height + 80)
    card_y1 = card_y0 + card_height

    img = Image.new("RGBA", (width, img_height), bg_color)
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        (card_x0, card_y0, card_x1, card_y1),
        radius=24,
        fill=(255, 255, 255, 255),
    )

    if group_name:
        gn_bbox = font_time.getbbox(group_name)
        gn_w = gn_bbox[2] - gn_bbox[0]
        gn_h = gn_bbox[3] - gn_bbox[1]
        gn_x = card_x0 + 30
        gn_y = card_y0 + 18
        draw.text((gn_x, gn_y), group_name, font=font_time, fill=(140, 145, 150))

    img.paste(avatar, (avatar_x, avatar_y), avatar)

    name_y = avatar_y - 6
    draw.text((text_x, name_y), nickname, font=font_name, fill=name_color)

    text_y = name_y + 42
    draw.multiline_text(
        (text_x, text_y),
        wrapped_text,
        font=font_text,
        fill=text_color,
        spacing=5,
    )

    bbox_time = font_time.getbbox(time_str)
    time_w = bbox_time[2] - bbox_time[0]
    time_h = bbox_time[3] - bbox_time[1]
    time_x = card_x1 - time_w - 40
    time_y = card_y1 - time_h - 24
    draw.text((time_x, time_y), time_str, font=font_time, fill=time_color)

    return img


def draw_chat_log(
    records: List[Dict[str, str]],
    group_name: str | None = None,
    width: int = 800,
) -> Image.Image:
    font_name, font_text, font_time = load_fonts()

    bg_color = (245, 246, 250, 255)
    avatar_size = 72
    card_margin = 32
    inner_spacing = 18
    block_spacing = 20
    name_color = (20, 23, 26)
    text_color = (55, 60, 63)
    time_color = (133, 144, 160)

    temp_img = Image.new("RGBA", (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    blocks = []
    total_height = card_margin * 2

    for rec in records:
        avatar = Image.open(BytesIO(rec["avatar_bytes"])).convert("RGBA")
        avatar = avatar.resize((avatar_size, avatar_size))
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
        avatar.putalpha(mask)

        card_x0 = card_margin
        card_x1 = width - card_margin
        avatar_x = card_x0 + 24
        text_x = avatar_x + avatar_size + 18
        max_text_width = card_x1 - text_x - 30

        wrapped_text = wrap_text(rec["text"], font_text, max_text_width)
        bbox = temp_draw.multiline_textbbox((0, 0), wrapped_text, font=font_text, spacing=4)
        text_height = bbox[3] - bbox[1]

        name_bbox = font_name.getbbox(rec["nickname"])
        name_height = name_bbox[3] - name_bbox[1]
        time_bbox = font_time.getbbox(rec["time_str"])
        time_height = time_bbox[3] - time_bbox[1]

        content_height = 16 + 45 + text_height + 20 + time_height + 20
        block_height = max(avatar_size + 32, content_height)

        blocks.append(
            {
                "avatar": avatar,
                "nickname": rec["nickname"],
                "text": wrapped_text,
                "text_height": text_height,
                "time_str": rec["time_str"],
                "height": block_height,
            }
        )
        total_height += block_height + block_spacing

    img = Image.new("RGBA", (width, total_height), bg_color)
    draw = ImageDraw.Draw(img)

    y = card_margin
    if group_name:
        gn_bbox = font_name.getbbox(group_name)
        gn_h = gn_bbox[3] - gn_bbox[1]
        gx = card_margin
        gy = y - 2
        draw.text((gx, gy), group_name, font=font_name, fill=(140, 145, 150))
        y += gn_h + inner_spacing + 4

    for block in blocks:
        h = block["height"]
        card_x0 = card_margin
        card_y0 = y
        card_x1 = width - card_margin
        card_y1 = card_y0 + h

        draw.rounded_rectangle(
            (card_x0, card_y0, card_x1, card_y1),
            radius=20,
            fill=(255, 255, 255, 255),
        )

        avatar_x = card_x0 + 24
        avatar_y = card_y0 + 16
        img.paste(block["avatar"], (avatar_x, avatar_y), block["avatar"])

        text_x = avatar_x + avatar_size + 18
        name_y = avatar_y
        draw.text((text_x, name_y), block["nickname"], font=font_name, fill=name_color)

        text_y = name_y + 42
        draw.multiline_text(
            (text_x, text_y),
            block["text"],
            font=font_text,
            fill=text_color,
            spacing=5,
        )

        time_str = block["time_str"]
        tb = font_time.getbbox(time_str)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        time_x = card_x1 - tw - 32
        time_y = card_y1 - th - 20
        draw.text((time_x, time_y), time_str, font=font_time, fill=time_color)

        y = card_y1 + block_spacing

    return img
