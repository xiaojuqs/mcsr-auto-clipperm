"""重命名已有文件，添加开局类型前缀"""
import asyncio
import os
import re
from pathlib import Path

from src.mcsr_api import McsrApiClient


async def rename_files(output_dir: str = "output"):
    """重命名 overworld 文件，添加开局类型前缀"""
    api = McsrApiClient()

    # 收集所有需要重命名的文件
    files_to_rename = []

    for root, dirs, files in os.walk(output_dir):
        for file in files:
            # 匹配 overworld_match_XXXXX.mp4 格式
            match = re.match(r"overworld_match_(\d+)\.mp4", file)
            if match:
                match_id = match.group(1)
                filepath = Path(root) / file
                files_to_rename.append((match_id, filepath))

    if not files_to_rename:
        print("没有找到需要重命名的文件")
        return

    print(f"找到 {len(files_to_rename)} 个文件需要重命名")

    # 按比赛 ID 分组，避免重复请求
    match_ids = list(set(f[0] for f in files_to_rename))
    print(f"需要查询 {len(match_ids)} 个比赛的开局类型")

    # 获取开局类型
    overworld_types = {}
    for i, match_id in enumerate(match_ids, 1):
        try:
            detail = await api.get_match_detail(match_id)
            seed = detail.get("seed")
            if seed and seed.get("overworld"):
                overworld_types[match_id] = seed["overworld"]
            print(f"\r[INFO] 查询进度: {i}/{len(match_ids)}", end="", flush=True)
        except Exception as e:
            print(f"\n[WARN] 获取比赛 {match_id} 失败: {e}")

    print()

    # 重命名文件
    renamed = 0
    skipped = 0

    for match_id, filepath in files_to_rename:
        if match_id not in overworld_types:
            print(f"[SKIP] {filepath.name} - 没有开局类型信息")
            skipped += 1
            continue

        overworld_type = overworld_types[match_id]
        new_name = f"{overworld_type}_overworld_match_{match_id}.mp4"
        new_path = filepath.parent / new_name

        if new_path.exists():
            print(f"[SKIP] {new_name} - 目标文件已存在")
            skipped += 1
            continue

        try:
            filepath.rename(new_path)
            print(f"[OK] {filepath.name} -> {new_name}")
            renamed += 1
        except Exception as e:
            print(f"[ERROR] 重命名失败: {e}")

    print(f"\n完成！重命名 {renamed} 个文件，跳过 {skipped} 个文件")

    await api.close()


if __name__ == "__main__":
    asyncio.run(rename_files())
