#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(/usr/bin/dirname "$0")" && pwd)"
exec /bin/bash "$SCRIPT_DIR/launch-notebook.sh" imu.py
