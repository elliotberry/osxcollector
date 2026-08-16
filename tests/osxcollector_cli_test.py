"""CLI output-directory tests."""

import os
from types import SimpleNamespace
from unittest.mock import patch

from osxcollector.cli import DEFAULT_OUTDIR_NAME, default_outdir, main, resolve_outdir


class TestDefaultOutdir:
    def test_uses_home(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SUDO_USER", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        assert default_outdir() == str(tmp_path / DEFAULT_OUTDIR_NAME)

    def test_prefers_sudo_user_home(self, monkeypatch, tmp_path):
        sudo_home = tmp_path / "sudo-user"
        sudo_home.mkdir()
        monkeypatch.setenv("SUDO_USER", "collector")
        monkeypatch.setenv("HOME", str(tmp_path / "root"))
        with patch("osxcollector.cli.pwd.getpwnam", return_value=SimpleNamespace(pw_dir=str(sudo_home))):
            assert default_outdir() == str(sudo_home / DEFAULT_OUTDIR_NAME)

    def test_falls_back_when_sudo_user_unknown(self, monkeypatch, tmp_path):
        monkeypatch.setenv("SUDO_USER", "missing-user")
        monkeypatch.setenv("HOME", str(tmp_path))
        with patch("osxcollector.cli.pwd.getpwnam", side_effect=KeyError("missing-user")):
            assert default_outdir() == str(tmp_path / DEFAULT_OUTDIR_NAME)


class TestResolveOutdir:
    def test_creates_default_directory(self, monkeypatch, tmp_path):
        monkeypatch.delenv("SUDO_USER", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))
        path = resolve_outdir(None)
        assert path == os.path.join(str(tmp_path), DEFAULT_OUTDIR_NAME)
        assert os.path.isdir(path)

    def test_creates_explicit_directory(self, tmp_path):
        target = tmp_path / "custom-out"
        path = resolve_outdir(str(target))
        assert path == str(target)
        assert os.path.isdir(path)


class TestMain:
    def test_list_sections_stdout(self, capsys):
        assert main(["--list-sections"]) == 0
        out, err = capsys.readouterr()
        assert "startup" in out.splitlines()
        assert "version" in out.splitlines()
        assert err == ""

    def test_root_check_does_not_write_jsonl_to_stdout(self, capsys, monkeypatch):
        monkeypatch.setattr("osxcollector.cli.os.geteuid", lambda: 501)
        monkeypatch.setattr("osxcollector.cli.os.getegid", lambda: 20)
        assert main([]) == 1
        out, err = capsys.readouterr()
        assert out == ""
        assert "Must run as root" in err
        assert "osxcollector_error" not in err
        assert "{" not in out
