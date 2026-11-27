# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 davhodg
"""The A2L generator pane: an ELF in, an A2L out, and a2ltool's word on it.

Three things, each one run of a2ltool: create an A2L from the ELF with the
variables whose names match, update an A2L after the ELF was rebuilt, and check
an A2L. What a2ltool printed is shown beneath, as it printed it.

The choice of variables is by regular expression for now -- what a2ltool takes
on its command line. A tree of the ELF's variables to choose from comes later.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .a2ltool import UPDATE_TYPES, Run, Selection, check_args, create_args, update_args

ELF_FILTER = "ELF files (*.elf *.out *.axf *.abs *.exe);;All files (*)"
A2L_FILTER = "A2L files (*.a2l);;All files (*)"
#: What each field is kept under in the plugin's settings.
KEPT = ("elf", "a2l", "measurements", "characteristics")


def regexes(text: str) -> tuple[str, ...]:
    """The regular expressions typed in a box, one per line, blank lines left out."""
    return tuple(line.strip() for line in text.splitlines() if line.strip())


class A2lGenView(QWidget):
    def __init__(self, app, folder: Path) -> None:
        super().__init__()
        self.app = app
        self.run = Run(folder, self)
        self.run.finished.connect(self._done)
        #: What the last run was, and what it ended with; None before the first.
        self.last: tuple[str, int] | None = None
        self._doing = ""

        self.elf = QLineEdit()
        self.elf.setToolTip("The program built for the ECU, with its debug information (DWARF).")
        self.a2l = QLineEdit()
        self.a2l.setToolTip("The A2L file: written by Create, updated by Update, read by Check.")
        self.measurements = QPlainTextEdit()
        self.measurements.setToolTip(
            "Variables to add as measurements, read while the ECU runs: a regular expression\n"
            "on their names, one per line. ^sensor_ takes every name starting sensor_."
        )
        self.characteristics = QPlainTextEdit()
        self.characteristics.setToolTip(
            "Variables to add as characteristics, calibrated in the ECU: as for measurements."
        )
        for box in (self.measurements, self.characteristics):
            box.setFont(app.mono_font())
            box.setMaximumHeight(80)
        self.update_kind = QComboBox()
        for kind in UPDATE_TYPES:
            self.update_kind.addItem(kind.capitalize(), kind)
        self.update_kind.setToolTip(
            "Full: addresses, types and limits from the rebuilt ELF. Addresses: only those."
        )
        self.strict = QCheckBox("Strict")
        self.strict.setChecked(True)
        self.strict.setToolTip(
            "Anything inconsistent at all is an error, not only what breaks the file."
        )

        browse_elf = QPushButton("Browse...")
        browse_elf.clicked.connect(self._choose_elf)
        browse_a2l = QPushButton("Browse...")
        browse_a2l.clicked.connect(self._choose_a2l)
        self.create_button = app.with_icon(QPushButton("Create"), "write")
        self.create_button.setToolTip("Write a new A2L from the ELF, with the variables chosen.")
        self.create_button.clicked.connect(self.create)
        self.update_button = app.with_icon(QPushButton("Update"), "switch")
        self.update_button.setToolTip("Bring the A2L up to date with the ELF after a rebuild.")
        self.update_button.clicked.connect(self.update_a2l)
        self.check_button = app.with_icon(QPushButton("Check"), "read")
        self.check_button.setToolTip("Check the A2L.")
        self.check_button.clicked.connect(self.check)
        self.stop_button = app.with_icon(QPushButton("Stop"), "stop")
        self.stop_button.clicked.connect(self.run.stop)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(app.mono_font())
        self.output.setLineWrapMode(QPlainTextEdit.NoWrap)

        files = QGridLayout()
        files.addWidget(QLabel("ELF"), 0, 0)
        files.addWidget(self.elf, 0, 1)
        files.addWidget(browse_elf, 0, 2)
        files.addWidget(QLabel("A2L"), 1, 0)
        files.addWidget(self.a2l, 1, 1)
        files.addWidget(browse_a2l, 1, 2)
        files.addWidget(QLabel("Measurements"), 2, 0, Qt.AlignTop)
        files.addWidget(self.measurements, 2, 1, 1, 2)
        files.addWidget(QLabel("Characteristics"), 3, 0, Qt.AlignTop)
        files.addWidget(self.characteristics, 3, 1, 1, 2)

        buttons = QHBoxLayout()
        buttons.addWidget(self.create_button)
        buttons.addWidget(self.update_button)
        buttons.addWidget(self.update_kind)
        buttons.addWidget(self.check_button)
        buttons.addWidget(self.strict)
        buttons.addStretch(1)
        buttons.addWidget(self.stop_button)

        layout = QVBoxLayout(self)
        layout.addLayout(files)
        layout.addLayout(buttons)
        layout.addWidget(self.status)
        layout.addWidget(self.output, 1)

        self._restore()
        for box in (self.elf, self.a2l):
            box.editingFinished.connect(self._keep)
        for box in (self.measurements, self.characteristics):
            box.textChanged.connect(self._keep)
        self._enable()

    # --- what it was left with -----------------------------------------------------------
    def _restore(self) -> None:
        settings = self.app.settings
        self.elf.setText(settings.get("elf", ""))
        self.a2l.setText(settings.get("a2l", ""))
        self.measurements.setPlainText(settings.get("measurements", ""))
        self.characteristics.setPlainText(settings.get("characteristics", ""))

    def _keep(self) -> None:
        settings = self.app.settings
        settings.set("elf", self.elf.text().strip())
        settings.set("a2l", self.a2l.text().strip())
        settings.set("measurements", self.measurements.toPlainText())
        settings.set("characteristics", self.characteristics.toPlainText())

    def _choose_elf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "ELF file", self.elf.text(), ELF_FILTER)
        if path:
            self.elf.setText(path)
            self._keep()

    def _choose_a2l(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "A2L file", self.a2l.text(), A2L_FILTER, options=QFileDialog.DontConfirmOverwrite
        )
        if path:
            self.a2l.setText(path)
            self._keep()

    # --- running a2ltool -----------------------------------------------------------------
    def _paths(self, need_elf: bool) -> tuple[Path, Path] | None:
        elf, a2l = Path(self.elf.text().strip()), Path(self.a2l.text().strip())
        if need_elf and not elf.is_file():
            self.status.setText("Choose the ELF file.")
            return None
        if not self.a2l.text().strip():
            self.status.setText("Choose the A2L file.")
            return None
        return elf, a2l

    def may_overwrite(self, path: Path) -> bool:
        """Asked before Create writes over an A2L that is already there."""
        answer = QMessageBox.question(
            self, "Replace the A2L?", f"{path.name} is already there. Replace it with a new one?"
        )
        return answer == QMessageBox.Yes

    def create(self) -> None:
        if (paths := self._paths(need_elf=True)) is None:
            return
        elf, a2l = paths
        selection = Selection(
            regexes(self.measurements.toPlainText()), regexes(self.characteristics.toPlainText())
        )
        if not selection.args():
            self.status.setText("Give at least one regular expression for the variables to add.")
            return
        if a2l.exists() and not self.may_overwrite(a2l):
            return
        self._start("create", create_args(elf, a2l, selection))

    def update_a2l(self) -> None:
        if (paths := self._paths(need_elf=True)) is None:
            return
        elf, a2l = paths
        if not a2l.is_file():
            self.status.setText("There is no A2L there to update: Create one first.")
            return
        self._start("update", update_args(a2l, elf, a2l, self.update_kind.currentData()))

    def check(self) -> None:
        if (paths := self._paths(need_elf=False)) is None:
            return
        _elf, a2l = paths
        if not a2l.is_file():
            self.status.setText("There is no A2L there to check.")
            return
        self._start("check", check_args(a2l, self.strict.isChecked()))

    def _start(self, doing: str, args: list[str]) -> None:
        self._doing = doing
        self.output.clear()
        self.status.setText(f"Running a2ltool: {doing}...")
        self.run.start(args)
        self._enable()

    def _done(self, code: int, output: str) -> None:
        self.last = (self._doing, code)
        self.output.setPlainText(output)
        if code == 0:
            self.status.setText(f"a2ltool: {self._doing} done.")
            self.app.log(f"a2ltool {self._doing}: done")
        else:
            self.status.setText(f"a2ltool: {self._doing} failed (exit code {code}): see below.")
            self.app.warn(f"a2ltool {self._doing} failed, exit code {code}")
        self._enable()

    def _enable(self) -> None:
        idle = not self.run.running
        for button in (self.create_button, self.update_button, self.check_button):
            button.setEnabled(idle)
        self.stop_button.setEnabled(not idle)

    def shutdown(self) -> None:
        """A run left going when the pane goes is stopped: nobody would see what came of it."""
        self.run.stop()
