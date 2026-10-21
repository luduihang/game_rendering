"""D6 复现：发牌分布是否偏离均匀。

Cards.draw_cards_plus()：抽 3 组候选（各 3 张），算每组强度，只保留最强的一组，
其余 6 张弃置不回堆 → 双方手牌来自「3 次抽样取最大」的有偏分布。

量化方法：用穷举 22100 手得到的精确强度表，把任一手牌映射到它的「分位」
（击败了多少比例的手牌）。均匀发牌的期望分位分布 ≈ U(0,1)（均值 0.5）。
"""

import numpy as np
from common import check, exact_value_table, h, hand_percentile, summary

from card_deck import Cards


def sample_percentiles(table, kind, n):
    deck = Cards()
    deck.shuffle_deck()
    out = []
    need = 3 if kind == "uniform" else 9
    for _ in range(n):
        if len(deck.cards) < need:
            deck.reset_deck()
            deck.shuffle_deck()
        hand = deck.draw_cards(3) if kind == "uniform" else deck.draw_cards_plus(3)
        out.append(hand_percentile(table, hand))
    return np.array(out)


def describe(name, arr):
    print(f"  {name:22s} n={len(arr)} 均值={arr.mean():.3f} "
          f"中位={np.median(arr):.3f} p25={np.percentile(arr,25):.3f} "
          f"p75={np.percentile(arr,75):.3f} 最强档(>0.95)占比={(arr>0.95).mean():.3f}")


def main():
    h("D6 发牌分布：draw_cards_plus 相对均匀发牌的偏置")

    table = exact_value_table()
    print(f"精确手牌强度表：穷举 {len(table)} 手（C(52,3)）\n")

    n = 150
    uniform = sample_percentiles(table, "uniform", n)
    biased = sample_percentiles(table, "biased", n)

    describe("均匀 draw_cards(3)", uniform)
    describe("draw_cards_plus(3)", biased)

    print()
    ok_uniform = abs(uniform.mean() - 0.5) < 0.08
    check("均匀发牌的分位均值应≈0.5", ok_uniform, f"实际 {uniform.mean():.3f}")

    shift = biased.mean() - uniform.mean()
    ok_biased_detected = shift > 0.10
    check("draw_cards_plus 应被检出显著偏强（均值上移）", ok_biased_detected,
          f"均值差 {shift:+.3f}（偏置路径{(biased.mean()):.3f} vs 均匀 {(uniform.mean()):.3f}）")

    passed = int(ok_uniform) + int(ok_biased_detected)
    bugs = 2 - passed
    summary("D6", passed, bugs,
            "偏置=3抽1取最强，且弃 6 张不回堆；穷举表口径需按契约 D-R1 改为默认均匀发牌")


if __name__ == "__main__":
    main()
