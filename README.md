# MCSR Auto Clipper

自动从 Twitch VOD 中剪辑 MCSR Rank 比赛的连贯进度片段。

## 功能特性

- 自动识别游戏进度事件（进入下界、堡垒、要塞、末地等）
- 输出连续片段，而非单独时刻
- 自动标注开局类型（VILLAGE、SHIPWRECK 等）
- 自动标注堡垒类型（TREASURE、STABLES、BRIDGE、HOUSING）
- 支持按选手名字、链接、比赛 ID 筛选
- 支持按时间范围筛选
- 失败自动输出重试命令

## 安装

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 下载 TwitchDownloaderCLI

从 [TwitchDownloader Releases](https://github.com/lay295/TwitchDownloader/releases/latest) 下载对应平台的可执行文件，放到项目目录。

### 3. 安装 FFmpeg

```bash
TwitchDownloaderCLI ffmpeg --download
```

## 快速开始

```bash
# 按选手名字剪辑
python -m src.cli doogile --twitch-cli ./TwitchDownloaderCLI.exe

# 按链接剪辑
python -m src.cli https://mcsrranked.com/stats/doogile/11642805

# 预览模式
python -m src.cli doogile --dry-run
```

### Windows 快捷脚本

```powershell
.\mcsr-clip doogile
.\mcsr-clip doogile --segments bastion_to_fortress
```

## 使用说明

详见 [USAGE.md](USAGE.md)

## 片段类型

| 参数 | 游戏阶段 | 说明 |
|------|----------|------|
| `overworld` | 开局 → 进入下界 | 主世界阶段 |
| `nether_to_bastion` | 进入下界 → 找到堡垒 | 下界赶路 |
| `bastion_to_fortress` | 找到堡垒 → 找到要塞 | 拿残骸、烈焰棒 |
| `fortress_to_eye` | 找到要塞 → 跟随末影之眼 | 做末影之眼 |
| `eye_to_end` | 跟随末影之眼 → 进入末地 | 进入传送门 |
| `end_to_dragon` | 进入末地 → 击杀末影龙 | 打龙阶段 |

## 开局类型

| 类型 | 说明 |
|------|------|
| `VILLAGE` | 村庄开局 |
| `SHIPWRECK` | 沉船开局 |
| `DESERT_TEMPLE` | 沙漠神殿开局 |
| `RUINED_PORTAL` | 废弃传送门开局 |
| `BURIED_TREASURE` | 埋藏宝藏开局 |

## 堡垒类型

| 类型 | 说明 |
|------|------|
| `TREASURE` | 宝藏室 |
| `STABLES` | 马厩 |
| `BRIDGE` | 桥梁 |
| `HOUSING` | 住宅区 |

## 输出文件名格式

```
VILLAGE_overworld_match_11642805.mp4
TREASURE_bastion_to_fortress_match_11413845.mp4
HOUSING_bastion_to_fortress_match_11642805.mp4
```

## 命令行参数

```
python -m src.cli <输入> [选项]

位置参数:
  input                 选手名字或 MCSR Ranked 链接

筛选选项:
  --match, -m MATCH     指定单个比赛 ID
  --match-ids IDS       指定多个比赛 ID，用逗号分隔
  --count, -c COUNT     处理的比赛数量（默认 10）
  --days, -d DAYS       只处理最近 N 天的比赛
  --days-from DAYS      从 N 天前开始（配合 --days-to 使用）
  --days-to DAYS        到 N 天前结束（配合 --days-from 使用）
  --season, -s SEASON   赛季号

片段选择:
  --segments SEGMENTS   要剪辑的片段类型（默认全部）

输出选项:
  --output, -o OUTPUT   输出目录（默认 output）
  --twitch-cli PATH     TwitchDownloaderCLI 路径
  --buffer-before SEC   片段前缓冲秒数（默认 10）
  --buffer-after SEC    片段后缓冲秒数（默认 5）

其他选项:
  --dry-run             预览模式，不实际剪辑
  --list-segments       列出所有可用片段类型
```

## 输出结构

```
output/
└── <选手名>/
    └── <日期>/
        ├── VILLAGE_overworld_match_11642805.mp4
        ├── HOUSING_nether_to_bastion_match_11642805.mp4
        ├── HOUSING_bastion_to_fortress_match_11642805.mp4
        ├── fortress_to_eye_match_11642805.mp4
        ├── eye_to_end_match_11642805.mp4
        └── end_to_dragon_match_11642805.mp4
```

## 失败重试

当剪辑失败时，程序会自动输出失败的比赛 ID 和重试命令：

```
[失败] 3 个片段剪辑失败

失败的比赛 ID: 11414950, 11413845, 11077250

重试命令:
  .\mcsr-clip doogile --match-ids 11414950,11413845,11077250 --segments bastion_to_fortress
```

即使按 Ctrl+C 中断，也会输出已失败的比赛 ID。

## 注意事项

1. **只筛选 Rank**: 默认只筛选 Ranked 比赛（type=2）
2. **请求延迟**: 片段间延迟 2秒，比赛间延迟 3秒，避免请求过快
3. **VOD 有效期**: Twitch VOD 有效期为 14 天（普通主播）或 60 天（合作伙伴）
4. **磁盘空间**: 视频文件较大，请确保有足够的磁盘空间

## 参考资源

- [MCSR Ranked API 文档](https://docs.mcsrranked.com)
- [TwitchDownloaderCLI](https://github.com/lay295/TwitchDownloader)

## 许可证

MIT
