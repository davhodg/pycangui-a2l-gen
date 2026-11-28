# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 davhodg
"""A2L generator for pycangui: an A2L from the ECU's ELF, updated after a rebuild, and checked.

The work is a2ltool's (https://github.com/DanielT/a2ltool, MIT or Apache-2.0),
which the plugin carries in its bin folder, built from the release this
repository's submodule is pinned to. The plugin is the pane over it: which
files, which variables, and what a2ltool said.
"""

from __future__ import annotations

from pathlib import Path

from .pane import A2lGenView

API_VERSION = 3
NAME = "A2L generator"
VERSION = "0.1"
DESCRIPTION = (
    "Creates an A2L file from an ECU's ELF, updates it after a rebuild, and checks it, "
    "with a2ltool."
)


def register(app) -> None:
    folder = Path(__file__).resolve().parent
    app.add_pane(
        "main",
        "A2L generator",
        lambda _name: A2lGenView(app, folder),
        area="right",
        shutdown=lambda view: view.shutdown(),
    )
