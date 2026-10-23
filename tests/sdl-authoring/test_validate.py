import os
import sys

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/sdl-authoring/scripts")
))

from validate import validate  # noqa: E402


class FakeParser:
    class SDLLibraryParsingError(Exception):
        def __init__(self, message):
            super().__init__(message)
            self.message = message

    def __init__(self, result=None, error=None):
        self.result = result or {"name": "hospital-ransomware"}
        self.error = error

    def parse_sdl(self, text):
        if self.error:
            raise self.SDLLibraryParsingError(self.error)
        return self.result


def write(tmp_path, text):
    path = tmp_path / "scenario.sdl"
    path.write_text(text)
    return str(path)


def test_valid_file_reports_its_name(tmp_path):
    code, message = validate(write(tmp_path, "name: hospital-ransomware\n"), FakeParser())
    assert code == 0
    assert "hospital-ransomware" in message


def test_parse_failure_reports_the_parser_message_verbatim(tmp_path):
    code, message = validate(
        write(tmp_path, "name: x\n"),
        FakeParser(error="error parsing field `nodes`: invalid type: found sequence"),
    )
    assert code == 1
    assert "error parsing field `nodes`: invalid type: found sequence" in message


def test_parse_failure_message_carries_the_file_path(tmp_path):
    path = write(tmp_path, "name: x\n")
    _, message = validate(path, FakeParser(error="missing field `name`"))
    assert path in message


def test_missing_parser_is_unknown_with_install_steps(tmp_path, monkeypatch):
    import validate as module

    def missing(name):
        raise ImportError("No module named 'sdl_parser'")

    monkeypatch.setattr(module.importlib, "import_module", missing)
    code, message = validate(write(tmp_path, "name: x\n"))
    assert code == 2
    assert "UNKNOWN" in message
    assert "apt install libsdl-parser" in message
