"""Phase 0 基线工具（已按重构后的架构改造）。

历史说明：P0 时这些脚本记录的是「修复前的错误行为」（红）。
现在它们断言「修复后的正确行为」（绿）。修复前的红证据保留在
``docs/BASELINE-REPORT.md`` 与 git 历史（提交 97a2737）。
"""

import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from core.cards import Card, Suit, full_deck  # noqa: E402
from core.evaluator import evaluate  # noqa: E402
from core.strength import beats_probability, table_size  # noqa: E402

SUITS = ["SPADE", "HEART", "DIAMOND", "CLUB"]
RANKS = list(range(2, 15))


def hand(*specs):
    """hand(("SPADE", 14), ("HEART", 14), ("DIAMOND", 14))"""
    return tuple(Card(Suit[s], r) for s, r in specs)


def h(title):
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"\n         {detail}" if detail else ""))
    return ok


def summary(code, passed, failed, notes=""):
    print()
    print("-" * 74)
    print(f"BASELINE_RESULT {code}: passed={passed} failed={failed}")
    if notes:
        print(f"NOTE: {notes}")
    print("-" * 74)


__all__ = [
    "Card",
    "Suit",
    "full_deck",
    "evaluate",
    "beats_probability",
    "table_size",
    "hand",
    "h",
    "check",
    "summary",
]
