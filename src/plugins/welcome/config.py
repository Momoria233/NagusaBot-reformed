from typing import Dict


class Config:
    # 目前允许的格式：
    # 1. {at} 对加群人的 at
    # 2. {img:path} 路径为 path 的图片

    welcome_message: Dict[int, str] = {
        996101999: "欢迎{at} 老师来到北京BAO游客群！\n请老师先阅读群公告，有问题请私信群管理\n本展将于5.1日开票，b站会员购链接为show.bilibili.com/platform/detail.html?id=101173。\n注意：本展与目前会员购上另一个“北京BAO2.0”并非同一个展，请老师购票时注意分辨。\n最后，请老师敬请期待，也祝老师在群里玩得愉快！",
        225173408: "入群测试消息",
    }
