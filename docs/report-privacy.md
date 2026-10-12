# Report Privacy and Safe Mode

GatorGrade reports can contain command-line arguments, check commands,
options, diagnostics, hints, file paths, and other information derived
from student files. Review reports before uploading, committing, or
sharing them.

## Default Privacy Mode

By default, GatorGrade uses best-effort redaction before saving reports.
It replaces recognizable sensitive values with `[redacted]`, including:

- API keys, tokens, passwords, and credentials stored under sensitive
  option or field names.
- Common credential formats, including recognizable provider tokens.
- Bearer tokens and credentials embedded in URLs.
- Sensitive values appearing in commands, diagnostics, and hints when
  they match supported redaction patterns.

Default mode generally preserves commands, check options, diagnostics,
hints, and file paths when they do not match a redaction pattern.

## Safe Mode for Public Reports

Use `--report-safe` when preparing a report for public sharing:

```bash
gatorgrade --report FILE JSON report.json --report-safe
```

You can also use safe mode with Markdown reports:

```bash
gatorgrade --report FILE MD report.md --report-safe
```

Safe mode applies the default credential redaction and additionally
replaces supported source-derived fields, including commands, check
options, diagnostics, hints, and output, with `[redacted]`.

Check results, scores, and check identifiers remain available.

Safe mode changes the saved report data, not the values used to execute
checks. Checks still run using their original commands and options.
Terminal output is not automatically hidden by this flag.

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
