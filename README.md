![osxcollector](https://raw.githubusercontent.com/YelpArchive/osxcollector/master/osx-github.png)

# OSXCollector

OSXCollector is a forensic evidence collection toolkit for macOS. It gathers information from plists, SQLite databases, and the filesystem, and writes **JSON Lines** plus selected logs into a `.tar.gz` for analysis.

**Version 2.0** requires **Python 3.11+** and targets modern macOS (Ventura and later; older releases best-effort). Default collection uses the **Python standard library** only so you can triage with `/usr/bin/python3` or an installed package.

## Quick start

```shell
# From a clone (stdlib collection; no third-party deps required)
sudo /usr/bin/python3 -m osxcollector

# Or install
pip install -e .
sudo osxcollector
```

```shell
$ sudo osxcollector
OSXCollector 2.0.0
  incident   osxcollect-2026_08_11-12_00_00
  root       /
  output     /Users/you/osxcollector-data/osxcollect-2026_08_11-12_00_00
  sections   24  (skipping codesign, full_hash)

  [pre]  Collecting evidence metadata
  [ 1/24] version                 1 record    0.0s
  [ 2/24] system_info             1 record    0.1s
  ...
  [post]  Archiving system logs
  [post]  Unified logs (--last 1h, timeout 120s)
  [post]  Compressing archive

Done in 42.3s
  records   35394
  warnings  18
  errors    0
  archive   /Users/you/osxcollector-data/osxcollect-2026_08_11-12_00_00.tar.gz
  sha256    <digest>
```

Progress, warnings, and errors go to **stderr**. The incident JSONL is written to the output directory (then archived). Missing optional paths show as compact warnings; they are also stored as `osxcollector_warn` records.

**Note:** Live collection against `/` requires root. Offline imaging uses `-p /path/to/mounted/volume` and does not require root for the collector process itself (you still need permission to read the image).

Optional Mach-O extra-data enrichment:

```shell
pip install -e '.[macho]'
```

## Useful options

| Flag | Purpose |
|------|---------|
| `-i PREFIX` | Incident ID prefix (default `osxcollect`) |
| `-p ROOT` | Collect against a mounted filesystem image |
| `-s SECTION` | Run only named section(s); repeatable |
| `--list-sections` | Print section names |
| `--outdir DIR` | Where to write the archive (default `~/osxcollector-data`) |
| `--no-archive` | Keep the incident directory; skip `.tar.gz` |
| `-c` / `-l` | Include cookie / localStorage **values** (sensitive) |
| `-d` | Debug: Extra context dumps, tracebacks, and pdb breakpoints |

Example:

```shell
sudo osxcollector -s startup -s tcc -s quarantines -i Case42
```

## What is collected

Common JSONL keys on every record: `osxcollector_incident_id`, `osxcollector_section`, and often `osxcollector_subsection` / `osxcollector_username`.

File records include `file_path`, `md5`, `sha1`, `sha2`, `atime`, `mtime`, `ctime`, and optionally quarantine / where-from xattrs.

### Sections (2.0)

Legacy (updated): `version`, `system_info`, `kext`, `startup` (LaunchAgents/Daemons, scripting additions, StartupItems, login items, background items), `applications`, `quarantines`, `downloads`, `chrome`, `firefox`, `safari`, `accounts`, `mail`, `executables`, `full_hash`.

New / expanded: `system_extensions`, `background_items`, `edge`, `brave`, `tcc`, `network`, `shell_history`, `ssh`, `processes`, `sip`, `gatekeeper`, `codesign`, plus `evidence_metadata` and unified-log archival into the bundle.

See [`docs/schema/osxcollector-record.schema.json`](docs/schema/osxcollector-record.schema.json) for the common record shape.

### Privilege notes

| Need | Sections / data |
|------|-----------------|
| Root | Live `/` collection; many system plists and logs |
| Full Disk Access | TCC DBs, some Mail/Safari/Chrome paths under SIP |
| Live only | `processes`, unified log export via `log show` |

## Development

```shell
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev,macho]'
make test
make lint
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Analysis

Automated triage of collector output previously lived in [osxcollector_output_filters](https://github.com/Yelp/osxcollector_output_filters) (also archived). Version 2 preserves the JSONL key conventions where possible so existing filters may still apply with minor updates.

## License

GNU GPL v3 or later. See [LICENSE](LICENSE).

Derived from [OSXAuditor](https://github.com/jipegit/OSXAuditor). Originally developed by Yelp Security.
