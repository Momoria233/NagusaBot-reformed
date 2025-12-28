import json
from nonebot import on_command, logger, get_driver
from nonebot.exception import FinishedException
from typing import List, Optional, Set, Tuple
from nonebot.adapters.onebot.v11 import (
    Bot,
    PrivateMessageEvent,
    GroupMessageEvent,
    MessageEvent,
    Message,
    MessageSegment,
)
from nonebot.params import CommandArg
from src.common.feature_manager import feature_manager
from src.common.config import global_config
from src.common.resource import resource_manager

logger.info("Admin Settings Plugin: Loading...")

admin_cmd = on_command("admin", aliases={"settings", "管理"}, priority=1,block=True)

driver = get_driver()

data_dir = resource_manager.get_data_dir("admin-settings")
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


def _write_access_control(bot_admins: Set[int], trusted_users: Set[int]) -> None:
    payload = {
        "bot_admins": sorted(int(x) for x in bot_admins),
        "trusted_users": sorted(int(x) for x in trusted_users),
    }
    with open(access_control_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _sync_access_control_from_file() -> Tuple[Set[int], Set[int]]:
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
    global_config.uni_recall_trusted_users = set(getattr(global_config, "uni_recall_trusted_users", set())) | trusted_users
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


async def _handle_access_control_command(args_list: List[str], actor_user_id: int) -> bool:
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


@driver.on_startup
async def startup_sync():
    logger.info("Admin Settings: Syncing feature manager cache...")
    await feature_manager.sync_cache()
    _sync_access_control_from_file()


@admin_cmd.handle()
async def handle_admin(bot: Bot, event: MessageEvent,args: Message = CommandArg()):
    logger.info(f"Admin Settings: Command triggered by user {event.user_id}")
    arg_str = args.extract_plain_text().strip()
    args_list = arg_str.split()
    user_id = event.user_id
    is_superuser = str(user_id) == str(global_config.superuser_id)
    is_bot_admin = _is_bot_admin(user_id)

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
            await show_group_settings(group_id)
            return

        if len(args_list) < 3:
            await admin_cmd.finish("指令格式错误。私聊请使用：/admin <群号> <功能名> <on/off>")

        feature_name = args_list[1]
        action = args_list[2]
        await set_group_feature(group_id, feature_name, action)

    elif isinstance(event, GroupMessageEvent):
        group_id = event.group_id

        if not (is_superuser or is_bot_admin):
            sender_role = event.sender.role
            if sender_role not in ["owner", "admin"]:
                await admin_cmd.finish("只有群主或管理员可以配置Bot功能。")

        if not args_list:
            await show_group_settings(group_id, is_group_chat=True)
            return

        if len(args_list) == 2:
            feature_name = args_list[0]
            action = args_list[1]
            await set_group_feature(group_id, feature_name, action)
            return

        if args_list[0].isdigit() and int(args_list[0]) == group_id:
            if len(args_list) == 1:
                await show_group_settings(group_id, is_group_chat=True)
            elif len(args_list) == 3:
                await set_group_feature(group_id, args_list[1], args_list[2])
            else:
                await admin_cmd.finish("指令格式错误。群内请使用：/admin <功能名> <on/off>")
        else:
            await admin_cmd.finish("群内指令请直接使用：/admin <功能名> <on/off>\n（无需输入群号，仅支持配置本群）")


async def show_group_settings(group_id: int, is_group_chat: bool = False):
    features_status = []
    all_features = feature_manager.features
    sorted_names = sorted(all_features.keys())

    for name in sorted_names:
        desc = all_features[name]
        enabled = feature_manager.is_enabled(str(group_id), name)
        status_icon = "✅" if enabled else "❌"
        features_status.append(f"{status_icon} {name}: {desc}")

    if not features_status:
        msg = "本群暂无已注册的可配置功能。" if is_group_chat else f"群 {group_id} 暂无已注册的可配置功能。"
    else:
        header = "本群功能配置：" if is_group_chat else f"群 {group_id} 功能配置："
        msg = header + "\n" + "\n".join(features_status)
        if is_group_chat:
            msg += "\n\n修改指令：/admin <功能名> <on/off>"
        else:
            msg += f"\n\n修改指令：/admin {group_id} <功能名> <on/off>"

    await admin_cmd.finish(msg)


async def set_group_feature(group_id: int, feature_name: str, action: str):
    action = action.lower()
    if action not in ["on", "off", "enable", "disable", "开启", "关闭", "true", "false"]:
        await admin_cmd.finish("操作只能是 on/off/开启/关闭")

    enable_flag = action in ["on", "enable", "开启", "true"]

    success = await feature_manager.set_feature(group_id, feature_name, enable_flag)

    if success:
        status_str = "开启" if enable_flag else "关闭"
        await admin_cmd.finish(f"已成功{status_str} {feature_name} 功能。")
    else:
        await admin_cmd.finish(f"设置失败，可能是功能名 '{feature_name}' 不存在。")

