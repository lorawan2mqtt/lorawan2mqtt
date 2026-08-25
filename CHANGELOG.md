# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) —
versioning: [SemVer](https://semver.org/).

## [Unreleased]

### Added
- Community codec database: one JSON file per sensor model, `spec` decode-table
  grammar compatible with the Awaro gateway (import/export in the Decoders tab).
- Reference validator (`tools/validate.py`) replaying every codec's test vectors.
- CI: codec validation on every push and pull request.
