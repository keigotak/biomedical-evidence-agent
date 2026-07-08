#!/usr/bin/env bash
# One-command demo driver for the ~3-minute video (see docs/demo_video.md).
# Runs each beat and waits for you to press enter, so you can narrate at your own
# pace and never fumble a command on camera. Zero setup: the PubMed and Claude
# beats read saved snapshots, so no network and no API key are needed.
#
#   bash scripts/demo.sh              # interactive (press enter between beats)
#   DEMO_PAUSE=0 bash scripts/demo.sh # run straight through (for a dry run)
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src
CLI="python -m biomedical_evidence_agent.cli"

banner() { printf '\n\033[1;36m### %s\033[0m\n\n' "$1"; }
pause() {
  if [ "${DEMO_PAUSE:-1}" = 1 ]; then
    printf '\n\033[2m  — press enter for the next beat —\033[0m'; read -r _; clear
  fi
}

clear
banner "BioClaim Auditor — it audits a claim, it doesn't just answer it"
pause

banner "1/6  A CONTESTED claim (BRAF V600E melanoma + targeted inhibitors)"
$CLI --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
     --top-k 3 --report claim-audit --reviewer mock
pause

banner "2/6  An OVERCLAIM ('definitively cures ... with salbutamol')"
$CLI --claim "TP53 mutation definitively cures colorectal cancer with salbutamol." \
     --top-k 3 --report claim-audit
pause

banner "3/6  Three therapeutic areas at a glance"
python experiments/compare_claims.py
pause

banner "4/6  Real PubMed — 'Vitamin D reduces cancer risk' -> CONTRADICTED by the VITAL trial (saved snapshot)"
sed -n '10,37p' outputs/example_claim_audit_vitamin_d_pubmed.md
pause

banner "5/6  Built with Claude — the reviewer catches incidence-vs-mortality (saved snapshot)"
sed -n '50,57p' outputs/example_claim_audit_vitamin_d_pubmed.md
pause

banner "6/6  Honest evaluation — 7 streams, stress 8/9, guard ablation"
python -m biomedical_evidence_agent.evaluation | tail -n 24
printf '\n\033[1;36m### Research signal only — not medical advice.\033[0m\n'
