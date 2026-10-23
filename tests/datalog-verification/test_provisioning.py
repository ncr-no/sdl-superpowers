import os
import sys
import types

sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../skills/datalog-verification/scripts")
))

import provisioning  # noqa: E402


def test_missing_parser_is_unknown_with_an_install_command(monkeypatch):
    def missing(name):
        raise ImportError("No module named 'sdl_parser'")
    monkeypatch.setattr(provisioning.importlib, "import_module", missing)
    status, detail = provisioning.check_sdl_parser()
    assert status == "UNKNOWN"
    assert "apt install libsdl-parser" in detail


def test_shared_library_load_failure_is_unknown_not_a_crash(monkeypatch):
    def missing(name):
        raise OSError("libsdl_parser.so: cannot open shared object file")
    monkeypatch.setattr(provisioning.importlib, "import_module", missing)
    status, detail = provisioning.check_sdl_parser()
    assert status == "UNKNOWN"
    assert "libsdl_parser.so" in detail


def test_importable_parser_passes(monkeypatch):
    module = types.SimpleNamespace(__version__="0.3.0")
    monkeypatch.setattr(provisioning.importlib, "import_module", lambda name: module)
    status, detail = provisioning.check_sdl_parser()
    assert status == "PASS"
    assert "0.3.0" in detail


def test_missing_deputy_is_unknown(monkeypatch):
    monkeypatch.setattr(provisioning.shutil, "which", lambda name: None)
    status, detail = provisioning.check_deputy()
    assert status == "UNKNOWN"
    assert "deputy" in detail


def test_present_deputy_passes(monkeypatch):
    monkeypatch.setattr(provisioning.shutil, "which",
                        lambda name: "/usr/local/bin/deputy")
    assert provisioning.check_deputy()[0] == "PASS"


def test_report_names_both_tools(monkeypatch):
    monkeypatch.setattr(provisioning.shutil, "which", lambda name: None)
    monkeypatch.setattr(provisioning.importlib, "import_module",
                        lambda name: (_ for _ in ()).throw(ImportError("absent")))
    names = [row[0] for row in provisioning.report()]
    assert names == ["sdl_parser", "deputy"]
