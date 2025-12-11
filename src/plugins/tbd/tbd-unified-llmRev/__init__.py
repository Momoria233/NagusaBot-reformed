from src.common.feature_manager import feature_manager
feature_manager.register("rev语录", ": \n使用/rev xx可以让bot根据过去xx条聊天记录返回一条人机语录，\n使用/rev-r xx可以同时返回理由。")

group_message_history: dict[int, list[str]] = {}

# def fetchRecentMsg(group_id: int, count: int = 5) -> list[str]:
#     messages = group_message_history.get(group_id, [])
#     return messages[-count:] if messages else []

# record_message = on_message(priority=99, block=False)

# @record_message.handle()
# async def record_message_handle(event: GroupMessageEvent):
#     group_id = event.group_id
#     message = str(event.get_message())

#     if "[CQ:image" in message or "[CQ:mface" in message or "[CQ:record" in message:
#         return

#     match = re.search(r']\s*(.+)', message)
#     if match:
#         message = match.group(1).strip()

#     if group_id not in group_message_history:
#         group_message_history[group_id] = []

#     group_message_history[group_id].append(message)

#     if len(group_message_history[group_id]) > MAX_HISTORY:
#         group_message_history[group_id].pop(0)

# revL = on_command("rev",priority=5, block=True)

# @revL.handle()
# async def rev(bot: Bot, event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
#     if not feature_manager.is_enabled(event.group_id, "rev语录"):
#         await matcher.finish()
#     group_id = event.group_id
#     # if not event.user_id in Config.usr_whitelist:
#     #     await matcher.finish()

#     try:
#         n = int(str(args).strip()) if str(args).strip() else 5
#     except ValueError:
#         await matcher.finish(message=Message("格式错误，请输入 /rev [数字]"))

#     last_messages = fetchRecentMsg(group_id, n)

#     if not last_messages:
#         await matcher.finish(messgae=Message("暂无记录"))

#     output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(last_messages)])
#     ifIncluded, llmReply = await get_yulu_response(output)
#     try:
#         if ifIncluded == False:
#             not_found_path = os.path.normpath(os.path.join(assets_dir,"notFound.jpg"))
#             msg = Message(MessageSegment.image(not_found_path))
#         else:
#             llm_reply_path = os.path.normpath(os.path.join(assets_dir, "yulu", llmReply))
#             msg = Message(MessageSegment.image(llm_reply_path))
#         logger.debug(msg)
#         logger.debug(llmReply)
#         await matcher.finish(message=msg)
#     except nonebot.exception.FinishedException:
#         pass
#     except Exception as e:
#         logger.error(e)
#         await matcher.finish()

# revR = on_command("rev-r",priority=5, block=True)

# @revR.handle()
# async def revr(bot: Bot, event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()):
#     if not feature_manager.is_enabled(event.group_id, "rev语录"):
#         await matcher.finish()
#     group_id = event.group_id
#     # if not event.user_id in Config.usr_whitelist:
#     #     await matcher.finish()

#     try:
#         n = int(str(args).strip()) if str(args).strip() else 5
#     except ValueError:
#         await matcher.finish(message=Message("格式错误，请输入 /rev-r[数字]"))

#     last_messages = fetchRecentMsg(group_id, n)

#     if not last_messages:
#         await matcher.finish(messgae=Message("暂无记录"))

#     output = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(last_messages)])
#     ifIncluded, llmReply = await get_yulu_response(output)
#     try:
#         if ifIncluded == False:
#             not_found_path = os.path.normpath(os.path.join(assets_dir,"notFound.jpg"))
#             msg = Message(MessageSegment.image(not_found_path))
#         else:
#             llm_reply_path = os.path.normpath(os.path.join(assets_dir, "yulu", llmReply))
#             llmReason = await get_yulu_reason(output, llmReply)
#             msg = Message([MessageSegment.image(llm_reply_path), MessageSegment.text(" " + llmReason)])
#             logger.debug(llmReason)
#         logger.debug(msg)
#         logger.debug(llmReply)
#         await matcher.finish(message=msg)
#     except nonebot.exception.FinishedException:
#         pass
#     except Exception as e:
#         logger.error(e)
#         await matcher.finish()