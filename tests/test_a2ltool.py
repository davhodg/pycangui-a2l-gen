# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 davhodg
"""a2ltool's arguments, and a2ltool itself run on the test ELF.

Needs a2ltool built into the plugin: python build/build.py.
"""

import re
import subprocess
from pathlib import Path

import pytest

from a2lgen import a2ltool
from a2lgen.a2ltool import Selection, check_args, create_args, update_args

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "a2lgen"
ELF = Path(__file__).parent / "data" / "demo.elf"


def built() -> Path:
    found = a2ltool.program(FOLDER)
    if not found.is_file():
        pytest.fail(f"{found.name} is not built: python build/build.py")
    return found


def run(args: list[str], tmp_path: Path) -> subprocess.CompletedProcess:
    """a2ltool as the plugin runs it: its arguments in a response file."""
    response = a2ltool.write_response(args, tmp_path / "args.txt")
    return subprocess.run(
        [str(built()), f"@{response}"], capture_output=True, text=True, check=False, timeout=60
    )


def names(a2l: Path, block: str) -> set[str]:
    """The names of an A2L's MEASUREMENTs or CHARACTERISTICs."""
    return set(re.findall(rf"/begin {block}\s+(\S+)", a2l.read_text(encoding="utf-8")))


def test_a_selection_is_one_option_per_regular_expression():
    chosen = Selection(measurements=("^meas_", "^x$"), characteristics=("^cal_",))
    assert chosen.args() == [
        "--measurement-regex", "^meas_", "--measurement-regex", "^x$",
        "--characteristic-regex", "^cal_",
    ]  # fmt: skip


def test_update_takes_only_what_a2ltool_takes():
    assert update_args(Path("a.a2l"), Path("b.elf"), Path("a.a2l"), "ADDRESSES")[4] == "ADDRESSES"
    with pytest.raises(ValueError):
        update_args(Path("a.a2l"), Path("b.elf"), Path("a.a2l"), "SOME")


def test_create_puts_in_the_variables_chosen_and_no_others(tmp_path):
    out = tmp_path / "demo.a2l"
    chosen = Selection(("^meas_battery", "^meas_position$"), ("^cal_",))
    done = run(create_args(ELF, out, chosen), tmp_path)
    assert done.returncode == 0, done.stdout
    assert names(out, "MEASUREMENT") == {"meas_battery_mv", "meas_position"}
    assert {"cal_speed_limit", "cal_gain"} <= names(out, "CHARACTERISTIC")


def test_paths_and_expressions_reach_a2ltool_as_written(tmp_path):
    """Spaces, backslashes and quotes through the response file: a Windows path,
    and a regular expression with an escape, a double quote and a backslash at
    its end -- the cases the rules for a quoted argument treat differently."""
    where = tmp_path / "with space 'and quotes'"
    where.mkdir()
    out = where / "out.a2l"
    done = run(create_args(ELF, out, Selection((r'^meas_\w+_mv$|"x\\',))), tmp_path)
    assert done.returncode == 0, done.stdout
    assert names(out, "MEASUREMENT") == {"meas_battery_mv"}


def test_what_create_wrote_passes_a_strict_check(tmp_path):
    out = tmp_path / "demo.a2l"
    assert run(create_args(ELF, out, Selection(("^meas_",), ("^cal_",))), tmp_path).returncode == 0
    assert run(check_args(out), tmp_path).returncode == 0


def test_a_broken_a2l_fails_the_check(tmp_path):
    broken = tmp_path / "broken.a2l"
    broken.write_text('ASAP2_VERSION 1 71\n/begin PROJECT p ""\n', encoding="utf-8")
    assert run(check_args(broken), tmp_path).returncode != 0


def test_update_keeps_the_variables_and_writes_the_file(tmp_path):
    out = tmp_path / "demo.a2l"
    assert run(create_args(ELF, out, Selection(("^meas_",))), tmp_path).returncode == 0
    before = names(out, "MEASUREMENT")
    updated = tmp_path / "updated.a2l"
    assert run(update_args(out, ELF, updated), tmp_path).returncode == 0
    assert names(updated, "MEASUREMENT") == before
