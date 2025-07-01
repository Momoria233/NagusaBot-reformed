from pydantic import BaseModel, Field
from typing import Dict

class Config(BaseModel):
    bilibili_watch_uid_group_map: Dict[int, int] = Field(
        ..., description="需要监听的B站UID与推送目标群号的映射，如 {uid: group_id}"
    )
    bilibili_watch_interval: int = Field(60, description="轮询间隔（秒）")

config = Config.model_validate({
    "bilibili_watch_uid_group_map": {
        3546575051688471: 996101999,
        1165690698: 996101999,
        # 3546575051688471: 225173408,
        # 410532721: 225173408,
    },
    "bilibili_watch_interval": 120,
})