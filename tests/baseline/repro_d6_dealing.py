"""D6 回归：默认发牌必须均匀，偏置路径必须默认关闭且显著更强。

P0 基线（修复前）：``draw_cards_plus`` 三抽一取最优并弃置其余 6 张 →
手牌强度分位均值 0.766（均匀为 0.489），最强档占比 0.147（均匀 0.013，11 倍）。
"""

import random

from common import check, h, summary

from core.dealing import deal_strength_biased, deal_uniform, new_deck, verify_uniformity

SAMPLE = 300


def sample(kind, n=SAMPLE):
    rng = random.Random(20261021)
    deck = new_deck(rng)
    hands = []
    for _ in range(n):
        need = 3 if kind == "uniform" else 9
        if len(deck) < need:
            deck = new_deck(rng)
        hands.append(deal_uniform(deck) if kind == "uniform" else deal_strength_biased(deck))
    return hands


def main():
    h("D6 发牌分布（回归检查）")

    uniform_mean = verify_uniformity(sample("uniform"))
    biased_mean = verify_uniformity(sample("biased"))

    print(f"  均匀 deal_uniform    分位均值 = {uniform_mean:.3f}")
    print(f"  偏置 deal_strength_biased 分位均值 = {biased_mean:.3f}")

    passed = failed = 0
    ok = 0.44 < uniform_mean < 0.56
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    check("默认发牌均匀（分位均值≈0.5）", ok, f"实际 {uniform_mean:.3f}")

    ok = biased_mean - uniform_mean > 0.15
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    check("偏置路径显著更强（仅作可选开关）", ok, f"差值 {biased_mean - uniform_mean:+.3f}")

    import inspect

    import scripts.env as env_mod

    src = inspect.getsource(env_mod)
    ok = "deal_strength_biased" not in src
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    check("训练/对局环境只使用均匀发牌", ok)

    summary("D6", passed, failed, "默认均匀；偏置逻辑保留但不被任何默认路径调用")


if __name__ == "__main__":
    main()
