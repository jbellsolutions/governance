# Gov CLI

The verified subset of the Paperclip board API used to spin up and manage teams of AI agents — whole businesses (companies) or departments (agents inside a company). Hand-authored from a live board (Paperclip 2026.529.0); Paperclip does not expose its own OpenAPI document.
Path rule: collection ops (create/list) are nested under /api/companies/{companyId}/...; single-item ops (get/update/delete) are top-level /api/{resource}/{id}.

Created by [@jbellsolutions](https://github.com/jbellsolutions).

## Install

The recommended path installs both the `gov-pp-cli` binary and the `pp-gov` agent skill (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, and other agents supported by the upstream [`skills`](https://github.com/vercel-labs/skills) CLI) in one shot:

```bash
npx -y @mvanhorn/printing-press-library install gov
```

For CLI only (no skill):

```bash
npx -y @mvanhorn/printing-press-library install gov --cli-only
```

For skill only — installs the skill into the same agents as the default command above, but skips the CLI binary (use this to update or reinstall just the skill):

```bash
npx -y @mvanhorn/printing-press-library install gov --skill-only
```

To constrain the skill install to one or more specific agents (repeatable — agent names match the [`skills`](https://github.com/vercel-labs/skills) CLI):

```bash
npx -y @mvanhorn/printing-press-library install gov --agent claude-code
npx -y @mvanhorn/printing-press-library install gov --agent claude-code --agent codex
```

### Without Node

The generated install path is category-agnostic until this CLI is published. If `npx` is not available before publish, install Node or use the category-specific Go fallback from the public-library entry after publish.

### Pre-built binary

Download a pre-built binary for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/gov-current). On macOS, clear the Gatekeeper quarantine: `xattr -d com.apple.quarantine <binary>`. On Unix, mark it executable: `chmod +x <binary>`.

<!-- pp-hermes-install-anchor -->
## Install for Hermes

Install the CLI binary first. The installer writes binaries to a per-user managed bin directory by default: `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows.

```bash
npx -y @mvanhorn/printing-press-library install gov --cli-only
```

Then install the focused Hermes skill.

From the Hermes CLI:

```bash
hermes skills install mvanhorn/printing-press-library/cli-skills/pp-gov --force
```

Inside a Hermes chat session:

```bash
/skills install mvanhorn/printing-press-library/cli-skills/pp-gov --force
```

Restart the Hermes session or gateway if the newly installed skill is not visible immediately.

## Install for OpenClaw
Install both the CLI binary and the focused OpenClaw skill. The installer defaults binaries to a per-user bin directory (`$HOME/.local/bin` on macOS/Linux, `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows):

```bash
npx -y @mvanhorn/printing-press-library install gov --agent openclaw
```

Restart the OpenClaw session or gateway if the newly installed skill is not visible immediately.

## Use with Claude Desktop

This CLI ships an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle — Claude Desktop's standard format for one-click MCP extension installs (no JSON config required).

To install:

1. Download the `.mcpb` for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/gov-current).
2. Double-click the `.mcpb` file. Claude Desktop opens and walks you through the install.
3. Fill in `GOV_BOARD_KEY` when Claude Desktop prompts you.

Requires Claude Desktop 1.0.0 or later. Pre-built bundles ship for macOS Apple Silicon (`darwin-arm64`) and Windows (`amd64`, `arm64`); for other platforms, use the manual config below.

<details>
<summary>Manual JSON config (advanced)</summary>

If you can't use the MCPB bundle (older Claude Desktop, unsupported platform), install the MCP binary and configure it manually.


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "gov": {
      "command": "gov-pp-mcp",
      "env": {
        "GOV_BOARD_KEY": "<your-key>"
      }
    }
  }
}
```

</details>

## Quick Start

### 1. Install

See [Install](#install) above.

### 2. Set Up Credentials

Get your access token from your API provider's developer portal, then store it:

```bash
gov-pp-cli auth set-token YOUR_TOKEN_HERE
```

Or set it via environment variable:

```bash
export GOV_BOARD_KEY="your-token-here"
```

### 3. Verify Setup

```bash
gov-pp-cli doctor
```

This checks your configuration and credentials.

### 4. Try Your First Command

```bash
gov-pp-cli agents get mock-value
```

## Usage

Run `gov-pp-cli --help` for the full command reference and flag list.

## Commands

### agents

Manage agents

- **`gov-pp-cli agents delete`** - Delete an agent (managers with reports may 500 — set status=terminated instead)
- **`gov-pp-cli agents get`** - Read an agent (incl. stats)
- **`gov-pp-cli agents update`** - Update an agent (status, budget, adapter, reporting line)

### companies

Manage companies

- **`gov-pp-cli companies create-company`** - Create a company (a new business)
- **`gov-pp-cli companies get-company`** - Read a company (incl. budget/spend)
- **`gov-pp-cli companies list`** - List all companies
- **`gov-pp-cli companies update-company`** - Update a company (rename, budget, archive)

### issues

Manage issues

- **`gov-pp-cli issues get`** - Read an issue
- **`gov-pp-cli issues update`** - Update an issue (status

### projects

Manage projects

- **`gov-pp-cli projects get`** - Read a project
- **`gov-pp-cli projects update`** - Update a project

### routines

Manage routines

- **`gov-pp-cli routines get`** - Read a routine (incl. triggers/nextRunAt)
- **`gov-pp-cli routines update`** - Update a routine (title, triggers, status, assignee)


## Output Formats

```bash
# Human-readable table (default in terminal, JSON when piped)
gov-pp-cli agents get mock-value

