"""MCSR Rank 比赛自动剪辑工具 - 主程序"""
import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

from .mcsr_api import McsrApiClient, McsrApiError
from .clip_extractor import (
    ClipExtractor, SUPPORTED_EVENTS, EVENT_DESCRIPTIONS,
    EVENT_ENTER_NETHER, EVENT_FIND_BASTION, EVENT_FIND_FORTRESS,
    EVENT_FOLLOW_EYE, EVENT_ENTER_END, EVENT_DRAGON_DEATH,
    EVENT_DEATH, EVENT_DEATH_SPAWNPOINT,
)
from .clip_extractor import SegmentMoment
from .video_processor import VideoProcessor, VideoProcessorError


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="MCSR Rank 比赛自动剪辑工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 剪辑指定用户的最近 10 场比赛
  python -m src.main Dream --count 10

  # 剪辑指定赛季的比赛
  python -m src.main Dream --season 10

  # 只剪辑死亡事件
  python -m src.main Dream --events death

  # 指定输出目录和 TwitchDownloaderCLI 路径
  python -m src.main Dream --output clips --twitch-cli ./TwitchDownloaderCLI

支持的事件类型:
  death      - 玩家死亡
  nether     - 进入下界
  bastion    - 到达堡垒
  fortress   - 到达要塞
  stronghold - 到达末地要塞
  end        - 进入末地
  dragon     - 击杀末影龙
        """,
    )
    parser.add_argument("username", help="Minecraft 用户名")
    parser.add_argument("--count", type=int, default=20, help="处理的比赛数量（默认 20）")
    parser.add_argument("--season", type=int, help="赛季号（不指定则使用当前赛季）")
    parser.add_argument("--output", default="output", help="输出目录（默认 output）")
    parser.add_argument(
        "--twitch-cli",
        default="TwitchDownloaderCLI",
        help="TwitchDownloaderCLI 路径（默认 TwitchDownloaderCLI）",
    )
    parser.add_argument(
        "--events",
        nargs="+",
        choices=[
            "nether", "bastion", "fortress", "eye", "end", "dragon",
            "death", "death_spawnpoint",
            "progress",  # 所有进度事件
        ],
        help="要剪辑的事件类型（默认全部）",
    )
    parser.add_argument("--buffer-before", type=int, default=10, help="事件前缓冲秒数（默认 10）")
    parser.add_argument("--buffer-after", type=int, default=5, help="事件后缓冲秒数（默认 5）")
    parser.add_argument("--max-duration", type=int, help="最大比赛时长（秒），超过则跳过")
    parser.add_argument("--dry-run", action="store_true", help="只显示将要剪辑的内容，不实际执行")
    parser.add_argument(
        "--mode",
        choices=["moments", "segments"],
        default="segments",
        help="剪辑模式：moments=单个时刻，segments=连续片段（默认）",
    )
    return parser.parse_args()


def map_event_types(events: list[str] | None) -> set[str] | None:
    """将简短的事件名称映射为完整的事件类型"""
    if not events:
        return None

    event_map = {
        # 游戏进度事件
        "nether": EVENT_ENTER_NETHER,
        "bastion": EVENT_FIND_BASTION,
        "fortress": EVENT_FIND_FORTRESS,
        "eye": EVENT_FOLLOW_EYE,
        "end": EVENT_ENTER_END,
        "dragon": EVENT_DRAGON_DEATH,
        # 死亡事件
        "death": EVENT_DEATH,
        "death_spawnpoint": EVENT_DEATH_SPAWNPOINT,
    }

    # 特殊选项：所有进度事件
    if "progress" in events:
        return {
            EVENT_ENTER_NETHER,
            EVENT_FIND_BASTION,
            EVENT_FIND_FORTRESS,
            EVENT_FOLLOW_EYE,
            EVENT_ENTER_END,
            EVENT_DRAGON_DEATH,
        }

    return {event_map[e] for e in events}


async def main():
    """主函数"""
    args = parse_args()

    # 初始化组件
    api = McsrApiClient()
    extractor = ClipExtractor(
        buffer_before=args.buffer_before,
        buffer_after=args.buffer_after,
    )
    processor = VideoProcessor(args.twitch_cli)

    # 映射事件类型
    event_types = map_event_types(args.events)

    print(f"[INFO] 正在获取 {args.username} 的比赛数据...")

    try:
        # 获取比赛列表
        matches = await api.get_user_matches(
            args.username,
            count=args.count,
            season=args.season,
        )
        print(f"[INFO] 找到 {len(matches)} 场有 VOD 的比赛")

        if not matches:
            print("[INFO] 没有找到有 VOD 的比赛")
            return

        total_clips = 0
        failed_clips = 0

        for i, match in enumerate(matches, 1):
            match_id = match["id"]
            match_date = datetime.fromtimestamp(match["date"]).strftime("%Y-%m-%d %H:%M")
            print(f"\n[{i}/{len(matches)}] 处理比赛 {match_id} ({match_date})...")

            # 获取比赛详情（含时间线）
            try:
                detail = await api.get_match_detail(match_id)
            except McsrApiError as e:
                print(f"  [ERROR] 获取比赛详情失败: {e}")
                continue

            # 根据模式提取内容
            if args.mode == "segments":
                # 连续片段模式
                segments = extractor.extract_segments(
                    detail,
                    target_user=args.username,
                    max_duration=args.max_duration,
                )

                if not segments:
                    print("  [INFO] 没有找到符合条件的连续片段")
                    continue

                print(f"  [INFO] 找到 {len(segments)} 个连续片段")

                # 剪辑每个片段
                for segment in segments:
                    # 生成输出路径
                    date_str = datetime.fromtimestamp(detail["date"]).strftime("%Y%m%d")
                    output_dir = Path(args.output) / args.username / date_str
                    output_file = output_dir / f"match_{match_id}_{segment.segment_type}.mp4"

                    if args.dry_run:
                        print(f"  [DRY-RUN] {segment.description}")
                        print(f"           VOD: {segment.vod_url}")
                        print(f"           时间: {segment.vod_start_seconds}s - {segment.vod_end_seconds}s")
                        print(f"           从: {segment.start_event}")
                        print(f"           到: {segment.end_event}")
                        print(f"           输出: {output_file}")
                        total_clips += 1
                        continue

                    print(f"  [INFO] 剪辑: {segment.description}")
                    print(f"         VOD: {segment.vod_url}")
                    print(f"         时间: {segment.vod_start_seconds}s - {segment.vod_end_seconds}s")
                    print(f"         从: {segment.start_event} -> {segment.end_event}")

                    try:
                        processor.clip_vod(
                            vod_url=segment.vod_url,
                            start_seconds=segment.vod_start_seconds,
                            end_seconds=segment.vod_end_seconds,
                            output_path=str(output_file),
                        )
                        print(f"         输出: {output_file}")
                        total_clips += 1
                    except VideoProcessorError as e:
                        print(f"  [ERROR] 剪辑失败: {e}")
                        failed_clips += 1

            else:
                # 单个时刻模式
                moments = extractor.extract_moments(
                    detail,
                    target_user=args.username,
                    event_types=event_types,
                    max_duration=args.max_duration,
                )

                if not moments:
                    print("  [INFO] 没有找到符合条件的关键时刻")
                    continue

                print(f"  [INFO] 找到 {len(moments)} 个关键时刻")

                # 剪辑每个时刻
                for moment in moments:
                    # 生成输出路径
                    date_str = datetime.fromtimestamp(detail["date"]).strftime("%Y%m%d")
                    output_dir = Path(args.output) / args.username / date_str
                    output_file = output_dir / f"match_{match_id}_{moment.event_type}_{moment.vod_start_seconds}.mp4"

                    if args.dry_run:
                        print(f"  [DRY-RUN] {moment.description}")
                        print(f"           VOD: {moment.vod_url}")
                        print(f"           时间: {moment.vod_start_seconds}s - {moment.vod_end_seconds}s")
                        print(f"           输出: {output_file}")
                        total_clips += 1
                        continue

                    print(f"  [INFO] 剪辑: {moment.description}")
                    print(f"         VOD: {moment.vod_url}")
                    print(f"         时间: {moment.vod_start_seconds}s - {moment.vod_end_seconds}s")

                    try:
                        processor.clip_vod(
                            vod_url=moment.vod_url,
                            start_seconds=moment.vod_start_seconds,
                            end_seconds=moment.vod_end_seconds,
                            output_path=str(output_file),
                        )
                        print(f"         输出: {output_file}")
                        total_clips += 1
                    except VideoProcessorError as e:
                        print(f"  [ERROR] 剪辑失败: {e}")
                        failed_clips += 1

            # API 限流保护
            await asyncio.sleep(1)

        # 显示总结
        print("\n" + "=" * 50)
        print(f"[完成] 共处理 {len(matches)} 场比赛")
        if args.dry_run:
            print(f"[DRY-RUN] 将剪辑 {total_clips} 个片段")
        else:
            print(f"[成功] 剪辑 {total_clips} 个片段")
            if failed_clips > 0:
                print(f"[失败] {failed_clips} 个片段剪辑失败")
        print("=" * 50)

    except McsrApiError as e:
        print(f"[ERROR] MCSR API 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INFO] 用户中断")
        sys.exit(0)
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
