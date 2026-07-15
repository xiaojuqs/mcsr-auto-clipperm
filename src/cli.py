"""MCSR Rank 比赛自动剪辑工具 - CLI 入口"""
import asyncio
import argparse
import re
import sys
from pathlib import Path
from datetime import datetime

from .mcsr_api import McsrApiClient, McsrApiError
from .clip_extractor import ClipExtractor, SEGMENT_DESCRIPTIONS
from .video_processor import VideoProcessor, VideoProcessorError


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        prog="mcsr-clip",
        description="MCSR Rank 比赛自动剪辑工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:

  # 按选手名字剪辑
  python -m src.cli doogile --twitch-cli ./TwitchDownloaderCLI.exe

  # 按链接剪辑（自动提取比赛 ID）
  python -m src.cli https://mcsrranked.com/stats/doogile/11642805 --twitch-cli ./TwitchDownloaderCLI.exe

  # 只剪辑特定比赛
  python -m src.cli doogile --match 11642805 --twitch-cli ./TwitchDownloaderCLI.exe

  # 剪辑最近 5 场比赛
  python -m src.cli doogile --count 5 --twitch-cli ./TwitchDownloaderCLI.exe

  # 只剪辑特定片段
  python -m src.cli doogile --segments overworld nether_to_bastion --twitch-cli ./TwitchDownloaderCLI.exe

  # 只剪辑单个片段
  python -m src.cli doogile --segments fortress_to_eye --twitch-cli ./TwitchDownloaderCLI.exe

  # 预览模式
  python -m src.cli doogile --dry-run

