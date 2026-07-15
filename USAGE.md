# MCSR 自动剪辑工具 - 使用说明

## 快速参考

| 我想要... | 命令 |
|-----------|------|
| 主世界到进入下界 | `--segments overworld` |
| 下界到堡垒 | `--segments nether_to_bastion` |
| 堡垒到要塞 | `--segments bastion_to_fortress` |
| 要塞到末影之眼 | `--segments fortress_to_eye` |
| 末影之眼到末地 | `--segments eye_to_end` |
| 末地到击杀末影龙 | `--segments end_to_dragon` |
| 全部分段 | 不加 `--segments` 参数 |

## 基本用法

```bash
python -m src.cli <输入> [选项]
```

## 输入方式

### 1. 按选手名字

```bash
python -m src.cli doogile --twitch-cli ./TwitchDownloaderCLI.exe
```

### 2. 按链接（自动提取比赛 ID）

```bash
python -m src.cli https://mcsrranked.com/stats/doogile/11642805 --twitch-cli ./TwitchDownloaderCLI.exe
```

### 3. 指定单个比赛 ID

```bash
python -m src.cli doogile --match 11642805 --twitch-cli ./TwitchDownloaderCLI.exe
```

### 4. 指定多个比赛 ID（用于重试失败的比赛）

```bash
python -m src.cli doogile --match-ids 11642293,11414950,11413845,11077250 --twitch-cli ./TwitchDownloaderCLI.exe
```

## 筛选比赛

### 处理最近 N 场比赛

```bash
python -m src.cli doogile --count 5 --twitch-cli ./TwitchDownloaderCLI.exe
```

### 处理最近 N 天的比赛

```bash
# 最近 3 天的比赛
python -m src.cli doogile --days 3 --twitch-cli ./TwitchDownloaderCLI.exe

# 最近 7 天的比赛
python -m src.cli doogile --days 7 --twitch-cli ./TwitchDownloaderCLI.exe
```

### 处理指定时间段的比赛

```bash
# 30-60 天前的比赛
python -m src.cli doogile --days-from 60 --days-to 30 --twitch-cli ./TwitchDownloaderCLI.exe

# 7-3 天前的比赛
python -m src.cli doogile --days-from 7 --days-to 3 --twitch-cli ./TwitchDownloaderCLI.exe
```

### 指定赛季

```bash
python -m src.cli doogile --season 10 --twitch-cli ./TwitchDownloaderCLI.exe
```

## 选择片段

### 剪辑全分段（默认）

```bash
python -m src.cli doogile --twitch-cli ./TwitchDownloaderCLI.exe
```

### 只剪辑特定片段

```bash
# 只剪辑主世界和末地到击杀末影龙
python -m src.cli doogile --segments overworld end_to_dragon --twitch-cli ./TwitchDownloaderCLI.exe

# 只剪辑下界到堡垒
python -m src.cli doogile --segments nether_to_bastion --twitch-cli ./TwitchDownloaderCLI.exe
```

### 可用片段类型

| 参数 | 游戏阶段 | 说明 |
|------|----------|------|
| `overworld` | 开局 → 进入下界 | 主世界阶段（挖钻石、做装备、找地狱门） |
| `nether_to_bastion` | 进入下界 → 找到堡垒 | 下界赶路到堡垒 |
| `bastion_to_fortress` | 找到堡垒 → 找到要塞 | 拿残骸、烈焰棒 |
| `fortress_to_eye` | 找到要塞 → 跟随末影之眼 | 做末影之眼、找要塞 |
| `eye_to_end` | 跟随末影之眼 → 进入末地 | 进入末地传送门 |
| `end_to_dragon` | 进入末地 → 击杀末影龙 | 打龙阶段 |

### 常用组合

```bash
# 只要开局（主世界到进入下界）
.\mcsr-clip doogile --segments overworld

# 只要下界部分（进入下界到找到要塞）
.\mcsr-clip doogile --segments nether_to_bastion bastion_to_fortress

# 只要末地部分（进入末地到击杀末影龙）
.\mcsr-clip doogile --segments eye_to_end end_to_dragon

# 除了主世界都要
.\mcsr-clip doogile --segments nether_to_bastion bastion_to_fortress fortress_to_eye eye_to_end end_to_dragon
```

### 开局类型

