# Report Privacy and Safe Mode

GatorGrade reports can contain command-line arguments, check commands,
options, diagnostics, hints, file paths, and other information derived
from student files. Review reports before uploading, committing, or
sharing them.

## Default Privacy Mode

By default, GatorGrade uses best-effort redaction before saving reports.
It replaces recognizable sensitive values with `[redacted]`, including:

- Values stored under names that suggest a secret, such as `api_key`,
  `token`, `password`, `secret`, `credential`, or `authorization`. Case,
  dashes, and underscores are ignored, so `API-KEY` and `apiKey` match.
- Common credential formats inside any text, including OpenAI-style `sk-`
  keys, GitHub `ghp_` and `github_pat_` tokens, AWS access key IDs,
  Slack `xox` tokens, `Bearer` tokens, and private key blocks.
- Values assigned to a secret name inside text, such as `API_KEY=value`
  or `"password": "value"`.
- Bearer tokens and credentials embedded in URLs.

Default mode generally preserves commands, check options, diagnostics,
hints, and file paths when they do not match a redaction pattern.
Redaction changes only the saved report data. Checks still run with their
original values, and terminal output is not redacted in either mode.

## Safe Mode for Public Reports

Use `--report-safe` when preparing a report for public sharing:

```bash
uv run gatorgrade --report FILE JSON report.json --report-safe
```

You can also use safe mode with Markdown reports:

```bash
uv run gatorgrade --report FILE MD report.md --report-safe
```

Safe mode applies the default credential redaction and additionally
replaces supported source-derived fields, including commands, check
options, diagnostics, hints, and output, with `[redacted]`.
Safe mode also redacts values under common file-path fields, including
`path`, `file_path`, `directory`, and `cwd`. Paths embedded in other
text may still remain.

Check results, scores, and check identifiers remain available.

Safe mode changes the saved report data, not the values used to execute
checks. Checks still run using their original commands and options.
Terminal output is not automatically hidden by this flag.

Safe mode also hides configuration paths stored in the `--config`
and `--config-dir` CLI arguments and the destination stored in
`--report`. The report destination type and format remain visible.
Other CLI arguments and arbitrary text may still contain paths.

## Saved Output Destinations

The privacy filter applies to these persisted outputs:

- **JSON reports:** Explicit JSON reports created with `--report`.
- **Markdown reports:** Explicit Markdown reports generated from
  sanitized report data.
- **Automatic history:** JSON reports saved in the platform-specific
  user data directory. History is enabled by default.
- **GitHub environment output:** Report data written using
  `--github-env`, including JSON and Markdown formats.
- **Auto-hint tracking:** Data saved in `autohints.json` when tracking
  is enabled.

When `--report-safe` is enabled, these outputs use the additional
safe-mode filtering.

## Redaction Limitations

Redaction is best-effort and cannot guarantee that every secret or
piece of private information will be recognized.

For example, an unrecognized credential, private student content,
or identifying information may remain in fields that are not covered
by the filtering rules.

Redaction may also hide harmless text that resembles a secret,
including assignments such as `token: example` or `password=value`.

Before sharing a report publicly, inspect its contents and remove
any remaining sensitive information. Avoid storing credentials
directly in assignment configurations or commands.
