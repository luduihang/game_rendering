"""为 ARCHITECTURE.md 的失效引用自动重定位新行号。

用法：
    python relocate_refs.py

输入：/tmp/audit/stale_content.json（由上一阶段的比对产生）
输出：/tmp/audit/relocated.json 与 /tmp/audit/relocated.md
"""

import json
import pathlib
import re
import subprocess

BASE = "6bd6253"  # 重构前基线
REPO = pathlib.Path("/home/kipley/Documents/code/learning/game_rendering")
STALE = pathlib.Path("/tmp/audit/stale_content.json")
OUT_JSON = pathlib.Path("/tmp/audit/relocated.json")
OUT_MD = pathlib.Path("/tmp/audit/relocated.md")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def locate(rel: str, old_line: str, old_total: int):
    """在当前文件里找 old_line 的内容，返回新行号候选。"""
    path = REPO / rel
    new = path.read_text(encoding="utf-8", errors="replace").splitlines()
    target = normalize(old_line)
    if not target or target in ('"""', "'''"):
        return None, "empty"

    exact = [i + 1 for i, line in enumerate(new) if normalize(line) == target]
    if len(exact) == 1:
        return exact[0], "exact"
    if len(exact) > 1:
        return min(exact, key=lambda x: abs(x - old_total)), "exact-multi"

    part = target[:60]
    contains = [i + 1 for i, line in enumerate(new) if part and part in normalize(line)]
    if len(contains) == 1:
        return contains[0], "contains"
    if len(contains) > 1:
        return min(contains, key=lambda x: abs(x - old_total)), "contains-multi"
    return None, "not-found"


def main() -> None:
    stale = json.loads(STALE.read_text(encoding="utf-8"))
    fixed = []
    unresolved = []

    for item in stale:
        old_line = item["old_line"]
        if len(old_line) >= 88:  # 之前被截断过，从 git 重新取原文
            rel = item["file"]
            old = subprocess.run(
                ["git", "show", f"{BASE}:{rel}"],
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            start = int(item["ref"].split(":")[1].split("-")[0])
            old_line = old[start - 1] if start - 1 < len(old) else old_line

        new_line, how = locate(item["file"], old_line, item["old_total"])
        record = dict(item)
        record["old_line_full"] = old_line.strip()[:120]
        if new_line:
            record["new_line"] = new_line
            record["match"] = how
            fixed.append(record)
        else:
            record["reason"] = how
            unresolved.append(record)

    OUT_JSON.write_text(
        json.dumps({"fixed": fixed, "unresolved": unresolved}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = [
        "# ARCHITECTURE.md 引用重定位清单",
        "",
        f"- 自动定位成功: **{len(fixed)}** / {len(stale)}",
        f"- 需人工确认: **{len(unresolved)}**",
        "",
        "## 可自动应用的修正",
        "",
        "| 文档行 | 旧引用 | 新引用 | 匹配方式 |",
        "|---|---|---|---|",
    ]
    for record in sorted(fixed, key=lambda x: (x["file"], x["doc_line"])):
        old_num = record["ref"].split(":", 1)[1]
        new_ref = f"{record['file']}:{record['new_line']}"
        if "-" in old_num:
            new_ref = f"{record['file']}:{record['new_line']}-{record['new_line']}"
        md.append(
            f"| {record['doc_line']} | `{record['ref']}` | `{new_ref}` | {record['match']} |"
        )
    md += ["", "## 需人工确认", ""]
    for record in unresolved:
        md.append(
            f"- 文档行 {record['doc_line']} `{record['ref']}` — {record.get('reason')} — "
            f"旧内容 `{record['old_line_full'][:70]}`"
        )
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(
        f"自动定位成功 {len(fixed)} / {len(stale)}；需人工确认 {len(unresolved)}"
    )
    print(f"已写入 {OUT_MD} 与 {OUT_JSON}")


if __name__ == "__main__":
    main()
