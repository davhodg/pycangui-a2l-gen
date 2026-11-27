# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 davhodg
"""Build a2ltool from its submodule and put it in the plugin's bin folder.

    python build/build.py

a2ltool is built from external/a2ltool, at the release the submodule is pinned
to, with the versions of its crates its Cargo.lock names (``--locked``). On
macOS it is built for Apple silicon and for Intel and the two joined into one
program with lipo, so one plugin runs on either; the two targets must be
installed (``rustup target add aarch64-apple-darwin x86_64-apple-darwin``).

Cargo's output goes to build/target rather than into the submodule, which stays
as it was checked out. a2ltool's two licence files go into bin beside it: the
plugin carries a2ltool, so it carries its licence.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "external" / "a2ltool"
TARGET = ROOT / "build" / "target"
BIN = ROOT / "a2lgen" / "bin"
EXE = ".exe" if sys.platform == "win32" else ""
#: Both kinds of Mac, joined into one program.
MAC_TARGETS = ("aarch64-apple-darwin", "x86_64-apple-darwin")
LICENCES = ("LICENSE-MIT", "LICENSE-APACHE")


def cargo(*args: str) -> None:
    command = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--manifest-path",
        str(SOURCE / "Cargo.toml"),
    ]
    subprocess.run(
        [*command, *args], check=True, env={**os.environ, "CARGO_TARGET_DIR": str(TARGET)}
    )


def build() -> Path:
    """Build it, and answer where the program is."""
    if sys.platform != "darwin":
        cargo()
        return TARGET / "release" / f"a2ltool{EXE}"
    built = []
    for target in MAC_TARGETS:
        cargo("--target", target)
        built.append(TARGET / target / "release" / "a2ltool")
    joined = TARGET / "a2ltool-universal"
    subprocess.run(["lipo", "-create", "-output", str(joined), *map(str, built)], check=True)
    return joined


def main() -> int:
    if not (SOURCE / "Cargo.toml").is_file():
        sys.exit("external/a2ltool is empty: git submodule update --init")
    program = build()
    BIN.mkdir(parents=True, exist_ok=True)
    placed = BIN / f"a2ltool{EXE}"
    shutil.copy2(program, placed)
    placed.chmod(placed.stat().st_mode | 0o755)
    for name in LICENCES:
        shutil.copy2(SOURCE / name, BIN / f"a2ltool-{name}")
    print(placed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
