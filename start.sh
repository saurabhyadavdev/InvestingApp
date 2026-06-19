#!/bin/bash
# InvestIQ launcher — starts backend + frontend, opens the browser.
# Auto-shuts down after TIMEOUT_MINS minutes.
# Re-running this script restarts everything cleanly.

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_LOG="$PROJECT_DIR/backend.log"
FRONTEND_LOG="$PROJECT_DIR/frontend.log"
PID_FILE="$PROJECT_DIR/investiq.pid"
BACKEND_PORT=8000
FRONTEND_PORT=3000
TIMEOUT_MINS=15

cd "$PROJECT_DIR"

# ── Helpers ──────────────────────────────────────────────────────────────────

kill_port() {
  local pid
  pid=$(lsof -ti :"$1" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "Stopping existing process on port $1 (PID $pid)..."
    kill "$pid" 2>/dev/null || true
    sleep 1
  fi
}

stop_all() {
  if [ -f "$PID_FILE" ]; then
    local pids
    pids=$(cat "$PID_FILE" 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "Stopping InvestIQ (PIDs: $pids)..."
      # shellcheck disable=SC2086
      kill $pids 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  kill_port $BACKEND_PORT
  kill_port $FRONTEND_PORT
}

# ── Stop command ─────────────────────────────────────────────────────────────
if [ "${1:-}" = "stop" ]; then
  stop_all
  echo "InvestIQ stopped."
  exit 0
fi

# ── Clean up any existing instances (enables restart) ────────────────────────
stop_all

# ── Backend ──────────────────────────────────────────────────────────────────
echo "Starting backend on port $BACKEND_PORT..."
~/headroom-env/bin/python3 -m uvicorn backend.main:app --port $BACKEND_PORT > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo -n "Waiting for backend"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:$BACKEND_PORT/health" > /dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
done

# ── Frontend ─────────────────────────────────────────────────────────────────
echo "Starting frontend on port $FRONTEND_PORT..."
cd "$PROJECT_DIR/frontend"
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!

echo -n "Waiting for frontend"
for i in $(seq 1 20); do
  if curl -sf "http://localhost:$FRONTEND_PORT" > /dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
done

# ── Save PIDs ─────────────────────────────────────────────────────────────────
echo "$BACKEND_PID $FRONTEND_PID" > "$PID_FILE"

# ── Open browser ──────────────────────────────────────────────────────────────
echo "Opening http://localhost:$FRONTEND_PORT ..."
open "http://localhost:$FRONTEND_PORT"

echo ""
echo "InvestIQ is running."
echo "  Backend log  : $BACKEND_LOG"
echo "  Frontend log : $FRONTEND_LOG"
echo "  Auto-shutdown: ${TIMEOUT_MINS} minutes"
echo ""
echo "Commands:"
echo "  Restart : ./start.sh"
echo "  Stop    : ./start.sh stop   (or Ctrl+C here)"
echo ""

# ── Auto-shutdown timer ───────────────────────────────────────────────────────
TIMEOUT_SECS=$((TIMEOUT_MINS * 60))
(
  sleep $TIMEOUT_SECS
  if [ -f "$PID_FILE" ]; then
    echo ""
    echo "Auto-shutdown: ${TIMEOUT_MINS}-minute limit reached. Stopping InvestIQ..."
    pids=$(cat "$PID_FILE" 2>/dev/null || true)
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
) &
TIMER_PID=$!

# ── Wait and clean up on Ctrl+C ───────────────────────────────────────────────
cleanup() {
  echo ""
  echo "Stopping..."
  kill $TIMER_PID 2>/dev/null || true
  kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
  rm -f "$PID_FILE"
  exit 0
}
trap cleanup INT TERM

wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
cleanup
