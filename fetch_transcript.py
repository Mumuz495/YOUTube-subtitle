#!/usr/bin/env python3
"""Command-line entry for the YouTube transcript study tool."""

from __future__ import annotations

import argparse
import json
import sys

from transcript_tool import (
    DEFAULT_OUTPUT_DIR,
    extract_video_id,
    is_single_video,
    list_video_ids_from_channel_or_playlist,
    process_url,
)

__all__ = [
    "extract_video_id",
    "is_single_video",
    "list_video_ids_from_channel_or_playlist",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="YouTube 字幕抓取 + 双语跟读稿生成")
    parser.add_argument("url", help="YouTube 视频、频道或播放列表链接")
    parser.add_argument("--no-translate", action="store_true", help="跳过中文翻译，只抓原文字幕")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="输出目录，默认 output/")
    parser.add_argument("--limit", type=int, default=None, help="频道/播放列表最多处理几个视频")
    args = parser.parse_args()

    try:
        result = process_url(
            args.url,
            output_root=args.output,
            translate=not args.no_translate,
            limit=args.limit,
        )
    except Exception as exc:
        print(f"[!] 失败：{exc}", file=sys.stderr)
        return 1

    for warning in result["warnings"]:
        print(f"[!] {warning}")

    for item in result["results"]:
        if item["ok"]:
            print(f"[OK] {item['video_id']}：{item['count']} 条字幕")
            for name, path in item["files"].items():
                print(f"     {name}: {path}")
        else:
            print(f"[SKIP] {item['video_id']}：{item['error']}")

    print(json.dumps({"output_root": result["output_root"], "videos": result["video_ids"]}, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
