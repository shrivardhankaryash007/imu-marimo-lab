#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(/usr/bin/dirname "${BASH_SOURCE[0]}")" && pwd)"

# Finder launches with a small PATH. Add common user and Homebrew locations.
PATH="${PATH:-/usr/bin:/bin:/usr/sbin:/sbin}"
PATH="$PATH:$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin"
export PATH

notebook="${1:-}"
case "$notebook" in
  attitude_lab.py|imu.py) ;;
  *)
    printf 'Unsupported notebook: %s\n' "$notebook" >&2
    printf 'Use one of: attitude_lab.py, imu.py\n' >&2
    exit 2
    ;;
esac

if ! command -v uvx >/dev/null 2>&1; then
  installer="$(mktemp "${TMPDIR:-/tmp}/uv-install.XXXXXX")"
  trap 'rm -f "$installer"' EXIT
  if ! /usr/bin/curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
    --output "$installer" https://astral.sh/uv/0.11.7/install.sh; then
    printf 'Could not download the uv installer. Install uv to provide uvx, then retry.\n' >&2
    exit 1
  fi
  if ! UV_UNMANAGED_INSTALL="$HOME/.local/bin" /bin/sh "$installer"; then
    printf 'uv installation failed. Install uv to provide uvx, then retry.\n' >&2
    exit 1
  fi
  /bin/rm -f "$installer"
  trap - EXIT
  PATH="$HOME/.local/bin:$PATH"
  export PATH
  if ! command -v uvx >/dev/null 2>&1; then
    printf 'uv installed, but uvx was not found in %s.\n' "$HOME/.local/bin" >&2
    exit 1
  fi
fi

cd "$REPO_DIR"
if [[ -f .env ]]; then
  exec uvx --env-file .env --python 3.11 marimo@0.25.2 run \
    --sandbox=uv --host 127.0.0.1 --token "$notebook"
fi

exec uvx --python 3.11 marimo@0.25.2 run \
  --sandbox=uv --host 127.0.0.1 --token "$notebook"
