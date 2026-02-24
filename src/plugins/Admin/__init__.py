import json
from typing import Optional
from nonebot import on_command, on_message, on_notice, logger, get_driver
from nonebot.exception import FinishedException
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    MessageEvent,
    PrivateMessageEvent,
    GroupIncreaseNoticeEvent,
    Message,
)
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.rule import to_me
from src.common.permission_manager import FeatureSpec, permission_manager
from src.common.plugin_config import get_group_assets_dir
from src.common.config import global_config
from src.common.resource import resource_manager

PLUGIN_REG_NAME = "Admin"
PLUGIN_REAL_NAME = "管理功能"
FEATURE_ADMIN = "/admin"

permission_manager.register(
    PLUGIN_REG_NAME,
    PLUGIN_REAL_NAME,
    features=[FeatureSpec(name=FEATURE_ADMIN, default_open=True, description="群bot功能管理")],
    group_customize=True,
)

pending_wizards = {}
driver = get_driver()

data_dir = resource_manager.data_root / "config" / PLUGIN_REG_NAME
data_dir.mkdir(parents=True, exist_ok=True)
access_control_file = data_dir / "access_control.json"


def _read_access_control() -> dict:
    if not access_control_file.exists():
        payload = {"bot_admins": [], "trusted_users": []}
        with open(access_control_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return payload
    try:
        with open(access_control_file, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            return {"bot_admins": [], "trusted_users": []}
        bot_admins = payload.get("bot_admins", [])
        trusted_users = payload.get("trusted_users", [])
        if not isinstance(bot_admins, list):
            bot_admins = []
        if not isinstance(trusted_users, list):
            trusted_users = []
        return {"bot_admins": bot_admins, "trusted_users": trusted_users}
    except Exception:
        return {"bot_admins": [], "trusted_users": []}


def _write_access_control(bot_admins: set[int], trusted_users: set[int]) -> None:
    payload = {
        "bot_admins": sorted(int(x) for x in bot_admins),
        "trusted_users": sorted(int(x) for x in trusted_users),
    }
    with open(access_control_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _sync_access_control_from_file() -> tuple[set[int], set[int]]:
    payload = _read_access_control()
    bot_admins = set()
    trusted_users = set()
    for x in payload.get("bot_admins", []):
        try:
            bot_admins.add(int(x))
        except Exception:
            continue
    for x in payload.get("trusted_users", []):
        try:
            trusted_users.add(int(x))
        except Exception:
            continue
    global_config.bot_admins = bot_admins
    global_config.uni_recall_trusted_users = set(
        getattr(global_config, "uni_recall_trusted_users", set())
    ) | trusted_users
    return bot_admins, set(getattr(global_config, "uni_recall_trusted_users", set()))


def _is_bot_admin(user_id: int) -> bool:
    if str(user_id) == str(global_config.superuser_id):
        return True
    return user_id in set(getattr(global_config, "bot_admins", set()))


def _parse_user_id(s: str) -> Optional[int]:
    s = s.strip()
    if not s.isdigit():
        return None
    try:
        return int(s)
    except Exception:
        return None


async def _handle_access_control_command(args_list: list[str], actor_user_id: int) -> bool:
    if not args_list:
        return False
    head = args_list[0].lower()
    if head not in {"trusted", "botadmin"}:
        return False

    action = args_list[1].lower() if len(args_list) >= 2 else "list"
    if action not in {"list", "add", "del", "remove"}:
        await admin_cmd.finish("用法：/admin trusted list|add|del <QQ>\n或：/admin botadmin list|add|del <QQ>")

    if head == "botadmin" and str(actor_user_id) != str(global_config.superuser_id):
        await admin_cmd.finish("只有超级管理员可以管理 botadmin。")

    if head == "trusted" and not _is_bot_admin(actor_user_id):
        await admin_cmd.finish("只有 botadmin 或超级管理员可以管理 trusted。")

    bot_admins, trusted_users = _sync_access_control_from_file()

    if head == "trusted":
        target_set = set(trusted_users)
        label = "trusted users"
    else:
        target_set = set(bot_admins)
        label = "bot admins"

    if action == "list":
        if not target_set:
            await admin_cmd.finish(f"{label} 为空。")
        await admin_cmd.finish(f"{label}：\n" + "\n".join(str(x) for x in sorted(target_set)))

    if len(args_list) < 3:
        await admin_cmd.finish("缺少 QQ 号参数。")

    target_id = _parse_user_id(args_list[2])
    if target_id is None:
        await admin_cmd.finish("QQ 号必须是数字。")

    if head == "trusted":
        if action == "add":
            target_set.add(target_id)
        else:
            target_set.discard(target_id)
        global_config.uni_recall_trusted_users = set(target_set)
        _write_access_control(set(getattr(global_config, "bot_admins", set())), set(target_set))
        await admin_cmd.finish(f"已更新 {label}，当前数量：{len(target_set)}")

    if action == "add":
        target_set.add(target_id)
    else:
        target_set.discard(target_id)
    global_config.bot_admins = set(target_set)
    _write_access_control(set(target_set), set(getattr(global_config, "uni_recall_trusted_users", set())))
    await admin_cmd.finish(f"已更新 {label}，当前数量：{len(target_set)}")

enable_cmd = on_command(
    "开启",
    aliases={"enable", "启用"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
)


@enable_cmd.handle()
async def handle_enable(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    if not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_ADMIN, event.group_id, event.user_id
    ):
        await enable_cmd.finish("功能未开启")
    raw = args.extract_plain_text().strip()
    if not raw:
        await enable_cmd.finish("请输入 <plugin> <feature>")
    parts = raw.replace(":", " ").replace("/", " ").split()
    if len(parts) < 2:
        await enable_cmd.finish("请输入 <plugin> <feature>")
    plugin_name, feature_name = parts[0], parts[1]
    try:
        permission_manager.set_feature_state(plugin_name, feature_name, event.group_id, True)
    except Exception:
        await enable_cmd.finish(f"未找到功能：{plugin_name}:{feature_name}。请使用 /help 查看可用功能。")
    logger.info(f"Group {event.group_id} enabled {plugin_name}:{feature_name}")
    await enable_cmd.finish(f"已为本群开启 {plugin_name}:{feature_name}")

disable_cmd = on_command(
    "关闭",
    aliases={"disable", "禁用"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
)


@disable_cmd.handle()
async def handle_disable(bot: Bot, event: GroupMessageEvent, args: Message = CommandArg()):
    if not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_ADMIN, event.group_id, event.user_id
    ):
        await disable_cmd.finish("功能未开启")
    raw = args.extract_plain_text().strip()
    if not raw:
        await disable_cmd.finish("请输入 <plugin> <feature>")
    parts = raw.replace(":", " ").replace("/", " ").split()
    if len(parts) < 2:
        await disable_cmd.finish("请输入 <plugin> <feature>")
    plugin_name, feature_name = parts[0], parts[1]
    try:
        permission_manager.set_feature_state(plugin_name, feature_name, event.group_id, False)
    except Exception:
        await disable_cmd.finish(f"未找到功能：{plugin_name}:{feature_name}。")
    logger.info(f"Group {event.group_id} disabled {plugin_name}:{feature_name}")
    await disable_cmd.finish(f"已为本群关闭 {plugin_name}:{feature_name}")

list_cmd = on_command(
    "本群功能",
    aliases={"ls_features"},
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
)


@list_cmd.handle()
async def handle_list(bot: Bot, event: GroupMessageEvent):
    if not permission_manager.is_enabled(
        PLUGIN_REG_NAME, FEATURE_ADMIN, event.group_id, event.user_id
    ):
        await list_cmd.finish("功能未开启")
    lines = ["== 本群功能状态 =="]
    for plugin_name in permission_manager.list_plugins():
        real_name, feature_items = permission_manager.list_features(plugin_name)
        for feature_name, feature_desc in feature_items:
            decision = permission_manager.get_decision(
                plugin_name, feature_name, event.group_id, event.user_id
            )
            state = "✅" if decision.enabled else "❌"
            desc = f" {feature_desc}" if feature_desc else ""
            if real_name == plugin_name:
                lines.append(f"{state} {plugin_name}:{feature_name}{desc}")
            else:
                lines.append(f"{state} {plugin_name}:{feature_name} ({real_name}){desc}")
    await list_cmd.finish("\n".join(lines))


admin_cmd = on_command("admin", aliases={"settings", "管理"}, priority=1, block=True)


@driver.on_startup
async def startup_sync():
    _sync_access_control_from_file()


@admin_cmd.handle()
async def handle_admin(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    logger.info(f"Admin Settings: Command triggered by user {event.user_id}")
    arg_str = args.extract_plain_text().strip()
    args_list = arg_str.split()
    user_id = event.user_id
    is_superuser = str(user_id) == str(global_config.superuser_id)
    is_bot_admin = _is_bot_admin(user_id)
    if isinstance(event, GroupMessageEvent):
        if not permission_manager.is_enabled(
            PLUGIN_REG_NAME, FEATURE_ADMIN, event.group_id, event.user_id
        ):
            await admin_cmd.finish("功能未开启")

    if args_list:
        handled = await _handle_access_control_command(args_list, user_id)
        if handled:
            return

    if isinstance(event, PrivateMessageEvent):
        if not args_list:
            await admin_cmd.send("正在获取您管理的群组列表，请稍候...")

            try:
                all_groups = await bot.get_group_list()
                admin_groups = []

                for group in all_groups:
                    gid = group["group_id"]
                    gname = group["group_name"]

                    if is_superuser or is_bot_admin:
                        admin_groups.append(f"{gname} ({gid})")
                        continue

                    try:
                        member_info = await bot.get_group_member_info(group_id=gid, user_id=user_id)
                        role = member_info.get("role", "member")
                        if role in ["owner", "admin"]:
                            admin_groups.append(f"{gname} ({gid})")
                    except Exception:
                        continue

                if not admin_groups:
                    await admin_cmd.finish("您当前没有管理的群组（或Bot未加入您管理的群组）。")

                msg = "您拥有管理权限的群组如下：\n" + "\n".join(admin_groups)
                msg += "\n\n请回复 '/admin <群号>' 查看该群功能设置。"
                await admin_cmd.finish(msg)

            except FinishedException:
                raise
            except Exception as e:
                logger.error(f"Error fetching admin groups: {e}")
                await admin_cmd.finish(f"获取群组列表失败: {e}")

        group_id_str = args_list[0]
        if not group_id_str.isdigit():
            await admin_cmd.finish("群号必须是数字。")

        group_id = int(group_id_str)

        if not (is_superuser or is_bot_admin):
            try:
                member_info = await bot.get_group_member_info(group_id=group_id, user_id=user_id)
                if member_info.get("role") not in ["owner", "admin"]:
                    await admin_cmd.finish(f"您在群 {group_id} 没有管理权限。")
            except Exception:
                await admin_cmd.finish(f"无法获取群 {group_id} 的成员信息，您可能不在该群中。")

        if len(args_list) == 1:
            await _show_group_settings(admin_cmd, group_id)
            return

        if len(args_list) < 3:
            await admin_cmd.finish("指令格式错误。私聊请使用：/admin <群号> <功能名> <on/off>")

        feature_name = args_list[1]
        action = args_list[2]
        await _set_group_feature(admin_cmd, group_id, feature_name, action)

    elif isinstance(event, GroupMessageEvent):
        group_id = event.group_id

        if not (is_superuser or is_bot_admin):
            sender_role = event.sender.role
            if sender_role not in ["owner", "admin"]:
                await admin_cmd.finish("只有群主或管理员可以配置Bot功能。")

        if not args_list:
            await _show_group_settings(admin_cmd, group_id, is_group_chat=True)
            return

        if len(args_list) == 2:
            feature_name = args_list[0]
            action = args_list[1]
            await _set_group_feature(admin_cmd, group_id, feature_name, action)
            return

        if args_list[0].isdigit() and int(args_list[0]) == group_id:
            if len(args_list) == 1:
                await _show_group_settings(admin_cmd, group_id, is_group_chat=True)
            elif len(args_list) == 3:
                await _set_group_feature(admin_cmd, group_id, args_list[1], args_list[2])
            else:
                await admin_cmd.finish("指令格式错误。群内请使用：/admin <功能名> <on/off>")
        else:
            await admin_cmd.finish("群内指令请直接使用：/admin <功能名> <on/off>\n（无需输入群号，仅支持配置本群）")


setup_cmd = on_command(
    "setup_wizard",
    aliases={"setup", "群设置向导"},
    rule=to_me(),
)


@setup_cmd.handle()
async def handle_setup(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    raw = args.extract_plain_text().strip()
    await _handle_setup_wizard(bot, event, raw, setup_cmd.finish)


assets_cmd = on_command(
    "setup_assets",
    aliases={"assets_init", "群资产初始化"},
    rule=to_me(),
)


@assets_cmd.handle()
async def handle_assets(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    raw = args.extract_plain_text().strip()
    await _handle_setup_assets(bot, event, raw, assets_cmd.finish)


bot_join_notice = on_notice()


@bot_join_notice.handle()
async def handle_bot_join(bot: Bot, event: GroupIncreaseNoticeEvent):
    if event.user_id != event.self_id:
        return
    superuser = global_config.superuser_id
    if not superuser:
        return
    await bot.send_private_msg(
        user_id=superuser,
        message=f"已加入新群 {event.group_id}，可回复 /setup_wizard {event.group_id} 进行功能设置，或 /setup_assets {event.group_id} 初始化群 assets。",
    )


wizard_reply = on_message()


@wizard_reply.handle()
async def handle_wizard_reply(bot: Bot, event: PrivateMessageEvent):
    if not isinstance(event, PrivateMessageEvent):
        return
    if str(event.user_id) != str(global_config.superuser_id):
        return
    state = pending_wizards.get(event.user_id)
    if not state:
        return
    text = event.message.extract_plain_text().strip().lower()
    if text in {"取消", "退出", "停止", "cancel", "stop"}:
        pending_wizards.pop(event.user_id, None)
        await bot.send_private_msg(user_id=event.user_id, message="已取消设置向导")
        return
    if text in {"all on", "all off"}:
        enable_flag = text.endswith("on")
        await _apply_all_remaining(state, enable_flag)
        pending_wizards.pop(event.user_id, None)
        await bot.send_private_msg(user_id=event.user_id, message="设置完成")
        return
    if text in {"on", "off", "enable", "disable", "开启", "关闭", "true", "false", "skip"}:
        if text in {"skip"}:
            state["index"] += 1
            await _send_wizard_prompt(bot, event.user_id)
            return
        enable_flag = text in {"on", "enable", "开启", "true"}
        await _apply_current(state, enable_flag)
        state["index"] += 1
        await _send_wizard_prompt(bot, event.user_id)
        return
    await bot.send_private_msg(
        user_id=event.user_id,
        message="请输入 on/off/skip，或 all on/all off，或 取消。",
    )


async def _handle_setup_wizard(bot: Bot, event: MessageEvent, raw: str, finish):
    if isinstance(event, GroupMessageEvent):
        if not permission_manager.is_enabled(
            PLUGIN_REG_NAME, FEATURE_ADMIN, event.group_id, event.user_id
        ):
            await finish("功能未开启")
        sender_role = getattr(event.sender, "role", None)
        if str(event.user_id) != str(global_config.superuser_id) and sender_role not in {
            "owner",
            "admin",
        }:
            await finish("仅群主或管理员可使用该功能")
        group_id = event.group_id
        await finish(f"请私信我并发送：/setup_wizard {group_id}")
    if not isinstance(event, PrivateMessageEvent):
        await finish("仅支持私信进行设置向导。")
    if str(event.user_id) != str(global_config.superuser_id):
        await finish("仅支持超级用户使用该功能")
    if not raw.isdigit():
        await finish("请输入群号：/setup_wizard <群号>")
    group_id = int(raw)
    pending_wizards[event.user_id] = {
        "group_id": group_id,
        "queue": _build_wizard_queue(),
        "index": 0,
    }
    await _send_wizard_prompt(bot, event.user_id)
    await finish("已启动设置向导")


async def _handle_setup_assets(bot: Bot, event: MessageEvent, raw: str, finish):
    if isinstance(event, GroupMessageEvent):
        if not permission_manager.is_enabled(
            PLUGIN_REG_NAME, FEATURE_ADMIN, event.group_id, event.user_id
        ):
            await finish("功能未开启")
        sender_role = getattr(event.sender, "role", None)
        if str(event.user_id) != str(global_config.superuser_id) and sender_role not in {
            "owner",
            "admin",
        }:
            await finish("仅群主或管理员可使用该功能")
        group_id = event.group_id
    else:
        if str(event.user_id) != str(global_config.superuser_id):
            await finish("仅支持超级用户使用该功能")
        if not raw.isdigit():
            await finish("请输入群号：/setup_assets <群号>")
        group_id = int(raw)
    created = 0
    for plugin_name in permission_manager.list_plugins():
        path = get_group_assets_dir(plugin_name, group_id, create=True)
        if path is not None:
            created += 1
    await finish(f"已为群 {group_id} 初始化 {created} 个插件的 assets 目录")


async def _show_group_settings(
    responder, group_id: int, is_group_chat: bool = False
):
    features_status = []
    for plugin_name in permission_manager.list_plugins():
        real_name, feature_items = permission_manager.list_features(plugin_name)
        for feature_name, feature_desc in feature_items:
            decision = permission_manager.get_decision(plugin_name, feature_name, group_id)
            status_icon = "✅" if decision.enabled else "❌"
            desc = f" {feature_desc}" if feature_desc else ""
            if real_name == plugin_name:
                features_status.append(f"{status_icon} {plugin_name}:{feature_name}{desc}")
            else:
                features_status.append(f"{status_icon} {plugin_name}:{feature_name} ({real_name}){desc}")

    if not features_status:
        msg = "本群暂无已注册的可配置功能。" if is_group_chat else f"群 {group_id} 暂无已注册的可配置功能。"
    else:
        header = "本群功能配置：" if is_group_chat else f"群 {group_id} 功能配置："
        msg = header + "\n" + "\n".join(features_status)
        if is_group_chat:
            msg += "\n\n修改指令：/admin <功能名> <on/off>"
        else:
            msg += f"\n\n修改指令：/admin {group_id} <功能名> <on/off>"

    await responder.finish(msg)


async def _set_group_feature(responder, group_id: int, feature_name: str, action: str):
    action = action.lower()
    if action not in ["on", "off", "enable", "disable", "开启", "关闭", "true", "false"]:
        await responder.finish("操作只能是 on/off/开启/关闭")

    enable_flag = action in ["on", "enable", "开启", "true"]

    parts = feature_name.replace(":", " ").replace("/", " ").split()
    if len(parts) == 2:
        plugin_reg_name, feature_key = parts[0], parts[1]
    else:
        await responder.finish("功能名格式应为 <plugin> <feature> 或 <plugin>:<feature>")
    try:
        permission_manager.set_feature_state(plugin_reg_name, feature_key, group_id, enable_flag)
    except Exception:
        await responder.finish(f"设置失败，可能是功能名 '{feature_name}' 不存在。")
        return

    status_str = "开启" if enable_flag else "关闭"
    await responder.finish(f"已成功{status_str} {plugin_reg_name}:{feature_key} 功能。")


def _build_wizard_queue():
    queue = []
    for plugin_name in permission_manager.list_plugins():
        real_name, feature_items = permission_manager.list_features(plugin_name)
        if not feature_items:
            continue
        queue.append((plugin_name, real_name, feature_items))
    return queue


async def _send_wizard_prompt(bot: Bot, user_id: int):
    state = pending_wizards.get(user_id)
    if not state:
        return
    index = state["index"]
    queue = state["queue"]
    if index >= len(queue):
        pending_wizards.pop(user_id, None)
        await bot.send_private_msg(user_id=user_id, message="设置完成")
        return
    plugin_name, real_name, feature_items = queue[index]
    features_text = "、".join([name for name, _ in feature_items])
    await bot.send_private_msg(
        user_id=user_id,
        message=(
            f"群 {state['group_id']} | {real_name} ({plugin_name})\n"
            f"功能：{features_text}\n"
            "回复 on/off/skip，或 all on/all off，或 取消"
        ),
    )


async def _apply_current(state, enable_flag: bool):
    group_id = state["group_id"]
    plugin_name, _, feature_items = state["queue"][state["index"]]
    for feature_name, _ in feature_items:
        permission_manager.set_feature_state(plugin_name, feature_name, group_id, enable_flag)


async def _apply_all_remaining(state, enable_flag: bool):
    group_id = state["group_id"]
    queue = state["queue"]
    for idx in range(state["index"], len(queue)):
        plugin_name, _, feature_items = queue[idx]
        for feature_name, _ in feature_items:
            permission_manager.set_feature_state(plugin_name, feature_name, group_id, enable_flag)
