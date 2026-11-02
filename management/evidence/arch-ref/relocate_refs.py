"""为 ARCHITECTURE.md 的失效引用自动重定位新行号。输出 JSON + Markdown 清单。"""
import re, subprocess, json
from collections import defaultdict
from pathlib import Path
REPO = Path("/home/kipley/Documents/code/learning/game_rendering")
BASE = "6bd6253"
stale = json.load(open("/tmp/audit/stale_content.json"))

def norm(s):
    return re.sub(r'\s+', ' ', s.strip())

def locate(rel, old_line, old_total):
    """在当前文件里找 old_line 的内容，返回新行号候选。"""
    p = REPO / rel
    new = p.read_text(encoding="utf-8", errors="replace").splitlines()
    target = norm(old_line)
    if not target or target in ("", '"""', "'''"):
        return None, "empty"
    exact = [i+1 for i,l in enumerate(new) if norm(l) == target]
    if len(exact) == 1:
        return exact[0], "exact"
    if len(exact) > 1:
        # 多个匹配：选离旧行号最近的
        return min(exact, key=lambda x: abs(x-old_total)), "exact-multi"
    # 退化：包含匹配
    part = target[:60]
    contains = [i+1 for i,l in enumerate(new) if part and part in norm(l)]
    if len(contains) == 1:
        return contains[0], "contains"
    if len(contains) > 1:
        return min(contains, key=lambda x: abs(x-old_total)), "contains-multi"
    return None, "not-found"

fixed, unresolved = [], []
for s in stale:
    old_line = s["old_line"]
    if len(old_line) >= 88:  # 被截断过，从 git 重新取原文
        rel = s["file"]
        old = subprocess.run(["git","show",f"{BASE}:{rel}"],capture_output=True,text=True).stdout.splitlines()
        a = int(s["ref"].split(":")[1].split("-")[0])
        old_line = old[a-1] if a-1 < len(old) else old_line
    new_line, how = locate(s["file"], old_line, s["old_total"])
    rec = dict(s); rec["old_line_full"] = old_line.strip()[:120]
    if new_line:
        rec["new_line"] = new_line; rec["match"] = how; fixed.append(rec)
    else:
        rec["reason"] = how; unresolved.append(rec)

json.dump({"fixed":fixed,"unresolved":unresolved}, open("/tmp/audit/relocated.json","w"), ensure_ascii=False, indent=2)

md=["# ARCHITECTURE.md 引用重定位清单","",
    f"- 自动定位成功: **{len(fixed)}** / {len(stale)}", f"- 需人工确认: **{len(unresolved)}**","",
    "## 可自动应用的修正", "", "| 文档行 | 旧引用 | 新引用 | 匹配方式 |", "|---|---|---|---|"]
for r in sorted(fixed, key=lambda x:(x["file"], x["doc_line"])):
    a=s["ref"].split(":")[1] if False else r["ref"].split(":",1)[1]
    old_num=a.split("-")[0]
    new_ref=f"{r['file']}:{r['new_line']}"
    if "-" in a:
        new_ref=f"{r['file']}:{r['new_line']}-{r['new_line']}"
    md.append(f"| {r['doc_line']} | `{r['ref']}` | `{new_ref}` | {r['match']} |")
md+=["","## 需人工确认",""]
for r in unresolved:
    md.append(f"- 文档行 {r['doc_line']} `{r['ref']}` — {r.get('reason')} — 旧内容 `{r['old_line_full'][:70]}`")
Path("/tmp/audit/relocated.md").write_text("\n".join(md), encoding="utf-8")
print(f"自动定位成功 {len(fixed)} / {len(stale)}；需人工确认 {len(unresolved)}")
print("已写入 /tmp/audit/relocated.md 与 relocated.json")
