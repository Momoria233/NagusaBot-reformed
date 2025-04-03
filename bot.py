import os
from datetime import datetime

import nonebot
import pytz
from nonebot import logger
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

if not os.path.exists("./logs/") and os.path.isdir("./logs/"):
    os.mkdir("./logs/")

logger.add(f'./logs/{datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d_%H-%M-%S")}.log', level="DEBUG")
logger.add(f'./logs/{datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d_%H-%M-%S")}.error', level="ERROR")
nonebot.init()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
