#!/bin/bash
# Run on Linux server after git pull if run_tmux.sh breaks with bash\r
set -euo pipefail
cd "$(dirname "$0")"
sed -i 's/\r$//' run_tmux.sh fix_line_endings.sh after_pull.sh 2>/dev/null || true
chmod +x run_tmux.sh fix_line_endings.sh after_pull.sh 2>/dev/null || true
echo "[after_pull] line endings fixed, run: ./run_tmux.sh"
