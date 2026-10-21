"""D2 回归：rest_option 必须单调不减；资源路径必须是包根相对路径。

P0 基线（修复前）：
- draw.py::update_inform 用 min() → 押注 100（索引3）后 rest_option 仍为 0
- const.py 硬编码 '../game_exercise/src/...' 与指向仓库外的 '../myclient/...'
"""

from common import check, h, summary

from core.rules import Action, GameRoom, IllegalAction


def main():
    h("D2 rest_option 单调不减（回归检查）")

    passed = failed = 0

    room = GameRoom.new([
        [{"suit": "黑桃", "value": 14}, {"suit": "红心", "value": 14}, {"suit": "方块", "value": 14}],
        [{"suit": "黑桃", "value": 2}, {"suit": "红心", "value": 3}, {"suit": "方块", "value": 5}],
    ])
    room.apply(Action.BET_100)
    ok = room.rest_option == 3
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    check("押注 100 后 rest_option 应为 3", ok, f"实际 {room.rest_option}")

    room.whose_turn = 0
    try:
        room.apply(Action.BET_10)
        raised = False
    except IllegalAction:
        raised = True
    passed, failed = (passed + 1, failed) if raised else (passed, failed + 1)
    check("降档押注必须抛 IllegalAction", raised)

    h("D2b 资源路径（坏路径已消除）")
    import const

    paths = [const.Background, const.Card_Back, const.FONT_MAIN, const.card_directory, const.bgm_directory]
    bad = [str(p) for p in paths if "myclient" in str(p) or str(p).startswith("..")]
    passed, failed = (passed + 1, failed) if not bad else (passed, failed + 1)
    check("const.py 路径均为包根相对路径", not bad, f"违规: {bad}")

    absolute = all(str(p).startswith(str(const.ROOT)) for p in paths)
    passed, failed = (passed + 1, failed) if absolute else (passed, failed + 1)
    check("const.py 路径均解析到仓库内", absolute)

    h("D2c const.py 不再依赖 pygame")
    import ast

    tree = ast.parse(open(const.__file__, encoding="utf-8").read())
    imports = {n.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module}
    ok = "pygame" not in imports
    passed, failed = (passed + 1, failed) if ok else (passed, failed + 1)
    check("import const 不再引入 pygame", ok, f"实际导入: {sorted(imports)}")

    summary("D2", passed, failed, "rest_option 单调 + 路径修正 + const 与 pygame 解耦")


if __name__ == "__main__":
    main()
