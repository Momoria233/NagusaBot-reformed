from pydantic import BaseModel, Field

class Config(BaseModel):
    bilibili_watch_uid: int = Field(..., description="需要监听的B站UID")
    bilibili_watch_interval: int = Field(60, description="轮询间隔（秒）")
    bilibili_watch_target_group: int = Field(..., description="推送目标群号")

config = Config.model_validate({
    "bilibili_watch_uid": 3546575051688471,
    "bilibili_watch_interval": 60,
    "bilibili_watch_target_group": 996101999,
})