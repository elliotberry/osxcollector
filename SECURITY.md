# Security Policy

## Reporting a vulnerability

If you discover a security issue in OSXCollector (for example unsafe subprocess usage, path traversal while collecting, or accidental exfiltration of secrets in default output), please open a private security advisory on the project repository or email the maintainers listed in the README.

Do not file public issues for vulnerabilities that could help an attacker abuse the collector on a victim machine.

## Design expectations

- Default runs redact cookie and local-storage values.
- Collection may require root and/or Full Disk Access; that is expected for IR triage.
- The collector is intended to run on potentially compromised hosts; treat its output as sensitive evidence.
- Optional network-touching features (if any) must be opt-in and documented.
