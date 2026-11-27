# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 davhodg
"""Running a2ltool: the program the plugin carries, its arguments, and what it said.

a2ltool is a command line, one run for each thing done -- create an A2L from an
ELF, update one after a rebuild, check one. Its arguments go in a response file
(``a2ltool @args``), which it reads itself, so a selection of thousands of
variables is not cut short by the length Windows allows a command line.

It reports on its standard output, and an error ends it with exit code 1. What
it says is shown as it said it: the pane does not try to read meaning into it.
"""

from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, Signal

#: The program, relative to the plugin's folder (".exe" on Windows).
PROGRAM = Path("bin") / "a2ltool"
#: What --update takes: everything about each item, or only its address.
UPDATE_TYPES = ("FULL", "ADDRESSES")


def program(folder: Path) -> Path:
    """The a2ltool the plugin carries. The .exe on Windows, which also has the
    Linux one beside it in a plugin made for both."""
    path = folder / PROGRAM
    if sys.platform == "win32":
        path = path.with_suffix(".exe")
    return path


def quote(arg: str) -> str:
    """One argument for the response file, in double quotes.

    a2ltool reads the file by Windows' command-line rules on every system: a
    backslash is itself, except in front of a double quote, where 2n of them
    are n and an odd one makes the quote literal. So a Windows path or a regular
    expression is written as it is, and only the backslashes before a quote --
    including the closing one -- are doubled.
    """
    out = ['"']
    backslashes = 0
    for char in arg:
        if char == "\\":
            backslashes += 1
            continue
        if char == '"':
            out.append("\\" * (2 * backslashes + 1) + '"')
        else:
            out.append("\\" * backslashes + char)
        backslashes = 0
    out.append("\\" * (2 * backslashes) + '"')
    return "".join(out)


def write_response(args: list[str], path: Path) -> Path:
    path.write_text("".join(f"{quote(arg)}\n" for arg in args), encoding="utf-8")
    return path


@dataclass(frozen=True)
class Selection:
    """Which of the ELF's variables to put in the A2L, as a2ltool chooses them:
    by regular expression on their names. A measurement is read while the ECU
    runs; a characteristic is a value calibrated in it."""

    measurements: tuple[str, ...] = ()
    characteristics: tuple[str, ...] = ()

    def args(self) -> list[str]:
        out: list[str] = []
        for regex in self.measurements:
            out += ["--measurement-regex", regex]
        for regex in self.characteristics:
            out += ["--characteristic-regex", regex]
        return out


def create_args(elf: Path, output: Path, selection: Selection) -> list[str]:
    """A new A2L from the ELF, with the variables chosen."""
    return ["--create", "--elffile", str(elf), *selection.args(), "--output", str(output)]


def update_args(a2l: Path, elf: Path, output: Path, kind: str = "FULL") -> list[str]:
    """An A2L brought up to date with a rebuilt ELF: addresses, and with FULL the
    types and limits too."""
    if kind not in UPDATE_TYPES:
        raise ValueError(f"update is one of {', '.join(UPDATE_TYPES)}, not {kind!r}")
    return [str(a2l), "--elffile", str(elf), "--update", kind, "--output", str(output)]


def check_args(a2l: Path, strict: bool = True) -> list[str]:
    """The A2L checked: references that resolve, limits that fit, and with strict,
    anything inconsistent at all is an error."""
    return [str(a2l), "--check", *(["--strict"] if strict else [])]


class Run(QObject):
    """One run of a2ltool, in the background. ``finished(code, output)`` once it
    has ended, on the GUI thread; code is -1 if it could not start or was stopped."""

    finished = Signal(int, str)

    def __init__(self, folder: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.folder = Path(folder)
        self._process: QProcess | None = None
        self._scratch: tempfile.TemporaryDirectory | None = None
        self._output: list[str] = []

    @property
    def running(self) -> bool:
        return self._process is not None

    def start(self, args: list[str]) -> None:
        if self._process is not None:
            raise RuntimeError("a2ltool is already running")
        self._scratch = tempfile.TemporaryDirectory(prefix="a2lgen-")
        response = write_response(args, Path(self._scratch.name) / "args.txt")
        self._output = []
        process = self._process = QProcess(self)
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(self._read)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._failed)
        process.start(str(program(self.folder)), [f"@{response}"])

    def stop(self) -> None:
        if self._process is not None:
            self._process.kill()

    def _read(self) -> None:
        if self._process is not None:
            data = bytes(self._process.readAllStandardOutput())
            self._output.append(data.decode("utf-8", errors="replace"))

    def _finished(self, code: int, status) -> None:
        self._read()
        crashed = status == QProcess.CrashExit
        self._end(-1 if crashed else code)

    def _failed(self, error) -> None:
        if error == QProcess.FailedToStart:
            self._output.append(f"a2ltool could not be started: {self._process.errorString()}\n")
            self._end(-1)

    def _end(self, code: int) -> None:
        process, scratch = self._process, self._scratch
        self._process = self._scratch = None
        if process is not None:
            process.deleteLater()
        if scratch is not None:
            scratch.cleanup()
        self.finished.emit(code, "".join(self._output))
