from tortoise import fields
from tortoise.models import Model

class User(Model):
    id = fields.IntField(pk=True)
    qq_id = fields.BigIntField(unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "users"

class FeatureSwitch(Model):
    id = fields.IntField(pk=True)
    group_id = fields.BigIntField()
    feature_name = fields.CharField(max_length=50)
    is_enabled = fields.BooleanField(default=True)
    
    class Meta:
        table = "feature_switches"
        unique_together = (("group_id", "feature_name"),)

class Subscription(Model):
    id = fields.IntField(pk=True)
    sub_type = fields.CharField(max_length=20)  # e.g., "bilibili", "weibo"
    sub_id = fields.CharField(max_length=50)    # e.g., UID
    group_id = fields.BigIntField()
    extra_info = fields.JSONField(default={})   # For names, last_check_time, etc.
    
    class Meta:
        table = "subscriptions"
        unique_together = (("sub_type", "sub_id", "group_id"),)
