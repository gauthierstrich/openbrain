#!/bin/bash
# ─── OpenBrain — Lanceur Multi-Agents ───
# Lance tous les agents Telegram en parallèle.
# Usage : bash scripts/start_agents.sh

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="/usr/local/bin/python3"
SRC="$SCRIPT_DIR/src/main_telegram.py"

echo "�� OpenBrain — Démarrage de tous les agents..."
echo "─────────────────────────────────────────────"

# Agent Personnel
echo "▸ Lancement de l'Assistant Personnel..."
nohup $PYTHON "$SRC" PERSONAL > "$SCRIPT_DIR/logs/personal.log" 2>&1 &
echo "  PID: $!"

# Agent AC20
echo "▸ Lancement de l'Agent AC20 (Data Science)..."
nohup $PYTHON "$SRC" AC20 > "$SCRIPT_DIR/logs/ac20.log" 2>&1 &
echo "  PID: $!"

echo "─────────────────────────────────────────────"
echo "✅ Tous les agents sont lancés."
echo "�� Logs : $SCRIPT_DIR/logs/"
echo "🛑 Pour arrêter : pkill -f main_telegram.py"
