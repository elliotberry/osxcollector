# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Live stderr dialogue during collection: start banner, per-section progress, archive phases, and a formatted summary (records, warnings, errors, output path, SHA-256).
- Warnings now print to stderr by default (still recorded as `osxcollector_warn` in JSONL).

### Changed

- Errors and exceptions on stderr are human-readable (`k=v` context, no Python dict `repr` or traceback blobs). JSONL `osxcollector_error` strings are likewise readable; debug mode (`-d`) still dumps Extra context and tracebacks.
- Refusing a live run without root no longer writes a JSONL error record to stdout.

## [2.0.0] - 2026-08-11

### Breaking

- Requires Python 3.11+ (Python 2.7 support removed; Apple no longer ships system Python 2.7).
- Replaced PyObjC `Foundation` plist APIs with stdlib `plistlib`.
- Default collection runs without third-party packages; `macholib` is an optional extra (`[macho]`).
- Packaging moved from `setup.py` to `pyproject.toml`; entry point is `osxcollector.cli:main`.
- Version bumped to 2.0.0 for the Python 3 and path-refresh release.

### Added

- Modular package layout under `osxcollector/` with per-domain collectors.
- New sections: `tcc`, `network`, `shell_history`, `ssh`, `processes`, `sip`, `gatekeeper`, `system_extensions`, `background_items`, `unified_logs` (archived), `chromium` browsers (Edge/Brave).
- Evidence metadata record and SHA-256 of the output archive.
- Safer SQLite handling (read-only URI attempts, tempfile copies, identifier validation).
- GitHub Actions CI on macOS, ruff, mypy, modern pre-commit.
- CLI flags: `--list-sections`, `--outdir`, `--no-archive`, `--timeout`.
- Default output directory is `~/osxcollector-data` (created if missing).
- JSON Schema for common JSONL fields under `docs/schema/`.

### Changed

- `os.popen` replaced with `subprocess.run` (list argv, no shell).
- Login items collection also looks for Background Task Management artifacts.
- Firefox/Safari/Chrome paths refreshed for current browser layouts; legacy paths kept as fallbacks.
- XProtect discovery expanded beyond CoreTypes bundle paths.
- README rewritten for modern macOS and Python 3.

### Removed

- Travis CI configuration (included encrypted credentials).
- Forced `from __future__ import absolute_import` and encoding pragmas.
- Hard runtime dependency on `pyobjc` and `xattr` packages.

## [1.12] - 2019-04-10

Last release under Yelp maintenance (Python 2.7).
