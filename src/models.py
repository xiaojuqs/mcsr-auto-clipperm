"""数据模型"""
from dataclasses import dataclass


@dataclass
class ClipMoment:
    """剪辑时刻"""
    match_id: str
    event_type: str  # death, nether, end, etc.
    player_name: str
    vod_url: str
    vod_start_seconds: int  # 在 VOD 中的开始时间（秒）
    vod_end_seconds: int    # 在 VOD 中的结束时间（秒）
    description: str
