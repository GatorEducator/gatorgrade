# Issue 218 Demo

These configs demonstrate shell timeouts and safe output decoding. They live
only on the `issue218-demo` branch and should never be merged into `main`.

Run every command from the repository root. In Git Bash on Windows, run
`export PYTHONIOENCODING=utf-8` first so that the check marks print (see issue
244). The slow commands sleep for 30 seconds, so a short run proves that they
were stopped.

## 1. Per-Check Timeout and Invalid Bytes

```bash
uv run gatorgrade --config demo/checks.yml --no-progress-bar
```

The slow check fails with `Command timed out after 3 second(s)` followed by
`running tests...`. The invalid UTF-8 check fails with `bad�byte` instead of a
traceback. Run it again without `--no-progress-bar` to show the progress bar.

## 2. The Per-Check Value Beats the Command Line

```bash
uv run gatorgrade --config demo/checks.yml --timeout 1 --no-progress-bar
```

The slow check still reports `after 3 second(s)`.

## 3. Command-Line Timeout for Checks Without Their Own

```bash
uv run gatorgrade --config demo/cli.yml --timeout 2 --verbose --no-progress-bar
```

The configuration panel shows `Timeout: 2` and the slow check times out after
2 seconds.

## 4. Invalid Values Are Rejected

```bash
uv run gatorgrade --config demo/checks.yml --timeout 0
```

```bash
uv run gatorgrade --config demo/bad_timeout.yml
```

## 5. Setup Timeout

```bash
uv run gatorgrade --config demo/setup.yml
```

Setup prints `installing...` and then reports that it timed out after 2
seconds.

## 6. Timeout in the JSON Report

```bash
uv run gatorgrade --config demo/checks.yml --report file json demo/report.json
```

```bash
cat demo/report.json
```

The slow check has `"timeout": 3` and the others have `"timeout": 300`.

## 7. No Leftover Processes

```bash
tasklist | findstr python
```

This prints nothing right after a demo, so the slow commands were killed.
