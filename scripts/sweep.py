#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only OR PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 天川澪 (Coko_Iya). Part of MioVRCA: https://github.com/CokoIya/MioVRC_AssetManager (terms in LICENSE.md)
"""定时任务（每 6 小时，也可以在 Actions 页面手动运行）：

1. 点赞：作品的点赞就是作品议题上的 👍。读取所有带「作品」标签的议题（每 100 个一次请求），写入 likes.json，
   重建 works.json。
2. 补上漏掉的：同时提交的议题较多时，GitHub 可能取消排队中的运行。还开着、没有任何回复、提交超过 15 分钟的名片
   （AUTO_PROFILES 开启时）、删除作品和作品（AUTO_WORKS 开启时）在这里补上处理。要回复的内容写入 --replies 指定的
   文件，由工作流在提交之后回复。

需要环境变量 GITHUB_TOKEN 和 GITHUB_REPOSITORY（工作流自带）。只用 Python 标准库发请求。
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import accept_issue  # noqa: E402
import rebuild  # noqa: E402
from rebuild import ROOT, issues, rebuild_works  # noqa: E402

WAIT = datetime.timedelta(minutes=15)  # 刚提交的议题留给它自己的运行


def count_likes():
    total = rebuild.count_likes()
    rebuild_works(refresh_likes=False)
    return total


def created_at(it):
    try:
        return datetime.datetime.strptime(it.get("created_at") or "", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except ValueError:
        return datetime.datetime.now(datetime.timezone.utc)


def missed(auto_profiles, auto_works, now=None):
    """还开着、没人回复过、提交了一会儿的议题，像刚提交时一样处理。返回要回复的 [{number, body, close}]。"""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    replies, seen = [], set()
    for label in (["名片"] if auto_profiles else []) + ["作品"]:
        for it in issues(label, "open"):
            if it["number"] in seen or it.get("comments", 0) > 0 or now - created_at(it) < WAIT:
                continue
            seen.add(it["number"])
            try:
                outcome, msg = accept_issue.handle(it, "sweep", "", auto_profiles, auto_works)
            except accept_issue.Refused as e:
                replies.append({"number": it["number"], "body": accept_issue.refusal(e), "close": False})
                continue
            if outcome == "close":
                replies.append({"number": it["number"], "body": msg, "close": True})
    return replies


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replies", default="replies.json", help="要回复的议题写到这里")
    a = ap.parse_args()
    auto_profiles = accept_issue.flag(os.environ.get("AUTO_PROFILES"), True)
    auto_works = accept_issue.flag(os.environ.get("AUTO_WORKS"), False)
    total = count_likes()
    replies = missed(auto_profiles, auto_works)
    with open(a.replies, "w", encoding="utf-8") as f:
        json.dump(replies, f, ensure_ascii=False)
    print("点赞共 %d 个；补上处理的议题 %d 个" % (total, len(replies)))


if __name__ == "__main__":
    main()
