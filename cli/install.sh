#!/usr/bin/env bash
#
# Build and install the `gov` governance CLI from source.
#   ./cli/install.sh            # installs to ~/.local/bin/gov
#   BIN_DIR=~/bin ./cli/install.sh
#
# Requires Go (1.24+; the project's go.mod may request a newer toolchain, which
# `go` auto-fetches when GOTOOLCHAIN=auto, the default).

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/gov"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

if ! command -v go >/dev/null 2>&1; then
  echo "Go is required (https://go.dev/dl/). Alternatively regenerate with Printing Press:" >&2
  echo "  go install github.com/mvanhorn/cli-printing-press/v4/cmd/cli-printing-press@latest" >&2
  echo "  cli-printing-press generate --spec $HERE/paperclip-governance.openapi.yaml --name gov --output $SRC --force" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"
echo "Building gov CLI from $SRC ..."
( cd "$SRC" && GOTOOLCHAIN=auto go build -o "$BIN_DIR/gov" ./cmd/gov-pp-cli )
echo "Installed: $BIN_DIR/gov"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "Note: add $BIN_DIR to your PATH.";; esac

cat <<'EOF'

Configure and use:
  export GOV_BOARD_KEY="pcp_board_..."           # your Paperclip board key
  # host comes from the spec server; override per-machine in ~/.config/gov-pp-cli/config.toml
  gov doctor --agent
  gov companies list --agent
  gov companies create-company --help            # spin up a business
  gov routines get <id>                          # first-class routines/projects
EOF
