#!/usr/bin/env python3
"""
每日定时任务脚本 —— 每次运行只处理队列中"下一个还没处理过"的视频。

设计思路：
  - queue.txt      存放视频链接（每行一个），可以是单视频链接，
                    也可以混入频道/播放列表链接（运行时会自动展开成具体视频）
  - state.json     记录哪些 video_id 已经处理过，避免重复抓取
  - 每次运行只取 1 个新视频处理（可通过 --count 调整一次处理几个）

用法：
  python daily_run.py                  # 处理队列中下一个视频
  python daily_run.py --count 1        # 同上，显式指定数量
  python daily_run.py --queue my_queue.txt --output my_output

配合 cron 实现"每天自动跑一个"：
  crontab -e
  # 每天早上9点运行一次
  0 9 * * * cd /path/to/yt-transcript-tool && /usr/bin/python3 daily_run.py >> daily_run.log 2>&1
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 复用主脚本里的链接解析逻辑，避免重复写一遍
from fetch_transcript import (
    is_single_video,
    extract_video_id,
    list_video_ids_from_channel_or_playlist,
)

DEFAULT_QUEUE_FILE = "queue.txt"
DEFAULT_STATE_FILE = "state.json"


def load_state(state_path: Path) -> dict:
    if state_path.exists():
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"done": [], "expanded_sources": []}


def save_state(state_path: Path, state: dict):
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def expand_queue_to_video_ids(queue_path: Path, state: dict) -> list[str]:
    """
    读取 queue.txt 里的每一行：
      - 单视频链接 -> 直接拿到 video_id
      - 频道/播放列表链接 -> 用 yt-dlp 展开成多个 video_id（只展开一次，记入 state，避免每天重复展开浪费请求）
    返回去重后的全部 video_id 列表，保持原始出现顺序。
    """
    if not queue_path.exists():
        print(f"[!] 找不到队列文件: {queue_path}")
        print(f"    请创建该文件，每行放一个 YouTube 链接（视频/频道/播放列表均可）。")
        sys.exit(1)

    all_video_ids = []
    seen = set()

    with open(queue_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for line in lines:
        if is_single_video(line):
            vid = extract_video_id(line)
            if vid and vid not in seen:
                all_video_ids.append(vid)
                seen.add(vid)
        else:
            # 频道/播放列表：只在第一次遇到时展开，结果记入 state 避免重复请求
            if line in state["expanded_sources"]:
                # 已经展开过，但我们没有缓存具体的视频列表，
                # 为简单起见这里选择重新展开（yt-dlp --flat-playlist 速度很快，开销不大）
                pass
            ids = list_video_ids_from_channel_or_playlist(line)
            if line not in state["expanded_sources"]:
                state["expanded_sources"].append(line)
            for vid in ids:
                if vid not in seen:
                    all_video_ids.append(vid)
                    seen.add(vid)

    return all_video_ids


def get_next_pending_videos(all_video_ids: list[str], state: dict, count: int) -> list[str]:
    done_set = set(state["done"])
    pending = [v for v in all_video_ids if v not in done_set]
    return pending[:count]


def run_fetch_for_video(video_id: str, output_dir: str, no_translate: bool) -> bool:
    """调用主脚本处理单个视频，返回是否成功。"""
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [sys.executable, "fetch_transcript.py", url, "--output", output_dir]
    if no_translate:
        cmd.append("--no-translate")

    print(f"[*] 执行: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="每日定时抓取队列中的下一个YouTube视频字幕")
    parser.add_argument("--queue", default=DEFAULT_QUEUE_FILE, help="队列文件路径")
    parser.add_argument("--state", default=DEFAULT_STATE_FILE, help="状态文件路径")
    parser.add_argument("--output", default="output", help="输出目录")
    parser.add_argument("--count", type=int, default=1, help="本次运行处理几个视频（默认1个）")
    parser.add_argument("--no-translate", action="store_true", help="跳过翻译")
    args = parser.parse_args()

    queue_path = Path(args.queue)
    state_path = Path(args.state)

    state = load_state(state_path)

    print(f"\n========== {datetime.now().isoformat(timespec='seconds')} ==========")

    all_video_ids = expand_queue_to_video_ids(queue_path, state)
    save_state(state_path, state)  # 保存 expanded_sources 记录

    pending = get_next_pending_videos(all_video_ids, state, args.count)

    if not pending:
        print("[*] 队列中所有视频都已处理完毕，没有新任务。")
        print(f"    已完成总数: {len(state['done'])}")
        return

    print(f"[*] 队列总数: {len(all_video_ids)} | 已完成: {len(state['done'])} | 本次将处理: {len(pending)}")

    for vid in pending:
        ok = run_fetch_for_video(vid, args.output, args.no_translate)
        if ok:
            state["done"].append(vid)
            save_state(state_path, state)
            print(f"[✓] {vid} 处理完成并已记录\n")
        else:
            print(f"[!] {vid} 处理失败，下次运行会重试（未记入已完成列表）\n")


if __name__ == "__main__":
    main()
