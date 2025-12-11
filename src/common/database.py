from tortoise import Tortoise
from nonebot import get_driver
from nonebot.log import logger
from src.common.config import global_config

async def init_db():
    """
    Initialize Tortoise ORM.
    Call this function in your bot's startup hook.
    """
    env = (global_config.environment or "dev").lower()
    db_url = global_config.db_url_dev if env == "dev" else global_config.db_url_prod
    logger.info(f"Initializing Database with URL: {db_url}")
    
    # Discover models automatically from plugins if they follow a pattern,
    # or explicitly list them here.
    # For now, we assume models are in 'src.common.models' (to be created).
    modules = {"models": ["src.common.models"]} 
    
    try:
        await Tortoise.init(
            db_url=db_url,
            modules=modules
        )
        # Generate schemas (create tables)
        # In production, use 'aerich' for migrations instead of generate_schemas
        await Tortoise.generate_schemas()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

async def close_db():
    await Tortoise.close_connections()

# Register hooks
driver = get_driver()
driver.on_startup(init_db)
driver.on_shutdown(close_db)
