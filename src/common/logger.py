import sys
from datetime import datetime
import pytz
from nonebot import logger, get_bot
from nonebot.exception import FinishedException
from src.common.config import global_config

async def error_report_sink(message):
    """
    Loguru sink that sends error logs to the Superuser.
    """
    record = message.record
    exception = record["exception"]
    
    # Filter out non-critical exceptions
    if exception:
        exc_type = exception.type
        # Ignore FinishedException (Control flow)
        if issubclass(exc_type, FinishedException):
            return

    # Format the error message
    err_msg = f"⚠️ [Error Report]\n{record['message']}\n"
    if exception:
        err_msg += f"{exception.type.__name__}: {exception.value}"

    try:
        bot = get_bot()
        # Use config for Superuser ID
        await bot.send_private_msg(user_id=global_config.superuser_id, message=err_msg)
    except Exception:
        pass

def setup_logger():
    """
    Configure Loguru logger with file output and admin reporting.
    """
    # Create logs directory
    import os
    if not os.path.exists("./logs"):
        os.makedirs("./logs")

    timestamp = datetime.now(pytz.timezone("Asia/Shanghai")).strftime("%Y-%m-%d_%H-%M-%S")
    
    # File Sinks
    logger.add(f'./logs/{timestamp}.log', level="DEBUG", rotation="10 MB")
    logger.add(f'./logs/{timestamp}.error', level="ERROR", rotation="10 MB")
    
    # Admin Report Sink (Async)
    logger.add(error_report_sink, level="ERROR")

