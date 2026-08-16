# Contributing to OSXCollector

Thanks for helping modernize this forensic collector.

## Development setup

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,macho]'
pre-commit install
make test
```

## Guidelines

- Target **Python 3.11+** and prefer the **stdlib** for anything that must run on a triage host.
- Keep JSONL keys stable when possible (`osxcollector_section`, `osxcollector_subsection`, hash fields). Document breaking key changes in `CHANGELOG.md`.
- New collectors belong under `osxcollector/collectors/` and should register cleanly with the section list.
- Prefer narrow exception handling (`OSError`, `sqlite3.Error`) over bare `except Exception`.
- Do not introduce shell=`True` subprocess calls.
- Add or update unit tests under `tests/` for pure helpers; mark live macOS smoke checks clearly.

## Pull requests

1. Run `make lint` and `make test`.
2. Describe collection path changes and any privilege requirements (root, Full Disk Access).
3. Update the README section list when adding collectors.
