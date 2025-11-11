from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import json

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

async def load_templates(config_path: str = "config.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["templates"]

async def get_template_by_id(templates, template_id="default"):
    for t in templates:
        if t["id"] == template_id:
            return t
    raise ValueError(f"Template '{template_id}' not found")


async def wrap_text(text, font, max_width, draw):

    lines = []
    words = list(text)
    line = ""
    for char in words:
        test_line = line + char
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = char
    if line:
        lines.append(line)
    return "\n".join(lines)


async def draw_text_on_template(template,text: str,color: str):
    img_path = os.path.join(assets_dir, template["path"])
    font_path = os.path.join(assets_dir, template["font_path"])

    img = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(img)

    x, y, w, h = template["text_area"]
    font_size = template["max_font_size"]
    x_offset, y_offset = template["offset"]
    while font_size >= template["min_font_size"]:
        font = ImageFont.truetype(font_path, font_size)
        wrapped_text = await wrap_text(text, font, w, draw)
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        if text_width <= w and text_height <= h:
            break
        font_size -= 2

    text_x = x + (w - text_width) / 2
    text_y = y + (h - text_height) / 2
    
    if "\n" not in wrapped_text:
        text_x -= x_offset
        text_y -= y_offset

    draw.multiline_text(
        (text_x, text_y),
        wrapped_text,
        font=font,
        fill=color,
        align=template.get("align", "center"),
        spacing=4
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
