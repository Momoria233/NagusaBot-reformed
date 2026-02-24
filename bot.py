import os
from datetime import datetime

import nonebot
import pytz
from nonebot import logger
from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter

# Initialize NoneBot first to ensure driver is available for config
nonebot.init()

# Imports that depend on initialized driver/config
from src.common.logger import setup_logger
# from src.common.feature_manager import feature_manager
import src.common.database  # Register Database hooks

# Setup Logger (Files + Global Error Reporting)
setup_logger()

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)

# Sync feature cache on startup
# @driver.on_startup
# async def sync_feature_cache():
#     await feature_manager.sync_cache()

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()