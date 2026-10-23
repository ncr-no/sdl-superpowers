#!/usr/bin/env python3
"""Report which verification tools are present.

`sdl_parser` is a ctypes wrapper around a Rust shared library, so importing
it raises when the library is missing — detection has to catch the import,
not look for a filename. A missing tool is UNKNOWN with an install command;
it is never a traceback (spec §2.4).
"""
from __future__ import annotations

import importlib
import shutil

PASS, UNKNOWN = "PASS", "UNKNOWN"

SDL_INSTALL = (
    "sudo apt install libsdl-parser, then pip install <sdl-parser repo>/python-package"
)


def check_sdl_parser():
    try:
        module = importlib.import_module("sdl_parser")
    except Exception as error:  # ImportError, or OSError from ctypes on load
        return UNKNOWN, "sdl_parser is not importable (%s). Install: %s" % (error, SDL_INSTALL)
    return PASS, "sdl_parser %s" % getattr(module, "__version__", "loaded")


def check_deputy():
    path = shutil.which("deputy")
    if path is None:
        return UNKNOWN, "deputy is not on PATH. Install it from the Deputy release page"
    return PASS, path


def report():
    return [
        ("sdl_parser",) + check_sdl_parser(),
        ("deputy",) + check_deputy(),
    ]


def main():
    for name, status, detail in report():
        print("%-10s %-8s %s" % (name, status, detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
