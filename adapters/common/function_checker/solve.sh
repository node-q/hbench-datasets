#!/bin/bash
set -euo pipefail

mkdir -p /app
cp "$(dirname "$0")/solution.py" /app/solution.py
