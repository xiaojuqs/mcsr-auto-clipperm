"""时间戳计算和片段提取"""
from datetime import datetime
from dataclasses import dataclass

from .models import ClipMoment


@dataclass
class SegmentMoment:
    """连续片段时刻"""
    match_id: str
    segment_type: str  # nether, bastion, fortress, etc.
    player_name: str
    vod_url: str
    vod_start_seconds: int  # 片段开始时间（秒）
    vod_end_seconds: int    # 片段结束时间（秒）
    description: str
    start_event: str  # 开始事件描述
    end_event: str    # 结束事件描述
    bastion_type: str = None  # 堡垒类型
    overworld_type: str = None  # 开局类型


# 时间线事件类型常量（基于实际 API 返回数据）

# 游戏进度事件（按游戏顺序）
EVENT_ENTER_NETHER = "story.enter_the_nether"  # 进入下界
EVENT_FIND_BASTION = "nether.find_bastion"  # 找到堡垒遗迹
EVENT_FIND_FORTRESS = "nether.find_fortress"  # 找到下界要塞
EVENT_FOLLOW_EYE = "story.follow_ender_eye"  # 跟随末影之眼（前往要塞）
EVENT_ENTER_END = "story.enter_the_end"  # 进入末地
EVENT_DRAGON_DEATH = "projectelo.timeline.dragon_death"  # 末影龙死亡

# 死亡事件
EVENT_DEATH = "projectelo.timeline.death"
EVENT_DEATH_SPAWNPOINT = "projectelo.timeline.death_spawnpoint"

# 所有支持的事件类型
SUPPORTED_EVENTS = {
    # 游戏进度事件
    EVENT_ENTER_NETHER,
    EVENT_FIND_BASTION,
    EVENT_FIND_FORTRESS,
    EVENT_FOLLOW_EYE,
    EVENT_ENTER_END,
    EVENT_DRAGON_DEATH,
    # 死亡事件
    EVENT_DEATH,
    EVENT_DEATH_SPAWNPOINT,
}

# 事件描述映射
EVENT_DESCRIPTIONS = {
    # 游戏进度事件
    EVENT_ENTER_NETHER: "进入下界",
    EVENT_FIND_BASTION: "找到堡垒遗迹",
    EVENT_FIND_FORTRESS: "找到下界要塞",
    EVENT_FOLLOW_EYE: "前往要塞",
    EVENT_ENTER_END: "进入末地",
    EVENT_DRAGON_DEATH: "末影龙死亡",
    # 死亡事件
    EVENT_DEATH: "死亡",
    EVENT_DEATH_SPAWNPOINT: "重生点死亡",
}

# 游戏进度事件顺序（用于过滤重复事件）
PROGRESS_EVENTS_ORDER = [
    EVENT_ENTER_NETHER,
    EVENT_FIND_BASTION,
    EVENT_FIND_FORTRESS,
    EVENT_FOLLOW_EYE,
    EVENT_ENTER_END,
    EVENT_DRAGON_DEATH,
]

# 片段类型映射（从事件A到事件B）
SEGMENT_TYPES = {
    ("start", EVENT_ENTER_NETHER): "overworld",  # 主世界到下界
    (EVENT_ENTER_NETHER, EVENT_FIND_BASTION): "nether_to_bastion",  # 下界到堡垒
    (EVENT_FIND_BASTION, EVENT_FIND_FORTRESS): "bastion_to_fortress",  # 堡垒到要塞
    (EVENT_FIND_FORTRESS, EVENT_FOLLOW_EYE): "fortress_to_eye",  # 要塞到末影之眼
    (EVENT_FOLLOW_EYE, EVENT_ENTER_END): "eye_to_end",  # 末影之眼到末地
    (EVENT_ENTER_END, EVENT_DRAGON_DEATH): "end_to_dragon",  # 末地到击杀末影龙
}

# 片段描述
SEGMENT_DESCRIPTIONS = {
    "overworld": "主世界",
    "nether_to_bastion": "下界到堡垒",
    "bastion_to_fortress": "堡垒到要塞",
    "fortress_to_eye": "要塞到末影之眼",
    "eye_to_end": "末影之眼到末地",
    "end_to_dragon": "末地到击杀末影龙",
}


