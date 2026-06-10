---
name: pp-gov
description: "Printing Press CLI for Gov. The verified subset of the Paperclip board API used to spin up and manage teams of AI agents — whole businesses"
author: "jbellsolutions"
license: "Apache-2.0"
argument-hint: "<command> [args] | install cli|mcp"
allowed-tools: "Read Bash"
metadata:
  openclaw:
    requires:
      bins:
        - gov-pp-cli
---

# Gov — Printing Press CLI

## Prerequisites: Install the CLI

This skill drives the `gov-pp-cli` binary. **You must verify the CLI is installed before invoking any command from this skill.** If it is missing, install it first:

1. Install via the Printing Press installer. It defaults binaries to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows:
   ```bash
   npx -y @mvanhorn/printing-press-library install gov --cli-only
   ```
2. Verify: `gov-pp-cli --version`
3. Ensure the reported install directory is on `$PATH` for the agent/runtime that will invoke this skill.

If the `npx` install fails before this CLI has a public-library category, install Node or use the category-specific Go fallback after publish.

If `--version` reports "command not found" after install, the runtime cannot see the binary directory on `$PATH`. Do not proceed with skill commands until verification succeeds.

The verified subset of the Paperclip board API used to spin up and manage teams of AI agents — whole businesses (companies) or departments (agents inside a company). Hand-authored from a live board (Paperclip 2026.529.0); Paperclip does not expose its own OpenAPI document.
Path rule: collection ops (create/list) are nested under /api/companies/{companyId}/...; single-item ops (get/update/delete) are top-level /api/{resource}/{id}.

## Command Reference

**agents** — Manage agents

- `gov-pp-cli agents delete` — Delete an agent (managers with reports may 500 — set status=terminated instead)
- `gov-pp-cli agents get` — Read an agent (incl. stats)
- `gov-pp-cli agents update` — Update an agent (status, budget, adapter, reporting line)

**companies** — Manage companies

- `gov-pp-cli companies create-company` — Create a company (a new business)
- `gov-pp-cli companies get-company` — Read a company (incl. budget/spend)
- `gov-pp-cli companies list` — List all companies
- `gov-pp-cli companies update-company` — Update a company (rename, budget, archive)

**issues** — Manage issues

- `gov-pp-cli issues get` — Read an issue
- `gov-pp-cli issues update` — Update an issue (status

**projects** — Manage projects

- `gov-pp-cli projects <projectId>` — Update a project


### Finding the right command

When you know what you want to do but not which command does it, ask the CLI directly:

```bash
gov-pp-cli which "<capability in your own words>"
```

`which` resolves a natural-language capability query to the best matching command from this CLI's curated feature index. Exit code `0` means at least one match; exit code `2` means no confident match — fall back to `--help` or use a narrower query.

## Auth Setup

Run `gov-pp-cli auth setup` for the URL and steps to obtain a token (add `--launch` to open the URL). Then store it:

```bash
gov-pp-cli auth set-token YOUR_TOKEN_HERE
```

Or set `GOV_BOARD_KEY` as an environment variable.

Run `gov-pp-cli doctor` to verify setup.

## Agent Mode

Add `--agent` to any command. Expands to: `--json --compact --no-input --no-color --yes`.

- **Pipeable** — JSON on stdout, errors on stderr
- **Filterable** — `--select` keeps a subset of fields. Dotted paths descend into nested structures; arrays traverse element-wise. Critical for keeping context small on verbose APIs:

  ```bash
  gov-pp-cli agents get mock-value --agent --select id,name,status
  ```
- **Previewable** — `--dry-run` shows the request without sending
- **Offline-friendly** — sync/search commands can use the local SQLite store when available
- **Non-interactive** — never prompts, every input is a flag
- **Explicit retries** — use `--idempotent` only when an already-existing create should count as success, and `--ignore-missing` only when a missing delete target should count as success

### Response envelope

Commands that read from the local store or the API wrap output in a provenance envelope:

```json
{
  "meta": {"source": "live" | "local", "synced_at": "...", "reason": "..."},
  "results": <data>
}
```

Parse `.results` for data and `.meta.source` to know whether it's live or local. A human-readable `N results (live)` summary is printed to stderr only when stdout is a terminal AND no machine-format flag (`--json`, `--csv`, `--compact`, `--quiet`, `--plain`, `--select`) is set — piped/agent consumers and explicit-format runs get pure JSON on stdout.

## Agent Feedback

When you (or the agent) notice something off about this CLI, record it:

```
gov-pp-cli feedback "the --since flag is inclusive but docs say exclusive"
gov-pp-cli feedback --stdin < notes.txt
gov-pp-cli feedback list --json --limit 10
```

Entries are stored locally at `~/.local/share/gov-pp-cli/feedback.jsonl`. They are never POSTed unless `GOV_FEEDBACK_ENDPOINT` is set AND either `--send` is passed or `GOV_FEEDBACK_AUTO_SEND=true`. Default behavior is local-only.

Write what *surprised* you, not a bug report. Short, specific, one line: that is the part that compounds.

## Output Delivery

Every command accepts `--deliver <sink>`. The output goes to the named sink in addition to (or instead of) stdout, so agents can route command results without hand-piping. Three sinks are supported:

| Sink | Effect |
|------|--------|
| `stdout` | Default; write to stdout only |
| `file:<path>` | Atomically write output to `<path>` (tmp + rename) |
| `webhook:<url>` | POST the output body to the URL (`application/json` or `application/x-ndjson` when `--compact`) |

Unknown schemes are refused with a structured error naming the supported set. Webhook failures return non-zero and log the URL + HTTP status on stderr.

## Named Profiles

A profile is a saved set of flag values, reused across invocations. Use it when a scheduled agent calls the same command every run with the same configuration - HeyGen's "Beacon" pattern.

```
gov-pp-cli profile save briefing --json
gov-pp-cli --profile briefing agents get mock-value
gov-pp-cli profile list --json
gov-pp-cli profile show briefing
gov-pp-cli profile delete briefing --yes
```

Explicit flags always win over profile values; profile values win over defaults. `agent-context` lists all available profiles under `available_profiles` so introspecting agents discover them at runtime.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error (wrong arguments) |
| 3 | Resource not found |
| 4 | Authentication required |
| 5 | API error (upstream issue) |
| 7 | Rate limited (wait and retry) |
| 10 | Config error |

## Argument Parsing

Parse `$ARGUMENTS`:

1. **Empty, `help`, or `--help`** → show `gov-pp-cli --help` output
2. **Starts with `install`** → ends with `mcp` → MCP installation; otherwise → see Prerequisites above
3. **Anything else** → Direct Use (execute as CLI command with `--agent`)

## MCP Server Installation

Install the MCP binary from this CLI's published public-library entry or pre-built release, then register it:

```bash
claude mcp add gov-pp-mcp -- gov-pp-mcp
```

Verify: `claude mcp list`

## Direct Use

1. Check if installed: `which gov-pp-cli`
   If not found, offer to install (see Prerequisites at the top of this skill).
2. Match the user query to the best command from the Unique Capabilities and Command Reference above.
3. Execute with the `--agent` flag:
   ```bash
   gov-pp-cli <command> [subcommand] [args] --agent
   ```
4. If ambiguous, drill into subcommand help: `gov-pp-cli <command> --help`.
