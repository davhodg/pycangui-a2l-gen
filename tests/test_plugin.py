# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 davhodg
"""The plugin in a pycangui window, running the a2ltool it carries.

Installed as somebody would install it, from the plugin folder. Needs a2ltool
built into it: python build/build.py.
"""

import re
import shutil
import time
from pathlib import Path

import pytest
from pycangui.core import plugin_package
from pycangui.ui.main_window import MainWindow
from PySide6.QtCore import QSettings

from a2lgen import a2ltool

ROOT = Path(__file__).resolve().parents[1]
ELF = Path(__file__).parent / "data" / "demo.elf"
PANE = "a2lgen:main"


def wait_for(app, condition, seconds: float = 30.0) -> bool:
    end = time.monotonic() + seconds
    while not condition() and time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()
    return condition()


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    if not a2ltool.program(ROOT / "a2lgen").is_file():
        pytest.fail("a2ltool is not built: python build/build.py")
    monkeypatch.setenv("PYCANGUI_HOME", str(tmp_path / "home"))
    QSettings().clear()
    win = MainWindow()
    win.show()
    app.processEvents()
    folder = tmp_path / "a2lgen"
    shutil.copytree(ROOT / "a2lgen", folder, ignore=shutil.ignore_patterns("__pycache__"))
    plugin_package.install_folder(folder, win.ctx.workspace_dir / "plugins")
    win._reload_plugins()
    app.processEvents()
    yield win
    win.close()


@pytest.fixture
def view(app, window):
    window.panes.show(PANE)
    return window.panes.view(PANE)


def finished(app, view, doing: str) -> int:
    assert wait_for(app, lambda: not view.run.running)
    assert view.last is not None and view.last[0] == doing
    return view.last[1]


def chosen(view, tmp_path, measurements="^meas_", characteristics="^cal_") -> Path:
    out = tmp_path / "demo.a2l"
    view.elf.setText(str(ELF))
    view.a2l.setText(str(out))
    view.measurements.setPlainText(measurements)
    view.characteristics.setPlainText(characteristics)
    return out


def measured(a2l: Path) -> set[str]:
    return set(re.findall(r"/begin MEASUREMENT\s+(\S+)", a2l.read_text(encoding="utf-8")))


def test_it_installs_with_a_pane(app, window):
    assert window.plugins.errors() == {}
    assert "A2L generator" in [r.label for r in window.plugins.working()]
    assert PANE in window.panes.docks


def test_create_then_check_from_the_pane(app, view, tmp_path):
    out = chosen(view, tmp_path)
    view.create()
    assert not view.create_button.isEnabled() and view.stop_button.isEnabled()
    assert finished(app, view, "create") == 0
    assert "meas_battery_mv" in measured(out)
    assert view.create_button.isEnabled() and not view.stop_button.isEnabled()

    view.check()
    assert finished(app, view, "check") == 0


def test_create_asks_before_replacing_an_a2l(app, view, tmp_path, monkeypatch):
    out = chosen(view, tmp_path)
    out.write_text("mine", encoding="utf-8")
    monkeypatch.setattr(view, "may_overwrite", lambda _path: False)
    view.create()
    assert not view.run.running and out.read_text(encoding="utf-8") == "mine"
    monkeypatch.setattr(view, "may_overwrite", lambda _path: True)
    view.create()
    assert finished(app, view, "create") == 0 and "meas_battery_mv" in measured(out)


def test_nothing_runs_without_an_elf_or_a_choice_of_variables(app, view, tmp_path):
    chosen(view, tmp_path, measurements="", characteristics="")
    view.create()
    assert not view.run.running and view.last is None
    view.elf.setText(str(tmp_path / "missing.elf"))
    view.measurements.setPlainText("^meas_")
    view.create()
    assert not view.run.running and view.last is None


def test_update_after_create(app, view, tmp_path):
    out = chosen(view, tmp_path)
    view.create()
    assert finished(app, view, "create") == 0
    before = measured(out)
    view.update_a2l()
    assert finished(app, view, "update") == 0
    assert measured(out) == before


def test_a_failed_check_is_told_with_its_exit_code(app, view, tmp_path):
    broken = tmp_path / "broken.a2l"
    broken.write_text('ASAP2_VERSION 1 71\n/begin PROJECT p ""\n', encoding="utf-8")
    view.a2l.setText(str(broken))
    view.check()
    assert finished(app, view, "check") != 0
    assert view.output.toPlainText(), "what a2ltool said is shown"


def test_the_fields_are_kept_in_the_workspace(app, window, view, tmp_path):
    chosen(view, tmp_path)
    view._keep()
    window.plugins.unload("a2lgen")
    window._reload_plugins()
    app.processEvents()
    window.panes.show(PANE)
    again = window.panes.view(PANE)
    assert again.elf.text() == str(ELF) and again.measurements.toPlainText() == "^meas_"
