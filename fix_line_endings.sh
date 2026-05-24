#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for f in run_tmux.sh fix_line_endings.sh; do
  if [[ -f "$f" ]]; then
    sed -i 's/\r$//' "$f"
    chmod +x "$f"
    echo "fixed: $f"
  fi
done
echo "done"
