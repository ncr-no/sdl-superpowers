#!/usr/bin/env bash
#
# skill-metrics.sh — print the per-skill impact table used by
# docs/superpowers/specs/2026-10-23-cyber-range-exercise-methodology-design.md
#
# Density is software-keyword hits per 100 SKILL.md lines, rounded to the
# nearest percent — the figure the spec table quotes. Reference counts include
# every file outside the skill's own directory, so they drift as documentation
# changes; treat them as a signal, not a fixed number.
#
# Usage:
#   scripts/skill-metrics.sh
#   SKILLS_DIR=/path/to/skills scripts/skill-metrics.sh   # fixture runs
#
set -euo pipefail

case "$0" in
  */*|*\\*) SCRIPT_DIR="$(cd "${0%[/\\]*}" && pwd)" ;;
  *) SCRIPT_DIR="$(pwd)" ;;
esac
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SKILLS_DIR="${SKILLS_DIR:-${REPO_ROOT}/skills}"

# Software vocabulary used to estimate how much of a skill is code-specific.
SW_PATTERN='\b(code|git|commit|branch|merge|pull request|PR|refactor|compile|lint|bug|debug|unit test|repository|repo)\b'

printf '| Skill | SKILL.md lines | Files | Software-keyword density | External files referencing it |\n'
printf '|---|---:|---:|---:|---:|\n'

total_lines=0
total_files=0

for dir in "${SKILLS_DIR}"/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  skill_md="${dir}SKILL.md"
  [ -f "$skill_md" ] || continue

  lines="$(wc -l < "$skill_md" | tr -d ' ')"
  files="$(find "$dir" -type f | wc -l | tr -d ' ')"
  # `|| true`: grep exits 1 on no match, which pipefail+set -e would turn into
  # an aborted table — a skill with no software vocabulary (the migration's
  # goal) or no references yet (every new skill) must still render a row.
  sw_hits="$(grep -oiE "$SW_PATTERN" "$skill_md" | wc -l | tr -d ' ' || true)"
  if [ "$lines" -gt 0 ]; then
    density=$(( (sw_hits * 100 + lines / 2) / lines ))
  else
    density=0
  fi
  refs="$(grep -rIl -F --exclude-dir=.git --exclude-dir=node_modules \
      --exclude-dir="$name" --exclude=RELEASE-NOTES.md \
      "$name" "$REPO_ROOT" 2>/dev/null | wc -l | tr -d ' ' || true)"

  printf '| %s | %s | %s | %s%% | %s |\n' "$name" "$lines" "$files" "$density" "$refs"
  total_lines=$(( total_lines + lines ))
  total_files=$(( total_files + files ))
done

printf '| **Total** | **%s** | **%s** | | |\n' "$total_lines" "$total_files"
