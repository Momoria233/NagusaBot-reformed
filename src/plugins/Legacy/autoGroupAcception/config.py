from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict

@dataclass
class StrategyConfig:
    type: Literal["json", "regex"]
    # for json
    file: Optional[str] = None
    keys: Optional[List[str]] = None
    # for regex
    # 支持正则表达式列表，只要匹配其中一个即可（OR 关系）。
    # 如果需要 AND 关系，请使用 lookahead regex (e.g. ^(?=.*A)(?=.*B))
    patterns: Optional[List[str]] = None 

# 默认配置：硬编码迁移至此
GROUP_STRATEGIES: Dict[int, StrategyConfig] = {
    996101999: StrategyConfig(
        type="json",
        file="replacement.json",
        keys=["FullName", "FamilyName", "PersonalName"]
    ),
    1081871797: StrategyConfig(
        type="regex",
        patterns=[r"(?s)(?=.*(?:日富美|hifumi))(?=.*(?:koharu|小春))"]
    ),
    225173408: StrategyConfig(
        type="regex",
        patterns=[r"(?s)(?=.*(?:日富美|hifumi))(?=.*(?:koharu|小春))"]
    )
}