可用片段类型:
  overworld          - 主世界（比赛开始 → 进入下界）
  nether_to_bastion  - 下界到堡垒
  bastion_to_fortress - 堡垒到要塞
  fortress_to_eye    - 要塞到末影之眼
  eye_to_end         - 末影之眼到末地
  end_to_dragon      - 末地到击杀末影龙
        """,
    )

    # 输入参数
    parser.add_argument(
        "input",
        help="选手名字或 MCSR Ranked 链接",
    )

    # 筛选参数
    parser.add_argument(
        "--match", "-m",
        help="指定单个比赛 ID（从链接中提取或手动指定）",
    )
    parser.add_argument(
        "--match-ids",
        help="指定多个比赛 ID，用逗号分隔（用于重试失败的比赛）",
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=10,
        help="处理的比赛数量（默认 10）",
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        help="只处理最近 N 天的比赛",
    )
    parser.add_argument(
        "--days-from",
        type=int,
        help="从 N 天前开始（配合 --days-to 使用）",
    )
    parser.add_argument(
        "--days-to",
        type=int,
        help="到 N 天前结束（配合 --days-from 使用）",
    )
    parser.add_argument(
        "--season", "-s",
        type=int,
        help="赛季号",
    )

    # 片段选择
    parser.add_argument(
        "--segments",
        nargs="+",
        choices=[
            "overworld", "nether_to_bastion", "bastion_to_fortress",
            "fortress_to_eye", "eye_to_end", "end_to_dragon",
        ],
        help="要剪辑的片段类型（默认全部）",
    )

    # 输出参数
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="输出目录（默认 output）",
    )
    parser.add_argument(
        "--twitch-cli",
        default="TwitchDownloaderCLI",
        help="TwitchDownloaderCLI 路径",
    )
    parser.add_argument(
        "--buffer-before",
        type=int,
        default=10,
        help="片段前缓冲秒数（默认 10）",
    )
    parser.add_argument(
        "--buffer-after",
        type=int,
        default=5,
        help="片段后缓冲秒数（默认 5）",
    )

    # 其他选项
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际剪辑",
    )
    parser.add_argument(
        "--list-segments",
        action="store_true",
        help="列出所有可用片段类型",
    )

    return parser.parse_args()


def extract_match_id_from_url(url: str) -> tuple[str, str] | None:
    """从 MCSR Ranked 链接中提取用户名和比赛 ID

    支持格式:
    - https://mcsrranked.com/stats/doogile/11642805
    - https://mcsrranked.com/stats/doogile/11642805?matches=ranked
    - mcsrranked.com/stats/doogile/11642805

    Returns:
        (username, match_id) 或 None
    """
    pattern = r'mcsrranked\.com/stats/([^/]+)/(\d+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2)
    return None


def extract_username(input_str: str) -> str:
    """从输入中提取用户名

    支持格式:
    - 纯用户名: doogile
    - Twitch 链接: https://www.twitch.tv/doogile
    - MCSR 链接: https://mcsrranked.com/stats/doogile/...
    """
    # 尝试从 MCSR 链接提取
    result = extract_match_id_from_url(input_str)
    if result:
        return result[0]

    # 尝试从 Twitch 链接提取
    twitch_pattern = r'twitch\.tv/([^/?]+)'
    match = re.search(twitch_pattern, input_str)
    if match:
        return match.group(1)

    # 假设是纯用户名
    return input_str.strip()


async def main():
    """主函数"""
    args = parse_args()

    # 列出片段类型
    if args.list_segments:
        print("可用片段类型:")
        for name, desc in SEGMENT_DESCRIPTIONS.items():
            print(f"  {name:25s} - {desc}")
        return

    # 解析输入
    username = extract_username(args.input)

    # 从链接中提取比赛 ID
    match_id_from_url = None
    result = extract_match_id_from_url(args.input)
    if result:
        match_id_from_url = result[1]

    # 确定比赛 ID
    match_id = args.match or match_id_from_url
    match_ids = None
    if args.match_ids:
        match_ids = [id.strip() for id in args.match_ids.split(",")]

    # 初始化组件
    api = McsrApiClient()
    extractor = ClipExtractor(
        buffer_before=args.buffer_before,
        buffer_after=args.buffer_after,
    )
    processor = VideoProcessor(args.twitch_cli)

    print(f"[INFO] 选手: {username}")
    if match_ids:
        print(f"[INFO] 比赛 ID: {', '.join(match_ids)}")
    elif match_id:
        print(f"[INFO] 比赛 ID: {match_id}")
    elif args.days_from and args.days_to:
        print(f"[INFO] 处理 {args.days_from}-{args.days_to} 天前的比赛")
    elif args.days:
        print(f"[INFO] 处理最近 {args.days} 天的比赛")
    else:
        print(f"[INFO] 处理最近 {args.count} 场比赛")

    try:
        # 获取比赛列表
        if match_ids:
            # 获取多个特定比赛
            matches_to_process = []
            for mid in match_ids:
                try:
                    detail = await api.get_match_detail(mid)
                    matches_to_process.append(detail)
                except McsrApiError as e:
                    print(f"[WARN] 获取比赛 {mid} 失败: {e}")
        elif match_id:
            # 获取特定比赛
            try:
                detail = await api.get_match_detail(match_id)
                matches_to_process = [detail]
            except McsrApiError as e:
                print(f"[ERROR] 获取比赛 {match_id} 失败: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # 获取用户比赛列表
            # 如果按天数筛选，需要获取更多比赛
            need_more = args.days or (args.days_from and args.days_to)
            fetch_count = 500 if need_more else args.count
            match_list = await api.get_user_matches(
                username,
                count=fetch_count,
                season=args.season,
                match_type=2,  # 只获取 Ranked 比赛
            )

            if not match_list:
                print(f"[INFO] 没有找到 {username} 的有 VOD 的比赛")
                return

            # 按天数筛选
            if args.days_from and args.days_to:
                from datetime import timedelta
                now = datetime.now()
                # days_from 是更早的时间（如 60天前）
                # days_to 是更晚的时间（如 30天前）
                from_time = now - timedelta(days=args.days_from)
                to_time = now - timedelta(days=args.days_to)
                from_timestamp = from_time.timestamp()
                to_timestamp = to_time.timestamp()
                match_list = [m for m in match_list if from_timestamp <= m["date"] <= to_timestamp]
                print(f"[INFO] 找到 {len(match_list)} 场 {args.days_from}-{args.days_to} 天前有 VOD 的比赛")
            elif args.days:
                from datetime import timedelta
                cutoff_time = datetime.now() - timedelta(days=args.days)
                cutoff_timestamp = cutoff_time.timestamp()
                match_list = [m for m in match_list if m["date"] >= cutoff_timestamp]
                print(f"[INFO] 找到 {len(match_list)} 场最近 {args.days} 天有 VOD 的比赛")
            else:
                print(f"[INFO] 找到 {len(match_list)} 场有 VOD 的比赛")

            if not match_list:
                print(f"[INFO] 没有找到符合条件的比赛")
                return

            # 获取每场比赛的详情
            matches_to_process = []
            for i, m in enumerate(match_list, 1):
                try:
                    detail = await api.get_match_detail(m["id"])
                    matches_to_process.append(detail)
                    if len(match_list) > 10:
                        print(f"\r[INFO] 获取比赛详情: {i}/{len(match_list)}", end="", flush=True)
                except McsrApiError as e:
                    print(f"[WARN] 获取比赛 {m['id']} 详情失败: {e}")
            if len(match_list) > 10:
                print()  # 换行

        total_clips = 0
        failed_clips = 0
        failed_match_ids: list[str] = []

        for i, detail in enumerate(matches_to_process, 1):
            match_id_str = detail["id"]
            match_date = datetime.fromtimestamp(detail["date"]).strftime("%Y-%m-%d %H:%M")
            print(f"\n[{i}/{len(matches_to_process)}] 比赛 {match_id_str} ({match_date})...")

            # 提取连续片段
            segments = extractor.extract_segments(
                detail,
                target_user=username,
            )

            if not segments:
                print("  [INFO] 没有找到符合条件的连续片段")
                continue

            # 筛选指定片段
            if args.segments:
                segments = [s for s in segments if s.segment_type in args.segments]
                if not segments:
                    print(f"  [INFO] 没有找到指定类型的片段: {args.segments}")
                    continue

            print(f"  [INFO] 找到 {len(segments)} 个片段")

            # 剪辑每个片段
            for j, segment in enumerate(segments):
                # 生成输出路径
                date_str = datetime.fromtimestamp(detail["date"]).strftime("%Y%m%d")
                output_dir = Path(args.output) / username / date_str

                # 文件名格式：类型_片段类型_match_比赛ID
                filename_parts = []
                # 添加类型前缀
                if segment.segment_type == "overworld" and segment.overworld_type:
                    # 主世界片段加开局类型
                    filename_parts.append(segment.overworld_type)
                elif segment.bastion_type and segment.segment_type in ["nether_to_bastion", "bastion_to_fortress"]:
                    # 堡垒相关片段加堡垒类型
                    filename_parts.append(segment.bastion_type)
                filename_parts.append(segment.segment_type)
                filename_parts.append(f"match_{match_id_str}")
                output_file = output_dir / f"{'_'.join(filename_parts)}.mp4"

                if args.dry_run:
                    print(f"  [DRY-RUN] {segment.description}")
                    print(f"           从: {segment.start_event}")
                    print(f"           到: {segment.end_event}")
                    print(f"           时间: {segment.vod_start_seconds}s - {segment.vod_end_seconds}s")
                    print(f"           输出: {output_file}")
                    total_clips += 1
                    continue

                print(f"  [INFO] {segment.description}")
                print(f"         {segment.start_event} -> {segment.end_event}")
                print(f"         时间: {segment.vod_start_seconds}s - {segment.vod_end_seconds}s")

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
                    match_id_str = str(match_id_str)
                    if match_id_str not in failed_match_ids:
                        failed_match_ids.append(match_id_str)

                # 片段间延迟，避免请求过快
                if j < len(segments) - 1:
                    await asyncio.sleep(2)

            # 比赛间延迟
            await asyncio.sleep(3)

        # 显示总结
        print("\n" + "=" * 50)
        if args.dry_run:
            print(f"[DRY-RUN] 将剪辑 {total_clips} 个片段")
        else:
            print(f"[完成] 剪辑 {total_clips} 个片段")
            if failed_clips > 0:
                print(f"[失败] {failed_clips} 个片段剪辑失败")
                failed_ids_str = [str(id) for id in failed_match_ids]
                print(f"\n失败的比赛 ID: {', '.join(failed_ids_str)}")

                # 构建重试命令
                segments_args = ""
                if args.segments:
                    segments_args = f" --segments {' '.join(args.segments)}"
                print(f"\n重试命令:")
                print(f"  .\\mcsr-clip {username} --match-ids {','.join(failed_ids_str)}{segments_args}")
        print("=" * 50)

    except McsrApiError as e:
        print(f"[ERROR] MCSR API 错误: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断")
        if failed_match_ids:
            failed_ids_str = [str(id) for id in failed_match_ids]
            print(f"\n已失败的比赛 ID: {', '.join(failed_ids_str)}")
            segments_args = ""
            if args.segments:
                segments_args = f" --segments {' '.join(args.segments)}"
            print(f"\n重试命令:")
            print(f"  .\\mcsr-clip {username} --match-ids {','.join(failed_ids_str)}{segments_args}")
        sys.exit(0)
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
