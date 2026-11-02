"""分层纯度测试：core/ 必须是纯逻辑，不依赖 pygame。"""

import re
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parent.parent / "core"

PYGAME_IMPORT = re.compile(r"^\s*(?:import\s+pygame|from\s+pygame[\s.])", re.MULTILINE)


def _core_sources():
    return sorted(p for p in CORE_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def test_core_has_sources():
    assert _core_sources(), "core/ 下未找到源文件"


def test_core_does_not_import_pygame():
    offenders = []
    for path in _core_sources():
        text = path.read_text(encoding="utf-8")
        if PYGAME_IMPORT.search(text):
            offenders.append(path.name)
    assert not offenders, f"core/ 中不应 import pygame，违规文件: {offenders}"


def test_core_imports_without_pygame_installed(monkeypatch):
    """把 pygame 从 sys.modules 中摘掉后，core 仍必须可导入。"""
    import importlib
    import sys

    saved = {name: mod for name, mod in sys.modules.items() if name == "pygame" or name.startswith("pygame.")}
    for name in saved:
        del sys.modules[name]

    class _Blocker:
        def find_module(self, name, path=None):  # noqa: D401 - 兼容旧式 finder 协议
            if name == "pygame" or name.startswith("pygame."):
                raise ImportError("pygame 在本测试中被禁用")
            return None

    blocker = _Blocker()
    sys.meta_path.insert(0, blocker)
    try:
        for name in ("core", "core.cards", "core.evaluator", "core.strength",
                     "core.dealing", "core.rules"):
            module = importlib.import_module(name)
            assert module is not None
    finally:
        sys.meta_path.remove(blocker)
        sys.modules.update(saved)


def test_core_declares_no_heavy_dependencies():
    """core 只应依赖标准库（plus 不依赖 numpy/scipy/torch）。"""
    heavy = []
    for path in _core_sources():
        text = path.read_text(encoding="utf-8")
        for name in ("numpy", "scipy", "torch", "matplotlib", "pygame"):
            if re.search(rf"^\s*(?:import\s+{name}|from\s+{name}[\s.])", text, re.MULTILINE):
                heavy.append(f"{path.name}:{name}")
    assert not heavy, f"core/ 不应依赖 {heavy}"


def test_import_core_does_not_build_strength_table():
    """全新解释器里 `import core` 后，22100 手强度表的 lru_cache 仍应为空（惰性建表不被触发）。

    在子进程中跑以保证「全新解释器」：同进程内其它测试可能已触发建表。
    """
    import subprocess
    import sys

    repo_root = CORE_DIR.parent
    code = (
        "import core; "
        "from core import strength; "
        "i = strength._ranked_keys.cache_info(); "
        "assert i.hits == 0 and i.currsize == 0, f'import core 触发了建表: {i}'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=repo_root
    )
    assert result.returncode == 0, f"新解释器 import core 断言失败: {result.stdout} {result.stderr}"
