#!/bin/bash
# Atlas — 一键克隆所有14个Agent仓库
# Usage: bash scripts/clone_all.sh [target_dir]

set -e

TARGET_DIR="${1:-$(pwd)/agents}"
mkdir -p "$TARGET_DIR"

REPOS=(
    "finance-agent"
    "screenplay-agent"
    "cross-domain-learner"
    "market-monitor"
    "system-sentinel"
    "ceo-agent-orchestrator"
    "mirofish-simulator"
    "creative-coordinator"
    "ecommerce-agent"
    "short-video-ops-agent"
    "deerflow-orchestrator"
    "image-agent"
    "video-agent"
    "token-budget-agent"
)

echo "=== Cloning 14 Agent repos into $TARGET_DIR ==="
for repo in "${REPOS[@]}"; do
    echo "[*] Cloning $repo..."
    git clone --depth 1 "https://github.com/596600892/$repo.git" "$TARGET_DIR/$repo" 2>/dev/null && \
        echo "  ✓ $repo" || echo "  ✗ $repo (already exists or failed)"
done

echo ""
echo "=== All done! ==="
echo "Repos cloned to: $TARGET_DIR"
echo ""
echo "To install all at once:"
echo "  for d in $TARGET_DIR/*/; do"
echo "    pip install -e \"\$d\" 2>/dev/null && echo \"✓ \$d\" || echo \"✗ \$d\""
echo "  done"
