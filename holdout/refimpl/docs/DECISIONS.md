# Decisions — RefImpl

Console-only, no GUI: this binary exists solely to calibrate the scorer's
G0/G1/G2/G3 paths. G4 (GUI) is human-scored and out of scope here.

- Ordinal, case-sensitive sort for `sort:"name"` (contract rule 5).
- Extension split requires the last dot at index > 0, so `.gitignore` has an
  empty extension (rule 2).
- Status precedence invalid > collision > unchanged > ok (rule 13); collision
  comparison is case-insensitive, matching Windows filesystem semantics.
- `plan.json` is written UTF-8 without BOM and camelCase, per the schema.
