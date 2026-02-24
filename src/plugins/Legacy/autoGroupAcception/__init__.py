import re
import json
import asyncio
from typing import Optional, Dict, Any, List
from nonebot import logger, on_request, on_message
from nonebot.adapters.onebot.v11 import Bot, GroupRequestEvent, PrivateMessageEvent
from nonebot.typing import T_State

from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.config import global_config
from src.common.plugin_config import get_assets_dir
from src.common.logger import get_group_name, get_user_display_name

from .config import GROUP_STRATEGIES, StrategyConfig

PLUGIN_REG_NAME = "autoGroupAcception"
PLUGIN_REAL_NAME = "入群申请管理"
FEATURE_AUTO = "自动入群申请"
FEATURE_MANUAL = "强制人工审核"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[
        FeatureSpec(name=FEATURE_AUTO, default_open=True, description="对新的入群申请进行正则表达式或json匹配并自动通过，对于未匹配成功的将进入向管理员私信申请手动匹配的功能。"),
        FeatureSpec(name=FEATURE_MANUAL, default_open=False, description="开启后，该群的所有入群申请都将转为人工审核，忽略自动匹配规则"),
    ],
    group_customize=True,
)

# Global pending requests storage
pending_requests = {}

# --- 验证逻辑 ---

def load_json_data(filename: str) -> List[Dict[str, Any]]:
    assets_dir = get_assets_dir(__file__)
    file_path = assets_dir / filename
    if not file_path.exists():
        logger.warning(f"JSON file not found: {file_path}")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load JSON file {file_path}: {e}")
        return []

# 缓存加载的数据，避免每次请求都读文件
# Key: filename, Value: data list
_json_cache: Dict[str, List[Dict[str, Any]]] = {}

def get_cached_json_data(filename: str) -> List[Dict[str, Any]]:
    if filename not in _json_cache:
        _json_cache[filename] = load_json_data(filename)
    return _json_cache[filename]

def check_json_strategy(answer: str, config: StrategyConfig) -> bool:
    if not config.file or not config.keys:
        return False
    data = get_cached_json_data(config.file)
    if not data:
        return False
    
    for item in data:
        for key in config.keys:
            val = item.get(key)
            if not val:
                continue
            # 原逻辑兼容：完全相等 OR 包含（反向包含：答案中包含名字）
            # 原逻辑：input_name == item.get("FullName") ... or item.get("FullName") in input_name
            if answer == val or val in answer:
                return True
    return False

def check_regex_strategy(answer: str, config: StrategyConfig) -> bool:
    if not config.patterns:
        return False
    for pattern in config.patterns:
        try:
            if re.search(pattern, answer):
                return True
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
    return False

def check_strategy(answer: str, group_id: int) -> bool:
    config = GROUP_STRATEGIES.get(group_id)
    if not config:
        # 如果没有配置策略，默认行为是什么？
        # 根据原代码逻辑，如果没有匹配到特定群号，会走到最后 check_stu_name 的通用检查
        # 也就是默认使用 replacement.json 检查。
        # 为了保持兼容性，我们可以定义一个默认策略，或者在没有配置时返回 False
        # 这里为了安全，没有配置默认返回 False (除非我们把通用检查作为默认配置)
        
        # 原逻辑最后有一个 check_stu_name(answer) 的通用调用
        # 这意味着所有未在特殊列表的群，都会尝试匹配 replacement.json
        # 所以我们需要一个 DEFAULT_STRATEGY
        default_config = StrategyConfig(
            type="json",
            file="replacement.json",
            keys=["FullName", "FamilyName", "PersonalName"]
        )
        return check_json_strategy(answer, default_config)

    if config.type == "json":
        return check_json_strategy(answer, config)
    elif config.type == "regex":
        return check_regex_strategy(answer, config)
    
    return False

# --- 异步处理逻辑 ---

async def wait_for_reply(key):
    fut = asyncio.get_event_loop().create_future()
    pending_requests[key] = fut
    return await fut

