# pycangui-a2l-gen

An A2L generator for [pycangui](https://github.com/davhodg/pycangui): a plugin that creates an
A2L file from the ECU's ELF, updates it after a rebuild, and checks it.

The work is done by [a2ltool](https://github.com/DanielT/a2ltool), which the plugin carries,
built from the release this repository's submodule is pinned to. The plugin is the pane over
it: which ELF, which A2L, which variables, and what a2ltool said.

**Early work.** What there is now: choose the variables by regular expressions on their names
-- measurements and characteristics separately -- then *Create*, *Update* (full, or addresses
only) and *Check* (strict or not). A tree of the ELF's variables to choose from, with a
conversion, unit and limits for each, comes next.

## Installing

It needs pycangui with plugin API 3, which is in the release after 0.6.2; until then, pycangui
from master. There are no releases yet.

## Developing

```
git clone --recurse-submodules https://github.com/davhodg/pycangui-a2l-gen
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python build/build.py
.venv/Scripts/python -m pytest -n auto
```

`build/build.py` builds a2ltool with cargo (Rust 1.85 or later, for its 2024 edition) and puts
it, with its licence files, in `a2lgen/bin`. On macOS it builds for Apple silicon and Intel and
joins them into one program: `rustup target add aarch64-apple-darwin x86_64-apple-darwin`
first. a2ltool's own test files are in Git LFS and are not needed.

- `a2lgen/`: the plugin, as pycangui loads it: `a2ltool.py` runs a2ltool, with its arguments in
  a response file so a long selection is not cut short by Windows' command line; `pane.py` is
  the pane.
- `external/a2ltool`: a2ltool, a submodule at a release tag, moved on purpose.
- `tests/`: a2ltool run as the plugin runs it, and the plugin in a pycangui window, on
  `tests/data/demo.elf` (built from `demo.c` by `gcc -g -O0`).

## Licence

Apache-2.0: see [LICENSE](LICENSE) and [NOTICE](NOTICE). a2ltool is MIT or Apache-2.0, by
Daniel Thaler; its licence files go into the plugin beside it.
