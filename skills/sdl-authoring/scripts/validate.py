#!/usr/bin/env python3
"""Validate an SDL file, or say why it cannot be validated.

The parser reports one exception, SDLLibraryParsingError, whose `.message`
is the only field — there is no line number. Quote it verbatim and let the
author find the construct; never invent a position.
"""
from __future__ import annotations

import argparse
import importlib
import sys


def _parser():
    return importlib.import_module("sdl_parser")


def validate(path, parser=None):
    if parser is None:
        try:
            parser = _parser()
        except Exception as error:  # ImportError, or OSError from ctypes on load
            return 2, (
                "UNKNOWN %s: sdl_parser is not importable (%s). Install: "
                "sudo apt install libsdl-parser, then pip install "
                "<sdl-parser repo>/python-package" % (path, error)
            )
    with open(path) as handle:
        text = handle.read()
    try:
        scenario = parser.parse_sdl(text)
    except parser.SDLLibraryParsingError as error:
        return 1, "FAIL %s: %s" % (path, error.message)
    name = (scenario or {}).get("name") or "<unnamed>"
    return 0, "PASS %s: %s" % (path, name)


def main(argv=None):
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("path")
    parsed = args.parse_args(argv)
    code, message = validate(parsed.path)
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())