class ClipExtractor:
    """从比赛数据中提取剪辑时刻"""

    def __init__(self, buffer_before: int = 10, buffer_after: int = 5):
        """
        Args:
            buffer_before: 事件前缓冲秒数
            buffer_after: 事件后缓冲秒数
        """
        self.buffer_before = buffer_before
        self.buffer_after = buffer_after

    def extract_moments(
        self,
        match: dict,
        target_user: str = None,
        event_types: set = None,
        max_duration: int = None,
        deduplicate_progress: bool = True,
    ) -> list[ClipMoment]:
        """从比赛中提取剪辑时刻

        Args:
            match: 比赛详情数据
            target_user: 目标用户名（None 表示所有玩家）
            event_types: 要提取的事件类型（None 表示所有支持的事件）
            max_duration: 最大比赛时长（秒），超过则跳过
            deduplicate_progress: 是否对进度事件去重（只保留每个类型的第一个实例）

        Returns:
            剪辑时刻列表
        """
        if event_types is None:
            event_types = SUPPORTED_EVENTS

        moments = []

        # 构建玩家 UUID 到昵称的映射
        uuid_to_name = {p["uuid"]: p["nickname"] for p in match["players"]}

        # 构建 VOD 映射
        vod_map = {v["uuid"]: v for v in match.get("vod", [])}

        # 比赛结束时间（Unix 秒）
        match_end_time = match["date"]
        # 比赛持续时间（毫秒）
        match_duration_ms = match["result"]["time"]
        # 比赛开始时间（Unix 秒）
        match_start_time = match_end_time - match_duration_ms / 1000

        # 检查比赛时长
        if max_duration and match_duration_ms / 1000 > max_duration:
            return []

        # 用于去重的集合：(玩家UUID, 事件类型)
        seen_progress = set()

        # 遍历时间线（按时间排序）
        timelines = sorted(match.get("timelines", []), key=lambda t: t["time"])

        for timeline in timelines:
            event_type = timeline["type"]

            # 只处理支持的事件类型
            if event_type not in event_types:
                continue

            player_uuid = timeline["uuid"]
            event_time_ms = timeline["time"]  # 相对于比赛开始的毫秒数

            # 过滤目标用户
            player_name = uuid_to_name.get(player_uuid, "Unknown")
            if target_user and player_name.lower() != target_user.lower():
                continue

            # 对进度事件去重
            if deduplicate_progress and event_type in PROGRESS_EVENTS_ORDER:
                key = (player_uuid, event_type)
                if key in seen_progress:
                    continue
                seen_progress.add(key)

            # 获取玩家对应的 VOD
            vod = vod_map.get(player_uuid)
            if not vod:
                continue

            # 计算 VOD 时间戳
            # event_time_ms 是相对于比赛开始的毫秒数
            # match_start_time 是比赛开始的 Unix 时间戳（秒）
            # vod["startsAt"] 是 VOD 开始的 Unix 时间戳（秒）
            event_absolute_unix = match_start_time + event_time_ms / 1000
            vod_start_unix = vod["startsAt"]
            vod_timestamp = int(event_absolute_unix - vod_start_unix)

            # 应用缓冲
            start_seconds = max(0, vod_timestamp - self.buffer_before)
            end_seconds = vod_timestamp + self.buffer_after

            # 生成描述
            event_desc = EVENT_DESCRIPTIONS.get(event_type, event_type)
            description = f"{player_name} - {event_desc}"

            moments.append(ClipMoment(
                match_id=match["id"],
                event_type=event_type,
                player_name=player_name,
                vod_url=vod["url"],
                vod_start_seconds=start_seconds,
                vod_end_seconds=end_seconds,
                description=description,
            ))

        return moments

    def extract_segments(
        self,
        match: dict,
        target_user: str = None,
        max_duration: int = None,
    ) -> list[SegmentMoment]:
        """从比赛中提取连续片段

        Args:
            match: 比赛详情数据
            target_user: 目标用户名（None 表示所有玩家）
            max_duration: 最大比赛时长（秒），超过则跳过

        Returns:
            连续片段列表
        """
        segments = []

        # 提取堡垒类型（从 seed.nether 字段）
        bastion_type = None
        overworld_type = None
        seed = match.get("seed")
        if seed:
            if seed.get("nether"):
                bastion_type = seed["nether"]
            if seed.get("overworld"):
                overworld_type = seed["overworld"]

        # 构建玩家 UUID 到昵称的映射
        uuid_to_name = {p["uuid"]: p["nickname"] for p in match["players"]}

        # 构建 VOD 映射
        vod_map = {v["uuid"]: v for v in match.get("vod", [])}

        # 比赛结束时间（Unix 秒）
        match_end_time = match["date"]
        # 比赛持续时间（毫秒）
        match_duration_ms = match["result"]["time"]
        # 比赛开始时间（Unix 秒）
        match_start_time = match_end_time - match_duration_ms / 1000

        # 检查比赛时长
        if max_duration and match_duration_ms / 1000 > max_duration:
            return []

        # 按玩家分组处理时间线
        player_timelines = {}
        for timeline in match.get("timelines", []):
            player_uuid = timeline["uuid"]
            player_name = uuid_to_name.get(player_uuid, "Unknown")

            # 过滤目标用户
            if target_user and player_name.lower() != target_user.lower():
                continue

            if player_uuid not in player_timelines:
                player_timelines[player_uuid] = []
            player_timelines[player_uuid].append(timeline)

        # 对每个玩家的时间线进行处理
        for player_uuid, timelines in player_timelines.items():
            player_name = uuid_to_name.get(player_uuid, "Unknown")

            # 获取玩家对应的 VOD
            vod = vod_map.get(player_uuid)
            if not vod:
                continue

            # 按时间排序
            timelines.sort(key=lambda t: t["time"])

            # 提取进度事件
            progress_events = []
            seen_events = set()

            for timeline in timelines:
                event_type = timeline["type"]

                # 只处理进度事件
                if event_type not in PROGRESS_EVENTS_ORDER:
                    continue

                # 去重
                if event_type in seen_events:
                    continue
                seen_events.add(event_type)

                # 计算 VOD 时间戳
                event_time_ms = timeline["time"]
                event_absolute_unix = match_start_time + event_time_ms / 1000
                vod_start_unix = vod["startsAt"]
                vod_timestamp = int(event_absolute_unix - vod_start_unix)

                progress_events.append({
                    "type": event_type,
                    "vod_timestamp": vod_timestamp,
                    "description": EVENT_DESCRIPTIONS.get(event_type, event_type),
                })

            # 生成连续片段
            # 第一个片段：从比赛开始到第一个进度事件
            if progress_events:
                first_event = progress_events[0]
                segment_type = SEGMENT_TYPES.get(("start", first_event["type"]))

                if segment_type:
                    # 计算比赛开始的 VOD 时间戳
                    match_start_vod = int(match_start_time - vod["startsAt"])

                    segments.append(SegmentMoment(
                        match_id=match["id"],
                        segment_type=segment_type,
                        player_name=player_name,
                        vod_url=vod["url"],
                        vod_start_seconds=max(0, match_start_vod - self.buffer_before),
                        vod_end_seconds=first_event["vod_timestamp"] + self.buffer_after,
                        description=f"{player_name} - {SEGMENT_DESCRIPTIONS.get(segment_type, segment_type)}",
                        start_event="比赛开始",
                        end_event=first_event["description"],
                        bastion_type=bastion_type,
                        overworld_type=overworld_type,
                    ))

            # 后续片段：从事件A到事件B
            for i in range(len(progress_events) - 1):
                current_event = progress_events[i]
                next_event = progress_events[i + 1]

                segment_type = SEGMENT_TYPES.get((current_event["type"], next_event["type"]))

                if segment_type:
                    segments.append(SegmentMoment(
                        match_id=match["id"],
                        segment_type=segment_type,
                        player_name=player_name,
                        vod_url=vod["url"],
                        vod_start_seconds=current_event["vod_timestamp"] - self.buffer_before,
                        vod_end_seconds=next_event["vod_timestamp"] + self.buffer_after,
                        description=f"{player_name} - {SEGMENT_DESCRIPTIONS.get(segment_type, segment_type)}",
                        start_event=current_event["description"],
                        end_event=next_event["description"],
                        bastion_type=bastion_type,
                        overworld_type=overworld_type,
                    ))

        return segments
