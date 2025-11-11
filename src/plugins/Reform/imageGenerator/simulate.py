from generator import load_templates, get_template_by_id, draw_text_on_template
from PIL import Image, ImageDraw
from io import BytesIO
import os
from PIL import ImageFont
assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

try:
    font = ImageFont.truetype("assets/SourceHanSansSC-VF.otf", 24)
    print("字体加载成功")
except Exception as e:
    print("字体加载失败:", e)

def main():
    templates = load_templates(os.path.join("config.json"))
    template = get_template_by_id(templates, "default")
    test_text = "再无话说 请速速动手"

    # 生成图像（只绘文字）
    img_bytes = draw_text_on_template(template, test_text)

    # 转为 PIL.Image
    img = Image.open(img_bytes)

    # 画出红框辅助线，方便你校准 text_area 坐标
    # img = draw_debug_area(img, template["text_area"])

    # 显示图片（直接弹出预览窗口）
    img.show()

    # 保存输出（可选）
    img.save("output_test.png")

if __name__ == "__main__":
    main()