async def check_manual_approve(bot: Bot, event: GroupRequestEvent, type: str, answer: str, block=False):
    superuser = global_config.superuser_id
    gname = await get_group_name(bot, event.group_id)
    uname = await get_user_display_name(bot, event.user_id)
    
    if type == "autoMatchFailed":
        msg = (f"群 {gname}({event.group_id}) 的 {uname}({event.user_id}) 入群匹配失败。\n申请提示词: {answer}，请在5分钟内回复“是”通过，“否”拒绝。")
        logger.info(msg)
        await bot.send_private_msg(user_id=superuser, message=msg)
    elif type == "manualApprove":
        msg = (f"群 {gname}({event.group_id}) 的 {uname}({event.user_id}) 需要人工审核。\n申请提示词: {answer}，请在5分钟内回复“是”通过，“否”拒绝。")
        logger.info(msg)
        await bot.send_private_msg(user_id=superuser, message=msg)
    else:
        return False
        
    key = f"{event.group_id}_{event.user_id}"
    
    try:
        # Wait for the future to be set by the private message handler
        result = await asyncio.wait_for(wait_for_reply(key), timeout=300)
        
        if result == "是":
            await event.approve(bot)
            await bot.send_private_msg(user_id=superuser, message=f"已通过 {uname}({event.user_id}) 在群 {gname}({event.group_id}) 的申请。")
        elif result == "否":
            await event.reject(bot)
            await bot.send_private_msg(user_id=superuser, message=f"已拒绝 {uname}({event.user_id}) 在群 {gname}({event.group_id}) 的申请。")
        else:
            await bot.send_private_msg(user_id=superuser, message=f"未知回复，已结束处理。回复：{result}。")
            
    except asyncio.TimeoutError:
        await bot.send_private_msg(user_id=superuser, message=f"针对 {uname}({event.user_id}) 的审核超时，已结束处理。")
    finally:
        pending_requests.pop(key, None)

GroupRequest = on_request(priority=1)

@GroupRequest.handle()
async def handle_group_request(bot: Bot, event: GroupRequestEvent, block=False):
    logger.info(f"Group {event.group_id} request from {event.user_id}")
    answer = event.comment.split("答案：", 1)[1] if "答案：" in event.comment else event.comment
    logger.info(f"Extracted answer: {answer}")

    # 1. 检查是否开启了自动入群功能
    if not permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_AUTO, event.group_id, event.user_id):
        # 如果没开启，直接结束，不处理（交给其他插件或忽略）
        # 除非有 Feature 明确说是 "禁用后自动拒绝"，否则通常是 "不作为"
        logger.info(f"Group {event.group_id} feature '{FEATURE_AUTO}' is disabled. Skipping.")
        await GroupRequest.finish()

    # 2. 检查是否开启了强制人工审核
    if permission_manager.is_enabled(PLUGIN_REG_NAME, FEATURE_MANUAL, event.group_id, event.user_id):
        logger.info(f"group {event.group_id} has forced manual approve enabled")
        await check_manual_approve(bot, event, type="manualApprove", answer=answer)
        await GroupRequest.finish()

    # 3. 执行策略匹配
    if check_strategy(answer, event.group_id):
        await event.approve(bot)
        msg = f"Group {event.group_id} request from {event.user_id} approved (Auto matched)"
        logger.info(msg)
        await bot.send_private_msg(user_id=global_config.superuser_id, message=msg)
        await GroupRequest.finish()
    else:
        # 4. 匹配失败，转人工
        logger.info(f"Group {event.group_id} request from {event.user_id} auto match failed")
        await check_manual_approve(bot, event, type="autoMatchFailed", answer=answer)
        await GroupRequest.finish()

private_msg = on_message(priority=1)

@private_msg.handle()
async def handle_private_msg(bot: Bot, event: PrivateMessageEvent):
    if not isinstance(event, PrivateMessageEvent):
        return
    if str(event.user_id) != str(global_config.superuser_id):
        return

    msg_text = event.message.extract_plain_text().strip()
    
    # Check if we have pending requests
    processed_count = 0
    
    for key, fut in list(pending_requests.items()):
        if isinstance(fut, asyncio.Future) and not fut.done():
            if msg_text in ["是", "否"]:
                fut.set_result(msg_text)
                processed_count += 1
    
    if processed_count > 0:
        await private_msg.finish()
