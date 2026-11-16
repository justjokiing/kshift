#!/usr/bin/env bash
# Run kshift's opt-in integration suite.
#
#   scripts/e2e-kshift.sh            # tiers 1 + 2 (private systemd --user)
#   scripts/e2e-kshift.sh --live     # also tier 3 (touches the live session)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "--live" ]]; then
    export KSHIFT_RUN_PLASMA=1
    shift
fi
export KSHIFT_RUN_INTEGRATION=1

echo "desktop: ${XDG_CURRENT_DESKTOP:-unknown}"
echo "plasma:  $(plasmashell --version 2>/dev/null || echo unavailable)"
echo "systemd: $(systemctl --version 2>/dev/null | head -n 1)"
echo

exec "${PYTHON:-python3}" -m pytest tests/integration -v "$@"