主世界片段会自动加上开局类型前缀：

| 类型 | 说明 |
|------|------|
| `VILLAGE` | 村庄开局 |
| `SHIPWRECK` | 沉船开局 |
| `DESERT_TEMPLE` | 沙漠神殿开局 |
| `RUINED_PORTAL` | 废弃传送门开局 |
| `BURIED_TREASURE` | 埋藏宝藏开局 |

示例文件名：
- `VILLAGE_overworld_match_11642805.mp4`
- `SHIPWRECK_overworld_match_11413845.mp4`

### 堡垒类型

堡垒相关片段会自动加上堡垒类型前缀：

| 类型 | 说明 |
|------|------|
| `TREASURE` | 宝藏室 |
| `STABLES` | 马厩 |
| `BRIDGE` | 桥梁 |
| `HOUSING` | 住宅区 |

示例文件名：
- `TREASURE_bastion_to_fortress_match_11413845.mp4`
- `HOUSING_bastion_to_fortress_match_11642805.mp4`

## 输出选项

### 指定输出目录

```bash
python -m src.cli doogile --output my_clips --twitch-cli ./TwitchDownloaderCLI.exe
```

### 调整缓冲时间

```bash
python -m src.cli doogile --buffer-before 15 --buffer-after 10 --twitch-cli ./TwitchDownloaderCLI.exe
```

## 其他选项

### 预览模式（不实际剪辑）

```bash
python -m src.cli doogile --dry-run
```

### 列出所有片段类型

```bash
python -m src.cli dummy --list-segments
```

## 完整示例

```bash
# 示例 1: 剪辑 doogile 的特定比赛的全分段
python -m src.cli https://mcsrranked.com/stats/doogile/11642805 --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 2: 剪辑 doogile 最近 3 场比赛的主世界和末地片段
python -m src.cli doogile --count 3 --segments overworld end_to_dragon --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 3: 预览 caqen 最近 5 场比赛
python -m src.cli caqen --count 5 --dry-run

# 示例 4: 剪辑特定比赛的下界到堡垒片段
python -m src.cli doogile --match 11642805 --segments nether_to_bastion --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 5: 剪辑近 3 天 doogile 比赛的堡垒到要塞部分
python -m src.cli doogile --days 3 --segments bastion_to_fortress --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 6: 剪辑近 7 天所有比赛的全分段
python -m src.cli doogile --days 7 --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 7: 剪辑 30-60 天前的比赛（已下载过最近 30 天的）
python -m src.cli doogile --days-from 60 --days-to 30 --segments bastion_to_fortress --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 8: 剪辑 7-3 天前的比赛
python -m src.cli doogile --days-from 7 --days-to 3 --segments bastion_to_fortress --twitch-cli ./TwitchDownloaderCLI.exe

# 示例 9: 重试失败的比赛
python -m src.cli doogile --match-ids 11414950,11413845,11077250 --segments bastion_to_fortress --twitch-cli ./TwitchDownloaderCLI.exe
```

## 输出结构

```
output/
└── <选手名>/
    └── <日期>/
        ├── TREASURE_bastion_to_fortress_match_11413845.mp4
        ├── HOUSING_bastion_to_fortress_match_11642805.mp4
        ├── BRIDGE_bastion_to_fortress_match_10958444.mp4
        ├── overworld_match_11642805.mp4
        ├── nether_to_bastion_match_11642805.mp4
        └── ...
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

1. **请求延迟**: 片段间延迟 2秒，比赛间延迟 3秒，避免请求过快
2. **失败重试**: 使用 `--match-ids` 参数重试失败的比赛
3. **VOD 有效期**: Twitch VOD 有效期为 14 天（普通主播）或 60 天（合作伙伴）
4. **磁盘空间**: 视频文件较大，请确保有足够的磁盘空间
5. **只筛选 Rank**: 默认只筛选 Ranked 比赛（type=2）

## Windows 快捷脚本

```bash
.\mcsr-clip doogile
.\mcsr-clip https://mcsrranked.com/stats/doogile/11642805
.\mcsr-clip doogile --segments bastion_to_fortress
.\mcsr-clip doogile --days 3 --segments bastion_to_fortress
.\mcsr-clip doogile --days-from 60 --days-to 30 --segments bastion_to_fortress
```
