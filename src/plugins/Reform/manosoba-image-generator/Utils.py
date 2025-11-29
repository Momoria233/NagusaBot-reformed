from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import json
from typing import Dict, List, Tuple

assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
config_path = os.path.join(assets_dir, "config.json")

TEMPLATES: List[Dict] = []
_FONT_CACHE: Dict[Tuple[str, int], ImageFont.FreeTypeFont] = {}

def _load_templates_once() -> List[Dict]:
    global TEMPLATES
    if TEMPLATES:
        return TEMPLATES

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Template config not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        TEMPLATES = json.load(f).get("templates", [])

    return TEMPLATES


_load_templates_once()

def get_template_by_id(templates: List[Dict], template_id: str = "default") -> Dict:
    for t in templates:
        if t.get("id") == template_id:
            return t
    raise ValueError(f"Template '{template_id}' not found")

def _get_font(font_path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (font_path, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    full_path = os.path.join(assets_dir, font_path)
    font = ImageFont.truetype(full_path, size)
    _FONT_CACHE[key] = font
    return font

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    if not text:
        return ""
    lines = []
    line = ""
    for ch in text:
        test_line = line + ch
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return "\n".join(lines)

def draw_text_on_template(template: Dict, text: str, color: str = "#000000") -> BytesIO:
    img_path = os.path.join(assets_dir, template["path"])
    font_rel_path = template["font_path"]

    with Image.open(img_path).convert("RGBA") as img:
        draw = ImageDraw.Draw(img)

        x, y, w, h = template["text_area"]
        font_size = template.get("max_font_size", 48)
        min_font_size = template.get("min_font_size", 10)
        x_offset, y_offset = template.get("offset", [0, 0])
        align = template.get("align", "center")

        wrapped_text = ""
        font = None
        while font_size >= min_font_size:
            font = _get_font(font_rel_path, font_size)
            wrapped_text = wrap_text(text, font, w)

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
            align=align,
            spacing=4,
        )

        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return buf

import asyncio

async def draw_text_on_template_async(template: Dict, text: str, color: str = "#000000") -> BytesIO:
    # MODIFIED: move heavy work to thread
    return await asyncio.to_thread(draw_text_on_template, template, text, color)
