import asyncio
from datetime import datetime
import requests
from generator import draw_quote

async def main():
    # 测试头像（使用一个公开头像 URL）
    url = "https://avatars.githubusercontent.com/u/9919?v=4"
    avatar_bytes = requests.get(url).content

    # 测试数据
    nickname = "NagusaBot"
    text = "这是一条测试引用消息。\n希望这一张图片能像 Telegram 的 Quote 一样简洁漂亮。"
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    img = await draw_quote(avatar_bytes, nickname, text, time_str)
    img.show()  # 或者 img.save("test_quote.png")

if __name__ == "__main__":
    asyncio.run(main())
