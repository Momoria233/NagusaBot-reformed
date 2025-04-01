import itertools
import os
import random
import re
import time
from typing import Dict, List

from nonebot import logger, on_message, on_notice
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
    PokeNotifyEvent,
)
from nonebot.typing import T_State

from .config import Config

REACT_MATCH_LIST_KEY = "react_match_list"

pattern_left = re.compile(r"(?<!\\)\{")
pattern_right = re.compile(r"(?<!\\)\}")
pattern_img_command = re.compile(r"!img:(.*)")
pattern_rand_command = re.compile(r"!rand:(.*)")


async def merge_reply(s: str, args: dict, event: MessageEvent, bot: Bot) -> Message:
    parts = [re.split(pattern_right, i) for i in re.split(pattern_left, s)]
    parts = [i.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\") for i in list(itertools.chain(*parts))]
    message_list: list[MessageSegment] = []
    for i, part in enumerate(parts):
        if i % 2 == 0:
            if part:
                message_list.append(MessageSegment.text(part))
        else:
            match part:
                case "!at":
                    message_list.append(MessageSegment.at(event.user_id))
                case str() as string if re.match(pattern_img_command, string):
                    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "asset", re.match(pattern_img_command, string).group(1))
                    message_list.append(MessageSegment.image(path))
                case str() as string if re.match(pattern_rand_command, string):
                    condition = re.match(pattern_rand_command, string).group(1)
                    if not condition in args:
                        logger.warning(f"Missing condition {condition} (Message: {s}). Ignore this segment.")
                        continue
                    if not isinstance(args[condition], dict):
                        logger.warning(f"Unexpect format for condition {condition} (Message: {s}). Ignore this segment.")
                        continue
                    if not "type" in args[condition]:
                        logger.warning(f'Missing key "type" (Condition: {condition}, Message: {s}). Ignore this segment.')
                        continue
                    if not "lower" in args[condition]:
                        logger.warning(f'Missing key "lower" (Condition: {condition}, Message: {s}). Ignore this segment.')
                        continue
                    if not "upper" in args[condition]:
                        logger.warning(f'Missing key "upper" (Condition: {condition}, Message: {s}). Ignore this segment.')
                        continue
                    if not isinstance(args[condition]["upper"], (str, int)):
                        logger.warning(f'Unexpect format for key "upper" (Condition: {condition}, Message: {s}). Ignore this segment.')
                        continue
                    if "group_num" in args[condition]["upper"]:
                        if not isinstance(event, GroupMessageEvent):
                            logger.warning(f'Found tag "group_num" in "upper", but message is private (Condition: {condition}, Message: {s}). Ignore this segment.')
                            continue
                        upper = eval(args[condition]["upper"].replace("group_num", str(len(await bot.get_group_member_list(event.group_id)))))
                    if not isinstance(args[condition]["lower"], (str, int)):
                        logger.warning(f'Unexpect format for key "lower" (Condition: {condition}, Message: {s}). Ignore this segment.')
                        continue
                    if "group_num" in args[condition]["lower"]:
                        if not isinstance(event, GroupMessageEvent):
                            logger.warning(f'Found tag "group_num" in "lower", but message is private (Condition: {condition}, Message: {s}). Ignore this segment.')
                            continue
                        lower = eval(args[condition]["lower"].replace("group_num", str(len(await bot.get_group_member_list(event.group_id)))))
                    match args[condition]["type"]:
                        case "int":
                            message_list.append(MessageSegment.text(random.randint(lower, upper)))
                        case "float":
                            if "fix" in args[condition]:
                                if not isinstance(args[condition]["fix"], int):
                                    logger.warning(f'Unexpect format for key "fix" (Condition: {condition}, Message: {s}). Ignore this segment.')
                                    continue
                                message_list.append(MessageSegment.text(round(random.uniform(lower, upper), args[condition]["fix"])))
                            else:
                                message_list.append(MessageSegment.text(random.uniform(lower, upper)))
                        case _:
                            logger.warning(f"Unknown type {args[condition]["type"]} (Condition: {condition}, Message: {s}). Ignore this segment.")
                            continue
                case str() as string:
                    if not string in args:
                        logger.warning(f"Missing argument {string} (Message: {s}). Ignore this segment.")
                        continue
                    if isinstance(args[string], list):
                        message_list.append(MessageSegment.text(random.choice(args[string])))
                    elif isinstance(args[string], dict):
                        message_list.append(MessageSegment.text(random.choice(list(args[string].keys()), list(args[string].values()))))
                    else:
                        logger.warning(f"Unexpect format for key {string} (Message: {s}). Ignore this segment.")
                        continue
    logger.debug(f"Formatted {s} to {message_list}")

    return Message(message_list)


patterns: List[re.Pattern] = []
replys: List[Dict] = []
cooldown_tracker: List[Dict[int, float]] = []
for pattern in Config.on_message.keys():
    patterns.append(re.compile(pattern))
    replys.append(Config.on_message[pattern])
    cooldown_tracker.append({})


def message_checker(event: GroupMessageEvent, state: T_State) -> bool:
    current_time = time.time()
    state[REACT_MATCH_LIST_KEY] = []
    for index, pattern in enumerate(patterns):
        last_used = cooldown_tracker[index].get(event.user_id, 0.0)
        if "cooldown" in replys[index]:
            if not isinstance(replys[index]["cooldown"], (int, float)):
                logger.warning(f'Unexpect format for key "cooldown" (Rule: {patterns[index].pattern}). Ignore cooldown.')
            if current_time - last_used < replys[index]["cooldown"]:
                continue
        if re.search(pattern, event.message.extract_plain_text()) != None:
            state[REACT_MATCH_LIST_KEY].append(index)
            cooldown_tracker[index][event.user_id] = current_time
    return len(state[REACT_MATCH_LIST_KEY]) == 0


message_matcher = on_message(priority=1, rule=message_checker)


@message_matcher.handle()
async def message_handler(bot: Bot, event: GroupMessageEvent, state: T_State):
    for index in state[REACT_MATCH_LIST_KEY]:
        await message_matcher.send(await merge_reply(replys[index]["res"], replys[index]["args"], event, bot))
    await message_matcher.finish()


poke_matcher = on_notice()


@poke_matcher.handle()
async def poke_handler(bot: Bot, event: PokeNotifyEvent, state: T_State):
    pass  # TODO
