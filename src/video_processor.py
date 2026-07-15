"""视频处理器 - 封装 TwitchDownloaderCLI"""
import os
import subprocess
from pathlib import Path


class VideoProcessorError(Exception):
    """视频处理错误"""
    pass


class VideoProcessor:
    """TwitchDownloaderCLI 封装"""

    def __init__(self, twitch_downloader_path: str = "TwitchDownloaderCLI"):
        """
        Args:
            twitch_downloader_path: TwitchDownloaderCLI 可执行文件路径
        """
        self.cli_path = twitch_downloader_path

    def clip_vod(
        self,
        vod_url: str,
        start_seconds: int,
        end_seconds: int,
        output_path: str,
        quality: str = None,
    ) -> str:
        """从 VOD 中剪辑片段

        Args:
            vod_url: Twitch VOD URL
            start_seconds: 开始时间（秒）
            end_seconds: 结束时间（秒）
            output_path: 输出文件路径
            quality: 视频质量（如 "1080p60"）

        Returns:
            输出文件路径

        Raises:
            VideoProcessorError: 剪辑失败时抛出
        """
        # 从 URL 提取 VOD ID
        vod_id = self._extract_vod_id(vod_url)

        # 格式化时间为 hh:mm:ss
        start_time = self._format_time(start_seconds)
        end_time = self._format_time(end_seconds)

        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 构建命令
        cmd = [
            self.cli_path,
            "videodownload",
            "--id", vod_id,
            "-b", start_time,
            "-e", end_time,
            "-o", output_path,
            "--collision", "Overwrite",
        ]

        if quality:
            cmd.extend(["-q", quality])

        # 执行命令
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 分钟超时
            )
        except subprocess.TimeoutExpired:
            raise VideoProcessorError("TwitchDownloaderCLI 执行超时")
        except FileNotFoundError:
            raise VideoProcessorError(
                f"找不到 TwitchDownloaderCLI: {self.cli_path}\n"
                "请确保已安装并将路径添加到 PATH 环境变量，或使用 --twitch-cli 参数指定路径"
            )

        if result.returncode != 0:
            raise VideoProcessorError(f"TwitchDownloaderCLI 错误:\n{result.stderr}")

        return output_path

    def _extract_vod_id(self, vod_url: str) -> str:
        """从 Twitch VOD URL 提取 ID

        支持格式:
        - https://www.twitch.tv/videos/123456789
        - https://www.twitch.tv/videos/123456789?t=123s
        - 123456789 (直接 ID)
        """
        if "/videos/" in vod_url:
            return vod_url.split("/videos/")[-1].split("?")[0].split("/")[0]
        # 假设是直接的 ID
        return vod_url.strip()

    def _format_time(self, seconds: int) -> str:
        """将秒数格式化为 hh:mm:ss

        Args:
            seconds: 秒数

        Returns:
            格式化的时间字符串
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def check_availability(self) -> bool:
        """检查 TwitchDownloaderCLI 是否可用

        Returns:
            是否可用
        """
        try:
            result = subprocess.run(
                [self.cli_path, "--help"],
                capture_output=True,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
