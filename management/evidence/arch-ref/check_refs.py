"""校验 ARCHITECTURE.md 中的 file:line 引用是否仍指向同一内容。输出写文件，不灌上下文。"""
import re, sys, pathlib, json
from collections import defaultdict

import os
REPO = pathlib.Path(os.environ.get("ARCH_REF_REPO", "/home/kipley/Documents/code/learning/game_rendering"))
DOC = REPO / "docs/ARCHITECTURE.md"
OUT = pathlib.Path("/tmp/audit/stale_refs.json")
OUT_MD = pathlib.Path("/tmp/audit/stale_refs.md")

text = DOC.read_text(encoding="utf-8")
lines = text.splitlines()

# 匹配 file.ext:123 或 file.ext:123-456
pat = re.compile(r'([A-Za-z0-9_./-]+\.(?:py|md|toml|json|yml|yaml|txt)):(\d+)(?:-(\d+))?')
refs = []
for i, ln in enumerate(lines, 1):
    for m in pat.finditer(ln):
        f, a, b = m.group(1), int(m.group(2)), m.group(3)
        refs.append((i, f, a, int(b) if b else a, m.group(0)))

# 建立 basename -> 候选路径索引（处理文档中的裸文件名引用，如 rules.py:31）
from collections import defaultdict as _dd
_INDEX = _dd(list)
for _p in REPO.rglob("*"):
    try:
        _rel = _p.relative_to(REPO)
    except ValueError:
        continue
    _r = str(_rel)
    # 只排除 REPO 内部的 .git/.pi/management 与隐藏目录；REPO 本身可能是 worktree
    if _p.is_file() and not _r.startswith((".git", ".pi", "management")) and not _r.startswith("."):
        _INDEX[_p.name].append(_p)


def resolve(f):
    f2 = f.lstrip("./")
    if "/" in f2:
        c = REPO / f2
        if c.exists():
            return c
        for c in _INDEX.get(pathlib.Path(f2).name, []):
            if str(c).endswith(f2):
                return c
        return None
    cands = _INDEX.get(f2, [])
    if not cands:
        return None
    if len(cands) == 1:
        return cands[0]
    # 多个同名候选：取 .py 优先且不在 management/docs 下的那个
    py = [c for c in cands if c.suffix == ".py"]
    if len(py) == 1:
        return py[0]
    return cands[0]


missing_file = defaultdict(list)
out_of_range = defaultdict(list)
ok = 0
for dline, f, a, b, raw in refs:
    p = resolve(f)
    if p is None:
        missing_file[f].append((dline, raw))
        continue
    n = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    if a < 1 or b > n:
        out_of_range[f].append({"doc_line": dline, "ref": raw, "file_lines": n})
    else:
        ok += 1

result = {
    "total_refs": len(refs),
    "in_range": ok,
    "missing_file": {k: v for k, v in missing_file.items()},
    "out_of_range": out_of_range,
}
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

md = [f"# 失效引用清单（自动生成）", "", f"- 总引用数: **{len(refs)}**", f"- 行号在范围内: **{ok}**",
      f"- 文件不存在: **{len(missing_file)}** 个文件 / {sum(len(v) for v in missing_file.values())} 处",
      f"- 行号越界: **{len(out_of_range)}** 个文件 / {sum(len(v) for v in out_of_range.values())} 处", "",
      "## 越界明细", ""]
for f, items in sorted(out_of_range.items()):
    md.append(f"### {f}（文件共 {items[0]['file_lines']} 行）")
    md.append("| 文档行 | 引用 | 实际行数 |")
    md.append("|---|---|---|")
    for it in items:
        md.append(f"| {it['doc_line']} | `{it['ref']}` | {it['file_lines']} |")
    md.append("")
md.append("## 文件不存在明细")
md.append("")
for f, items in sorted(missing_file.items()):
    md.append(f"- `{f}`: " + ", ".join(f"文档行{d} `{r}`" for d, r in items))
OUT_MD.write_text("\n".join(md), encoding="utf-8")
print(f"总引用 {len(refs)} | 范围内 {ok} | 越界 {sum(len(v) for v in out_of_range.values())} 处 | 文件缺失 {sum(len(v) for v in missing_file.values())} 处")
print(f"已写入 {OUT_MD}")
