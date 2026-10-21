"""D2 复现：rest_option（最低可押档）语义分叉。

规则文本（algorithm.py::show_help_font）：
    「每轮玩家可以押注大小的最小选项是当前所有玩家押注选项的最大值」
    → rest_option 必须单调不减。

已知：
- Game_room.get_choice 用 `self.rest_option = action`（在动作合法的前提下
  等价于运行最大值）→ 语义正确。
- draw.py::Draw_Pic.update_inform 用 `min(self.rest_option, self.option)` → 门槛只会降。
- draw_me_vs_DQN.py::Draw_Pic.update_inform 用 `max(...)` → 正确，说明是复制分叉漂移。

预期基线：draw.py 版本在押注 100（索引3）后 rest_option 仍为 0，判定 BUG。
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from common import h, check, summary


def exercise(name, cls, five_args):
    pic = cls()
    pic.load_cards([[{"suit": "黑桃", "value": 2}], [{"suit": "红心", "value": 3}]])
    pic.rest_option = 0

    # 押注序列：先押 100（选项索引 3），再押 10（索引 0，规则上非法但 UI 若门槛不升就能点）
    steps = []
    for option in (3, 0):
        if five_args:
            pic.update_inform(0, option, 10, [5, 5], [20000, 20000])
        else:
            pic.update_inform(0, option, 10, [5, 5])
        steps.append((option, pic.rest_option))

    print(f"\n{name}")
    print(f"  押注序列 -> rest_option 轨迹: {steps}")
    check(
        f"{name}: 押注 100(索引3) 后 rest_option 应 >= 3",
        steps[0][1] >= 3,
        f"实际 rest_option = {steps[0][1]}（{'门槛未提升，允许继续小额下注' if steps[0][1] < 3 else '正常'}）",
    )
    return steps[0][1] >= 3


def main():
    h("D2 rest_option 最低押注档语义（规则要求单调不减）")

    import draw as draw_mod

    passed = bugs = 0
    if exercise("draw.py (min)", draw_mod.Draw_Pic, False):
        passed += 1
    else:
        bugs += 1

    # draw_me_vs_DQN.py 的 Draw_Pic 里 update_inform 用的是 max()（正确）。
    # 但该模块在 import 期就 load_state_dict('dqn_model_0.pth')，而该权重是 4 维、
    # 代码声明 DQN(9,6) → import 直接崩（D7-d / D8 证据）。此处改为静态核对源码，
    # 避免基线脚本被 import 副作用带崩。
    import re
    src = open(os.path.join(os.path.dirname(__file__), "..", "..",
                            "draw_me_vs_DQN.py"), encoding="utf-8").read()
    uses_max = bool(re.search(r"self\.rest_option\s*=\s*max\(", src))
    print("\ndraw_me_vs_DQN.py (静态核对，因 import 期 load_state_dict 会崩)")
    print(f"  update_inform 使用 max(...): {uses_max}")
    check("draw_me_vs_DQN.py: rest_option 使用单调不减语义", uses_max)
    if uses_max:
        passed += 1
    else:
        bugs += 1

    summary("D2", passed, bugs, "draw.py 的 min() 是 bug；draw_me_vs_DQN.py 的 max() 正确")


if __name__ == "__main__":
    main()
