"""校验 ARCHITECTURE.md 中的 file:line 引用是否越界或文件缺失。

用法：
    ARCH_REF_REPO=<repo 路径> python check_refs.py

输出写文件到 /tmp/audit/，只把摘要打印到 stdout（避免灌满子 Agent 上下文）。
"""

import json
import os
import pathlib
import re
from collections import defaultdict

REPO = pathlib.Path(
    os.environ.get("ARCH_REF_REPO", "/home/kipley/Documents/code/learning/game_rendering")
)
DOC = REPO / "docs/ARCHITECTURE.md"
OUT = pathlib.Path("/tmp/audit/stale_refs.json")
OUT_MD = pathlib.Path("/tmp/audit/stale_refs.md")

REF_PATTERN = re.compile(
    r"([A-Za-z0-9_./-]+\.(?:py|md|toml|json|yml|yaml|txt)):(\d+)(?:-(\d+))?"
)


def build_index(root: pathlib.Path) -> dict:
    """建立 basename -> 候选路径索引（处理文档中的裸文件名引用，如 rules.py:31）。"""
    index: dict = defaultdict(list)
    for path in root.rglob("*"):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        # 只排除 REPO 内部的隐藏目录与治理目录；REPO 本身可能是 worktree
        if path.is_file() and not rel.startswith((".", "management")):
            index[path.name].append(path)
    return index


INDEX = build_index(REPO)


def resolve(ref: str):
    """把引用里的文件名解析为仓库内的实际路径。"""
    name = ref.lstrip("./")
    if "/" in name:
        direct = REPO / name
        if direct.exists():
            return direct
        for candidate in INDEX.get(pathlib.Path(name).name, []):
            if str(candidate).endswith(name):
                return candidate
        return None
    candidates = INDEX.get(name, [])
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    python_files = [c for c in candidates if c.suffix == ".py"]
    if len(python_files) == 1:
        return python_files[0]
    return candidates[0]


def main() -> None:
    lines = DOC.read_text(encoding="utf-8").splitlines()
    refs = []
    for line_no, line in enumerate(lines, 1):
        for match in REF_PATTERN.finditer(line):
            start = int(match.group(2))
            end = int(match.group(3)) if match.group(3) else start
            refs.append((line_no, match.group(1), start, end, match.group(0)))

    missing: dict = defaultdict(list)
    out_of_range: dict = defaultdict(list)
    in_range = 0
    for doc_line, name, start, end, raw in refs:
        path = resolve(name)
        if path is None:
            missing[name].append((doc_line, raw))
            continue
        total = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if start < 1 or end > total:
            out_of_range[str(path.relative_to(REPO))].append(
                {"doc_line": doc_line, "ref": raw, "file_lines": total}
            )
        else:
            in_range += 1

    result = {
        "total_refs": len(refs),
        "in_range": in_range,
        "missing_file": {k: v for k, v in missing.items()},
        "out_of_range": {k: v for k, v in out_of_range.items()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# 失效引用清单（自动生成）",
        "",
        f"- 总引用数: **{len(refs)}**",
        f"- 行号在范围内: **{in_range}**",
        f"- 文件不存在: **{len(missing)}** 个文件 / {sum(len(v) for v in missing.values())} 处",
        f"- 行号越界: **{len(out_of_range)}** 个文件 / {sum(len(v) for v in out_of_range.values())} 处",
        "",
        "## 越界明细",
        "",
    ]
    for name, items in sorted(out_of_range.items()):
        md.append(f"### {name}（文件共 {items[0]['file_lines']} 行）")
        md.append("| 文档行 | 引用 | 实际行数 |")
        md.append("|---|---|---|")
        for item in items:
            md.append(f"| {item['doc_line']} | `{item['ref']}` | {item['file_lines']} |")
        md.append("")
    md.append("## 文件不存在明细")
    md.append("")
    for name, items in sorted(missing.items()):
        detail = ", ".join(f"文档行{line} `{raw}`" for line, raw in items)
        md.append(f"- `{name}`: {detail}")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(
        f"总引用 {len(refs)} | 范围内 {in_range} | "
        f"越界 {sum(len(v) for v in out_of_range.values())} 处 | "
        f"文件缺失 {sum(len(v) for v in missing.values())} 处"
    )
    print(f"已写入 {OUT_MD}")


if __name__ == "__main__":
    main()
