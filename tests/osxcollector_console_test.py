"""Tests for operator-facing console output and logger bridging."""

from __future__ import annotations

import io
from unittest.mock import patch

from osxcollector.collectors.collector import Collector
from osxcollector.console import Console, color_enabled_for, format_context
from osxcollector.logging_jsonl import Logger


class FakeTTY(io.StringIO):
    def isatty(self) -> bool:
        return True


class TestFormatContext:
    def test_skips_incident_id(self):
        extras = {
            "osxcollector_incident_id": "osxcollect-1",
            "osxcollector_section": "startup",
            "osxcollector_subsection": "launch_agents",
        }
        assert format_context(extras) == ("osxcollector_section=startup osxcollector_subsection=launch_agents")

    def test_empty(self):
        assert format_context(None) == ""
        assert format_context({}) == ""


class TestColorEnabled:
    def test_off_when_not_a_tty(self):
        assert color_enabled_for(io.StringIO()) is False

    def test_off_when_no_color_set(self, monkeypatch):
        monkeypatch.setenv("NO_COLOR", "1")
        monkeypatch.setenv("TERM", "xterm")
        assert color_enabled_for(FakeTTY()) is False

    def test_off_when_term_dumb(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "dumb")
        assert color_enabled_for(FakeTTY()) is False

    def test_on_for_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm")
        assert color_enabled_for(FakeTTY()) is True


class TestConsole:
    def test_banner_and_summary(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.banner(
            version="2.0.0",
            incident_id="osxcollect-2026_08_16-16_28_00",
            root="/",
            output="/tmp/out",
            section_count=24,
            skipped=["codesign", "full_hash"],
        )
        Console.warnings = 18
        Console.errors = 1
        Console.summary(duration_s=42.3, records=35394, output="/tmp/out.tgz", digest="abc")
        text = buf.getvalue()
        assert "OSXCollector 2.0.0" in text
        assert "incident   osxcollect-2026_08_16-16_28_00" in text
        assert "root       /" in text
        assert "output     /tmp/out" in text
        assert "sections   24  (skipping codesign, full_hash)" in text
        assert "Done in 42.3s" in text
        assert "records   35394" in text
        assert "warnings  18" in text
        assert "errors    1" in text
        assert "archive   /tmp/out.tgz" in text
        assert "sha256    abc" in text

    def test_summary_without_archive_uses_output(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.summary(duration_s=1.0, records=10, output="/tmp/incident")
        text = buf.getvalue()
        assert "output    /tmp/incident" in text
        assert "archive" not in text
        assert "sha256" not in text

    def test_section_same_line_when_quiet(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.section_start(1, 24, "version")
        Console.section_end(1, 0.0)
        text = buf.getvalue()
        assert text.count("\n") == 1
        assert "[ 1/24] version" in text
        assert "1 record" in text
        assert "0.0s" in text

    def test_section_breaks_line_on_warning(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.section_start(3, 24, "startup")
        Console.warn("Directory not found /Library/StartupItems")
        Console.section_end(142, 0.8)
        text = buf.getvalue()
        lines = text.splitlines()
        assert any("[ 3/24] startup" in line for line in lines)
        assert any("warn  Directory not found /Library/StartupItems" in line for line in lines)
        assert any("142 records" in line for line in lines)
        assert Console.warnings == 1

    def test_warn_outside_section_uses_prefix(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.warn("unified log export failed: boom")
        assert "[WARN]  unified log export failed: boom" in buf.getvalue()

    def test_error_increments_and_shows_context(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.error("PermissionError: denied", "osxcollector_section=tcc")
        text = buf.getvalue()
        assert "[ERROR] PermissionError: denied" in text
        assert "osxcollector_section=tcc" in text
        assert Console.errors == 1

    def test_color_applied_on_tty(self, monkeypatch):
        monkeypatch.delenv("NO_COLOR", raising=False)
        monkeypatch.setenv("TERM", "xterm")
        buf = FakeTTY()
        Console.configure(stream=buf)
        Console.error("boom")
        assert "\033[31m" in buf.getvalue()
        assert "\033[0m" in buf.getvalue()

    def test_phase(self):
        buf = io.StringIO()
        Console.configure(stream=buf)
        Console.phase("Archiving system logs")
        Console.phase("Collecting evidence metadata", tag="pre")
        text = buf.getvalue()
        assert "[post]  Archiving system logs" in text
        assert "[pre]  Collecting evidence metadata" in text


class TestLoggerBridge:
    def test_warning_always_reaches_console(self):
        jsonl = io.StringIO()
        err = io.StringIO()
        Logger.set_output_file(jsonl)
        Console.configure(stream=err, debug=False)
        Logger.log_warning("Directory not found /tmp/missing")
        assert "[WARN]" in err.getvalue()
        assert "Directory not found /tmp/missing" in err.getvalue()
        assert "osxcollector_warn" in jsonl.getvalue()

    def test_error_has_no_dict_repr(self):
        jsonl = io.StringIO()
        err = io.StringIO()
        Logger.set_output_file(jsonl)
        Console.configure(stream=err)
        with Logger.Extra("osxcollector_section", "tcc"):
            Logger.log_error("boom")
        text = err.getvalue()
        assert "[ERROR] boom" in text
        assert "{'osxcollector" not in text
        assert "osxcollector_section=tcc" in text
        assert "osxcollector_error" in jsonl.getvalue()

    def test_exception_message_is_readable(self):
        jsonl = io.StringIO()
        err = io.StringIO()
        Logger.set_output_file(jsonl)
        Console.configure(stream=err)
        try:
            raise PermissionError("denied")
        except PermissionError as exc:
            Logger.log_exception(exc, message="read_plist failed on /path")
        record = jsonl.getvalue()
        assert "read_plist failed on /path: PermissionError: denied" in record
        assert "extract_tb" not in record
        assert "FrameSummary" not in record
        assert "PermissionError: denied" in err.getvalue()
        assert Console.errors == 1


class TestCollectorProgress:
    def test_sections_to_run_default_skips(self):
        names = Collector.sections_to_run(None)
        assert "version" in names
        assert "full_hash" not in names
        assert "codesign" not in names
        assert Collector.default_skipped_sections(None) == ["codesign", "full_hash"]

    def test_sections_to_run_explicit(self):
        names = Collector.sections_to_run(["tcc", "startup", "missing"])
        assert names == ["startup", "tcc"]
        assert Collector.default_skipped_sections(["tcc"]) == []

    def test_collect_emits_section_progress(self):
        jsonl = io.StringIO()
        err = io.StringIO()
        Logger.set_output_file(jsonl)
        Console.configure(stream=err)
        with patch("osxcollector.collectors.base.get_homedirs", return_value=[]):
            collector = Collector()
            collector._version_string = lambda: Logger.log_dict({"osxcollector_version": "2.0.0"})
            collector.collect(section_list=["version"])
        text = err.getvalue()
        assert "[ 1/1] version" in text
        assert "1 record" in text