# JSON for scripting and agents
gov-pp-cli agents get mock-value --json

# Filter to specific fields
gov-pp-cli agents get mock-value --json --select id,name,status

# Dry run — show the request without sending
gov-pp-cli agents get mock-value --dry-run

# Agent mode — JSON + compact + no prompts in one flag
gov-pp-cli agents get mock-value --agent
```

## Agent Usage

This CLI is designed for AI agent consumption:

- **Non-interactive** - never prompts, every input is a flag
- **Pipeable** - `--json` output to stdout, errors to stderr
- **Filterable** - `--select id,name` returns only fields you need
- **Previewable** - `--dry-run` shows the request without sending
- **Explicit retries** - add `--idempotent` to create retries and `--ignore-missing` to delete retries when a no-op success is acceptable
- **Confirmable** - `--yes` for explicit confirmation of destructive actions
- **Piped input** - write commands can accept structured input when their help lists `--stdin`
- **Offline-friendly** - sync/search commands can use the local SQLite store when available
- **Agent-safe by default** - no colors or formatting unless `--human-friendly` is set

Exit codes: `0` success, `2` usage error, `3` not found, `4` auth error, `5` API error, `7` rate limited, `10` config error.

## Health Check

```bash
gov-pp-cli doctor
```

Verifies configuration, credentials, and connectivity to the API.

## Configuration

Config file: `~/.config/paperclip-governance-pp-cli/config.toml`

Static request headers can be configured under `headers`; per-command header overrides take precedence.

Environment variables:

| Name | Kind | Required | Description |
| --- | --- | --- | --- |
| `GOV_BOARD_KEY` | per_call | Yes | Set to your API credential. |

### agentcookie (optional)

If you use agentcookie to sync secrets across machines, this CLI auto-adopts agentcookie-managed credentials with no extra setup. When the daemon writes to this CLI's config, `gov-pp-cli doctor` reports `agentcookie: detected` and `auth-status` labels the source as `agentcookie`. Skip this section if you don't use agentcookie - the CLI works the same as any other.

## Troubleshooting
**Authentication errors (exit code 4)**
- Run `gov-pp-cli doctor` to check credentials
- Verify the environment variable is set: `echo $GOV_BOARD_KEY`
**Not found errors (exit code 3)**
- Check the resource ID is correct
- Run the `list` command to see available items

---

Generated by [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)
