#!/usr/bin/env bash
#
# sync-main-to-dev.sh
#
# Detect commits that have landed on the stable branch (main) but are missing
# from the v5 integration branch (dev), then DRY-RUN cherry-pick them into a
# throwaway worktree and report which apply cleanly vs. which conflict.
#
# Why this exists: community v4.x bug fixes merge to `main`, while v5 work lives
# on `dev`. Nothing syncs them automatically, so the two branches silently
# diverge. Run this on a regular cadence to catch divergence early.
#
# This script is READ-ONLY with respect to the remote: it never pushes. Landing
# the resolved branch on `dev` is a deliberate human step because every push to
# `dev` auto-publishes a 5.0.0.devN release to PyPI (see .github/workflows/release.yml).
#
# Usage:
#   scripts/sync-main-to-dev.sh
#
# Overridable via environment:
#   REMOTE (default: origin)  BASE (default: main)  TARGET (default: dev)
#
set -euo pipefail

REMOTE="${REMOTE:-origin}"
BASE="${BASE:-main}"
TARGET="${TARGET:-dev}"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

WT_DIR=".worktrees/sync-${BASE}-to-${TARGET}"
WT_BRANCH="sync/${BASE}-to-${TARGET}-$(date +%Y-%m-%d)"

echo "Fetching ${REMOTE}/${BASE} and ${REMOTE}/${TARGET}..."
git fetch --quiet "$REMOTE" "$BASE" "$TARGET"

mapfile -t commits < <(git log --reverse --no-merges --format='%H' "${REMOTE}/${TARGET}..${REMOTE}/${BASE}")

if [ "${#commits[@]}" -eq 0 ]; then
    echo "In sync: ${REMOTE}/${BASE} has no non-merge commits missing from ${REMOTE}/${TARGET}."
    exit 0
fi

echo "Found ${#commits[@]} commit(s) on ${REMOTE}/${BASE} missing from ${REMOTE}/${TARGET}:"
git log --reverse --no-merges --oneline "${REMOTE}/${TARGET}..${REMOTE}/${BASE}"
echo

# Recreate the throwaway worktree from scratch each run.
git worktree remove --force "$WT_DIR" 2>/dev/null || true
git worktree prune
git branch -D "$WT_BRANCH" 2>/dev/null || true
git worktree add -b "$WT_BRANCH" "$WT_DIR" "${REMOTE}/${TARGET}" >/dev/null

echo "Dry-run cherry-pick into ${WT_DIR} (branch ${WT_BRANCH}):"
echo

clean_count=0
conflict_count=0
for sha in "${commits[@]}"; do
    subject="$(git -C "$WT_DIR" log -1 --format='%s' "$sha")"
    if git -C "$WT_DIR" cherry-pick -x "$sha" >/dev/null 2>&1; then
        printf '  CLEAN     %.9s  %s\n' "$sha" "$subject"
        clean_count=$((clean_count + 1))
    else
        printf '  CONFLICT  %.9s  %s\n' "$sha" "$subject"
        git -C "$WT_DIR" diff --name-only --diff-filter=U | sed 's/^/              - /'
        git -C "$WT_DIR" cherry-pick --abort
        conflict_count=$((conflict_count + 1))
    fi
done

echo
echo "Summary: ${clean_count} clean, ${conflict_count} conflicting."
echo "Worktree left at ${WT_DIR} for inspection."
if [ "$conflict_count" -gt 0 ]; then
    echo
    echo "WARNING: conflicting commits were SKIPPED; the worktree HEAD omits them."
    echo "         Resolve each by hand before pushing, e.g.:"
    echo "           git -C ${WT_DIR} cherry-pick -x <sha>   # then resolve + --continue"
fi
echo
echo "To land on ${TARGET} (auto-publishes ONE 5.0.0.devN to PyPI):"
echo "  git -C ${WT_DIR} push ${REMOTE} HEAD:${TARGET}"
echo "To discard:"
echo "  git worktree remove --force ${WT_DIR} && git branch -D ${WT_BRANCH}"
